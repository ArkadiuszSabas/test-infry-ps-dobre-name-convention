"""OCR pipeline run dependency factories for the API service."""

from collections.abc import Mapping
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind_api.application.attribute_requirements.models import (
    DocumentTypeAttributeRequirementMatrix,
)
from docmind_api.application.attribute_requirements.policies import (
    EffectiveAttributeRequirementsPolicy,
    MetadataBooleanMakesAllOptionalPolicy,
    UnchangedAttributeRequirementsPolicy,
)
from docmind_api.application.attribute_requirements.service import AttributeRequirementMatrixService
from docmind_api.application.ocr_pipeline_runs.commands import (
    StartOcrPipelineRunCommand,
)
from docmind_api.application.ocr_pipeline_runs.context_resolver_config import (
    OcrPipelineContextAttribute,
    OcrPipelineContextMetadata,
    context_metadata_value,
    context_value_type,
)
from docmind_api.application.ocr_pipeline_runs.ports import (
    DirectOcrPipelineRunLimits,
    OcrPipelineRunExecutionPolicy,
    OcrPipelineRunInvoker,
    OcrPipelineRunScheduler,
)
from docmind_api.application.ocr_pipeline_runs.service import OcrPipelineRunService
from docmind_api.bootstrap.dependencies.connectors import get_connector_profile_manifest
from docmind_api.bootstrap.dependencies.database import (
    get_database_session,
    get_database_session_factory,
    get_or_create_database_session_factory,
)
from docmind_api.bootstrap.dependencies.ocr_pipeline_run_dispatch import (
    DirectOcrPipelineRunDispatcher,
)
from docmind_api.domain.ocr_pipeline_runs.models import OcrPipelineRunRecord
from docmind_api.infrastructure.ocr_pipeline_runs.runtime import (
    UnavailableOcrPipelineRunInvoker,
    UtcClock,
    UuidOcrPipelineRunIdFactory,
)
from docmind_api.infrastructure.ocr_pipeline_runs.scheduler import OcrPipelineRunTaskScheduler
from docmind_api.infrastructure.persistence.attribute_requirements.repositories import (
    SqlAlchemyAttributeRequirementRepository,
)
from docmind_api.infrastructure.persistence.attributes.category_repositories import (
    SqlAlchemyAttributeCategoryRepository,
)
from docmind_api.infrastructure.persistence.attributes.repositories import (
    SqlAlchemyAttributeDefinitionRepository,
)
from docmind_api.infrastructure.persistence.document_types.repositories import (
    SqlAlchemyDocumentTypeCatalogRepository,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.repositories import (
    SqlAlchemyOcrPipelineRunDocumentReader,
    SqlAlchemyOcrPipelineRunRepository,
    SqlAlchemyPublishedOcrPipelineSnapshotReader,
)
from docmind_api.infrastructure.persistence.sql import database_session_scope
from docmind_api.settings import DirectOcrPipelineRunSettings
from docmind_api.settings import load_direct_ocr_pipeline_run_settings as load_run_settings
from docmind_core.connectors.profiles import ProfileManifest

_OCR_PIPELINE_RUN_SCHEDULER_STATE_KEY = "_docmind_api_ocr_pipeline_run_scheduler"


class CommittedOcrPipelineRunStarter:
    """Creates direct OCR runs in a committed unit of work before dispatch."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        limits: DirectOcrPipelineRunLimits,
        effective_requirements_policy: EffectiveAttributeRequirementsPolicy,
        connector_display_names: Mapping[str, str],
    ) -> None:
        self._session_factory = session_factory
        self._limits = limits
        self._effective_requirements_policy = effective_requirements_policy
        self._connector_display_names = dict(connector_display_names)

    async def start_run(self, command: StartOcrPipelineRunCommand) -> OcrPipelineRunRecord:
        """Create one pending run and commit it before returning to the route."""

        async with database_session_scope(self._session_factory) as session:
            service = _create_run_service(
                session,
                limits=self._limits,
                effective_requirements_policy=self._effective_requirements_policy,
                connector_display_names=self._connector_display_names,
            )
            return await service.start_run(command)


class AttributeRequirementContextAttributeSource:
    """Reads document-type matrix attributes for Context Resolver runtime config."""

    def __init__(
        self,
        matrix_service: AttributeRequirementMatrixService,
        effective_requirements_policy: EffectiveAttributeRequirementsPolicy,
    ) -> None:
        self._matrix_service = matrix_service
        self._effective_requirements_policy = effective_requirements_policy
        self._matrix_cache: dict[UUID, DocumentTypeAttributeRequirementMatrix] = {}

    async def list_context_attributes(
        self,
        *,
        document_type_id: UUID,
        metadata_values: Mapping[str, object],
    ) -> tuple[OcrPipelineContextAttribute, ...]:
        matrix = await self._matrix(document_type_id)
        all_optional = self._effective_requirements_policy.all_attributes_optional(metadata_values)
        attributes: list[OcrPipelineContextAttribute] = []
        for entry in matrix.requirements:
            if entry.is_metadata:
                continue
            attributes.append(
                OcrPipelineContextAttribute(
                    attribute_id=UUID(str(entry.attribute.id)),
                    attribute_external_id=entry.attribute.external_id or str(entry.attribute.id),
                    display_name=entry.attribute.name,
                    value_type=context_value_type(entry.attribute.data_type),
                    required=False if all_optional else entry.requirement.required,
                    llm_context=entry.attribute.llm_context,
                ),
            )
        return tuple(attributes)

    async def list_context_metadata(
        self,
        *,
        document_type_id: UUID,
        metadata_values: Mapping[str, object],
    ) -> tuple[OcrPipelineContextMetadata, ...]:
        """Return only matrix-opted metadata values present on the document."""

        matrix = await self._matrix(document_type_id)
        metadata: list[OcrPipelineContextMetadata] = []
        for entry in matrix.requirements:
            if not entry.requirement.include_metadata_in_context_resolver:
                continue
            if not entry.is_metadata:
                continue
            key = entry.attribute.external_id or str(entry.attribute.id)
            value = context_metadata_value(metadata_values.get(key))
            if value is not None:
                metadata.append(
                    OcrPipelineContextMetadata(
                        key=key,
                        display_name=entry.attribute.name,
                        value=value,
                    )
                )
        return tuple(metadata)

    async def _matrix(self, document_type_id: UUID) -> DocumentTypeAttributeRequirementMatrix:
        if (matrix := self._matrix_cache.get(document_type_id)) is None:
            matrix = await self._matrix_service.get_matrix(document_type_id=document_type_id)
            self._matrix_cache[document_type_id] = matrix
        return matrix


def install_ocr_pipeline_run_scheduler(
    app: FastAPI,
    *,
    max_concurrency: int,
    stale_run_timeout_seconds: float,
    watchdog_interval_seconds: float,
) -> None:
    """Install the app-owned scheduler before the API starts accepting requests."""

    scheduler = OcrPipelineRunTaskScheduler(max_concurrency=max_concurrency)

    async def reconcile_stale_runs() -> int:
        settings = load_run_settings()
        dispatcher = DirectOcrPipelineRunDispatcher(
            session_factory=get_or_create_database_session_factory(app),
            invocation_timeout_seconds=settings.invocation_timeout_seconds,
            execution_policy=OcrPipelineRunExecutionPolicy(
                max_attempts=settings.max_attempts,
                lease_duration_seconds=settings.lease_duration_seconds,
                lease_renewal_interval_seconds=settings.lease_renewal_interval_seconds,
            ),
        )
        return await dispatcher.fail_stale_executions(
            stale_after_seconds=stale_run_timeout_seconds,
        )

    scheduler.start_watchdog(
        reconcile_stale_runs,
        interval_seconds=watchdog_interval_seconds,
    )
    setattr(app.state, _OCR_PIPELINE_RUN_SCHEDULER_STATE_KEY, scheduler)


def get_ocr_pipeline_run_scheduler(request: Request) -> OcrPipelineRunScheduler:
    """Return the app-owned scheduler used by direct run routes."""

    scheduler = getattr(request.app.state, _OCR_PIPELINE_RUN_SCHEDULER_STATE_KEY, None)
    if not isinstance(scheduler, OcrPipelineRunTaskScheduler):
        raise RuntimeError("OCR pipeline run scheduler is not initialized.")
    return scheduler


async def dispose_ocr_pipeline_run_scheduler(app: FastAPI) -> None:
    """Stop app-owned OCR dispatches before shared resources are disposed."""

    scheduler = getattr(app.state, _OCR_PIPELINE_RUN_SCHEDULER_STATE_KEY, None)
    if not isinstance(scheduler, OcrPipelineRunTaskScheduler):
        return
    await scheduler.shutdown()
    setattr(app.state, _OCR_PIPELINE_RUN_SCHEDULER_STATE_KEY, None)


def get_direct_ocr_pipeline_run_settings() -> DirectOcrPipelineRunSettings:
    """Return direct OCR run settings for dependency injection."""

    return load_run_settings()


def get_direct_ocr_pipeline_run_limits(
    settings: Annotated[
        DirectOcrPipelineRunSettings,
        Depends(get_direct_ocr_pipeline_run_settings),
    ],
) -> DirectOcrPipelineRunLimits:
    """Map service settings to application run limits."""

    return DirectOcrPipelineRunLimits(
        max_content_bytes=settings.max_content_bytes,
        max_step_count=settings.max_step_count,
    )


def get_effective_attribute_requirements_policy(
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
) -> EffectiveAttributeRequirementsPolicy:
    """Build the document-independent policy selected by the active deployment profile."""

    policy = manifest.runtime_policies.effective_attribute_requirements
    if policy is None:
        return UnchangedAttributeRequirementsPolicy()
    return MetadataBooleanMakesAllOptionalPolicy(
        trigger_metadata_key=policy.trigger_metadata_key,
    )


def get_ocr_pipeline_run_starter(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_database_session_factory),
    ],
    limits: Annotated[DirectOcrPipelineRunLimits, Depends(get_direct_ocr_pipeline_run_limits)],
    effective_requirements_policy: Annotated[
        EffectiveAttributeRequirementsPolicy,
        Depends(get_effective_attribute_requirements_policy),
    ],
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
) -> CommittedOcrPipelineRunStarter:
    """Return a starter that commits the run before background dispatch is scheduled."""

    return CommittedOcrPipelineRunStarter(
        session_factory=session_factory,
        limits=limits,
        effective_requirements_policy=effective_requirements_policy,
        connector_display_names=_connector_display_names(manifest),
    )


def get_ocr_pipeline_run_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    limits: Annotated[DirectOcrPipelineRunLimits, Depends(get_direct_ocr_pipeline_run_limits)],
    effective_requirements_policy: Annotated[
        EffectiveAttributeRequirementsPolicy,
        Depends(get_effective_attribute_requirements_policy),
    ],
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
) -> OcrPipelineRunService:
    """Return the request-scoped OCR pipeline run application service."""

    return _create_run_service(
        session,
        limits=limits,
        effective_requirements_policy=effective_requirements_policy,
        connector_display_names=_connector_display_names(manifest),
    )


def get_ocr_pipeline_run_dispatcher(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_database_session_factory),
    ],
    settings: Annotated[
        DirectOcrPipelineRunSettings,
        Depends(get_direct_ocr_pipeline_run_settings),
    ],
) -> DirectOcrPipelineRunDispatcher:
    """Return a dispatcher for app-scheduled direct runs."""

    return DirectOcrPipelineRunDispatcher(
        session_factory=session_factory,
        invocation_timeout_seconds=settings.invocation_timeout_seconds,
        execution_policy=OcrPipelineRunExecutionPolicy(
            max_attempts=settings.max_attempts,
            lease_duration_seconds=settings.lease_duration_seconds,
            lease_renewal_interval_seconds=settings.lease_renewal_interval_seconds,
        ),
    )


def _create_run_service(
    session: AsyncSession,
    *,
    limits: DirectOcrPipelineRunLimits,
    effective_requirements_policy: EffectiveAttributeRequirementsPolicy,
    connector_display_names: Mapping[str, str] | None = None,
    invoker: OcrPipelineRunInvoker | None = None,
) -> OcrPipelineRunService:
    return OcrPipelineRunService(
        repository=SqlAlchemyOcrPipelineRunRepository(session),
        document_reader=SqlAlchemyOcrPipelineRunDocumentReader(session),
        pipeline_reader=SqlAlchemyPublishedOcrPipelineSnapshotReader(session),
        invoker=invoker or UnavailableOcrPipelineRunInvoker(),
        id_factory=UuidOcrPipelineRunIdFactory(),
        clock=UtcClock(),
        limits=limits,
        context_attribute_source=AttributeRequirementContextAttributeSource(
            AttributeRequirementMatrixService(
                repository=SqlAlchemyAttributeRequirementRepository(session),
                document_type_repository=SqlAlchemyDocumentTypeCatalogRepository(session),
                attribute_repository=SqlAlchemyAttributeDefinitionRepository(session),
                attribute_category_repository=SqlAlchemyAttributeCategoryRepository(session),
                clock=UtcClock(),
            ),
            effective_requirements_policy=effective_requirements_policy,
        ),
        connector_display_names=connector_display_names,
    )


def _connector_display_names(manifest: ProfileManifest) -> dict[str, str]:
    return {
        instance.connector_instance_id: instance.safe_metadata.label
        for instance in manifest.connector_instances
    }
