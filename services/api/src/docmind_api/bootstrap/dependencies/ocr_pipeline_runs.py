"""OCR pipeline run dependency factories for the API service."""

import logging
from collections.abc import Mapping
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI
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
from docmind_api.application.dictionaries.ports import DictionaryRepository
from docmind_api.application.ocr_pipeline_runs.admin_read_model import AdminOcrRunReadService
from docmind_api.application.ocr_pipeline_runs.commands import (
    StartOcrPipelineRunCommand,
)
from docmind_api.application.ocr_pipeline_runs.context_resolver_config import (
    OcrPipelineContextAttribute,
    OcrPipelineContextMetadata,
    context_metadata_value,
    context_value_type,
)
from docmind_api.application.ocr_pipeline_runs.outbox import OcrRunOutboxRelay
from docmind_api.application.ocr_pipeline_runs.ports import (
    OcrEventCompletion,
    OcrPipelineRunLimits,
)
from docmind_api.application.ocr_pipeline_runs.service import OcrPipelineRunService
from docmind_api.bootstrap.dependencies.connectors import get_connector_profile_manifest
from docmind_api.bootstrap.dependencies.database import (
    get_database_session,
    get_database_session_factory,
    get_or_create_database_session_factory,
)
from docmind_api.bootstrap.dependencies.ocr_pipeline_review import initialize_pipeline_run_review
from docmind_api.domain.dictionaries.models import DictionaryStatus
from docmind_api.domain.ocr_pipeline_runs.models import OcrPipelineRunRecord
from docmind_api.infrastructure.ocr_pipeline_runs.maintenance import OcrPipelineRunMaintenance
from docmind_api.infrastructure.ocr_pipeline_runs.outbox import DaprOcrRunRequestPublisher
from docmind_api.infrastructure.ocr_pipeline_runs.runtime import (
    UtcClock,
    UuidOcrPipelineRunIdFactory,
)
from docmind_api.infrastructure.persistence.attribute_requirements.repositories import (
    SqlAlchemyAttributeRequirementRepository,
)
from docmind_api.infrastructure.persistence.attributes.category_repositories import (
    SqlAlchemyAttributeCategoryRepository,
)
from docmind_api.infrastructure.persistence.attributes.repositories import (
    SqlAlchemyAttributeDefinitionRepository,
)
from docmind_api.infrastructure.persistence.dictionaries.repositories import (
    SqlAlchemyDictionaryRepository,
)
from docmind_api.infrastructure.persistence.document_types.repositories import (
    SqlAlchemyDocumentTypeCatalogRepository,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.admin_read_repository import (
    SqlAlchemyAdminOcrRunReadRepository,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.repositories import (
    SqlAlchemyOcrPipelineRunDocumentReader,
    SqlAlchemyOcrPipelineRunRepository,
    SqlAlchemyPublishedOcrPipelineSnapshotReader,
)
from docmind_api.infrastructure.persistence.sql import database_session_scope
from docmind_api.settings import OcrPipelineRunSettings, get_dapr_client_settings
from docmind_api.settings import load_ocr_pipeline_run_settings as load_run_settings
from docmind_backend_runtime import create_dapr_client
from docmind_core.connectors.profiles import ProfileManifest

_OCR_PIPELINE_RUN_MAINTENANCE_STATE_KEY = "_docmind_api_ocr_pipeline_run_maintenance"
_LOGGER = logging.getLogger(__name__)


def _agentic_attribute_source(*, is_metadata: bool, configured_source: str) -> str:
    if is_metadata:
        # Owner rule: metadata opt-in alone selects verification; configured source is ignored.
        return "ai"
    return configured_source


class CommittedOcrPipelineRunStarter:
    """Create OCR runs and their outbox events in one committed unit of work."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        limits: OcrPipelineRunLimits,
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


class CommittedOcrEventRunCompleter:
    """Commit an event completion before initiating its independent Review projection."""

    def __init__(self, *, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def complete(
        self,
        run_id: UUID,
        attempt_id: UUID,
        completion: OcrEventCompletion,
    ) -> str:
        async with database_session_scope(self._session_factory) as session:
            outcome = await SqlAlchemyOcrPipelineRunRepository(session).complete_event_run(
                run_id,
                attempt_id,
                completion,
            )
        if outcome in {"completed", "duplicate"}:
            try:
                await initialize_pipeline_run_review(
                    self._session_factory,
                    completion.document_id,
                    run_id,
                )
            except Exception:
                _LOGGER.error(
                    "OCR pipeline completion persisted but Review initialization failed.",
                    extra={"ocr_pipeline_run_id": str(run_id)},
                )
        return outcome


class AttributeRequirementContextAttributeSource:
    """Reads document-type matrix attributes for Context Resolver runtime config."""

    def __init__(
        self,
        matrix_service: AttributeRequirementMatrixService,
        effective_requirements_policy: EffectiveAttributeRequirementsPolicy,
        dictionary_repository: DictionaryRepository | None = None,
    ) -> None:
        self._matrix_service = matrix_service
        self._effective_requirements_policy = effective_requirements_policy
        self._dictionary_repository = dictionary_repository
        self._matrix_cache: dict[UUID, DocumentTypeAttributeRequirementMatrix] = {}

    async def list_context_attributes(
        self,
        *,
        document_type_id: UUID,
        metadata_values: Mapping[str, object],
    ) -> tuple[OcrPipelineContextAttribute, ...]:
        return await self._attributes(
            document_type_id=document_type_id,
            metadata_values=metadata_values,
        )

    async def list_agentic_context_attributes(
        self,
        *,
        document_type_id: UUID,
        metadata_values: Mapping[str, object],
    ) -> tuple[OcrPipelineContextAttribute, ...]:
        """Return the richer snapshot used only by the alternative resolver."""

        matrix = await self._matrix(document_type_id)
        all_optional = self._effective_requirements_policy.all_attributes_optional(metadata_values)
        attributes: list[OcrPipelineContextAttribute] = []
        for entry in matrix.requirements:
            if not entry.attribute.is_active:
                continue
            metadata_value: str | None = None
            if entry.is_metadata:
                if not entry.requirement.include_metadata_in_context_resolver:
                    continue
                key = entry.attribute.external_id or str(entry.attribute.id)
                metadata_value = context_metadata_value(metadata_values.get(key))
            attributes.append(
                OcrPipelineContextAttribute(
                    attribute_id=UUID(str(entry.attribute.id)),
                    attribute_external_id=entry.attribute.external_id or str(entry.attribute.id),
                    display_name=entry.attribute.name,
                    value_type=context_value_type(entry.attribute.data_type),
                    required=False if all_optional else entry.requirement.required,
                    llm_context=entry.attribute.llm_context,
                    data_type=entry.attribute.data_type.value,
                    value_source=entry.attribute.value_source.value,
                    constraints=entry.attribute.constraints.as_json(),
                    allowed_values=entry.attribute.allowed_values,
                    dictionary_values=await self._dictionary_values(entry.attribute),
                    source=_agentic_attribute_source(
                        is_metadata=entry.is_metadata,
                        configured_source=entry.attribute.source.value,
                    ),
                    configured_required=entry.requirement.required,
                    missing_required_action=(
                        entry.requirement.missing_required_action.value
                        if entry.requirement.missing_required_action is not None
                        else None
                    ),
                    metadata_value=metadata_value,
                ),
            )
        return tuple(attributes)

    async def _attributes(
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
                    attribute_external_id=(entry.attribute.external_id or str(entry.attribute.id)),
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
                        attribute_id=UUID(str(entry.attribute.id)),
                    )
                )
        return tuple(metadata)

    async def list_agentic_context_metadata(
        self,
        *,
        document_type_id: UUID,
        metadata_values: Mapping[str, object],
    ) -> tuple[OcrPipelineContextMetadata, ...]:
        """Return only active, opted-in metadata with stable UUID identity."""

        matrix = await self._matrix(document_type_id)
        metadata: list[OcrPipelineContextMetadata] = []
        for entry in matrix.requirements:
            if not entry.attribute.is_active:
                continue
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
                        attribute_id=UUID(str(entry.attribute.id)),
                    )
                )
        return tuple(metadata)

    async def _dictionary_values(self, attribute: object) -> tuple[str, ...]:
        dictionary_id = getattr(attribute, "dictionary_id", None)
        if dictionary_id is None or self._dictionary_repository is None:
            return ()
        result = await self._dictionary_repository.search_entries(
            dictionary_id,
            status=DictionaryStatus.ACTIVE,
            limit=100,
            offset=0,
        )
        if result.total_count > 100:
            raise ValueError(
                "Agentic Context Resolver dictionary snapshot exceeds the MVP maximum."
            )
        return tuple(entry.label for entry in result.entries)

    async def _matrix(self, document_type_id: UUID) -> DocumentTypeAttributeRequirementMatrix:
        if (matrix := self._matrix_cache.get(document_type_id)) is None:
            matrix = await self._matrix_service.get_matrix(document_type_id=document_type_id)
            self._matrix_cache[document_type_id] = matrix
        return matrix


def install_ocr_pipeline_run_maintenance(
    app: FastAPI,
    *,
    interval_seconds: float,
    outbox_relay_interval_seconds: float,
) -> None:
    """Install the API-owned durable OCR maintenance loop."""

    maintenance = OcrPipelineRunMaintenance()

    async def relay_pending_outbox() -> int:
        return await relay_ocr_run_outbox_once(get_or_create_database_session_factory(app))

    async def reconcile_executions() -> int:
        settings = get_ocr_pipeline_run_settings()
        async with database_session_scope(get_or_create_database_session_factory(app)) as session:
            return await SqlAlchemyOcrPipelineRunRepository(session).reconcile_event_executions(
                defer_seconds=settings.defer_seconds
            )

    async def reconcile_cancellations() -> int:
        async with database_session_scope(get_or_create_database_session_factory(app)) as session:
            return await SqlAlchemyOcrPipelineRunRepository(session).reconcile_cancellations()

    async def refresh_admission_metrics() -> int:
        async with database_session_scope(get_or_create_database_session_factory(app)) as session:
            await SqlAlchemyOcrPipelineRunRepository(session).refresh_admission_metrics()
            return 1

    maintenance.start_periodic(
        relay_pending_outbox,
        interval_seconds=outbox_relay_interval_seconds,
        task_name="ocr-pipeline-run-outbox-relay",
    )
    maintenance.start_periodic(
        reconcile_executions,
        interval_seconds=interval_seconds,
        task_name="ocr-pipeline-run-execution-watchdog",
    )
    maintenance.start_periodic(
        reconcile_cancellations,
        interval_seconds=interval_seconds,
        task_name="ocr-pipeline-run-cancellation-watchdog",
    )
    maintenance.start_periodic(
        refresh_admission_metrics,
        interval_seconds=interval_seconds,
        task_name="ocr-pipeline-run-admission-metrics",
    )
    setattr(app.state, _OCR_PIPELINE_RUN_MAINTENANCE_STATE_KEY, maintenance)


async def dispose_ocr_pipeline_run_maintenance(app: FastAPI) -> None:
    """Stop OCR control-plane maintenance before shared resources are disposed."""

    maintenance = getattr(app.state, _OCR_PIPELINE_RUN_MAINTENANCE_STATE_KEY, None)
    if not isinstance(maintenance, OcrPipelineRunMaintenance):
        return
    await maintenance.shutdown()
    setattr(app.state, _OCR_PIPELINE_RUN_MAINTENANCE_STATE_KEY, None)


def get_ocr_pipeline_run_settings() -> OcrPipelineRunSettings:
    """Return OCR control-plane settings for dependency injection."""

    return load_run_settings()


async def relay_ocr_run_outbox_once(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    limit: int = 20,
) -> int:
    """Publish one bounded OCR outbox batch after the run transaction commits."""

    settings = get_ocr_pipeline_run_settings()
    async with database_session_scope(session_factory) as session:
        relay = OcrRunOutboxRelay(
            repository=SqlAlchemyOcrPipelineRunRepository(session),
            publisher=DaprOcrRunRequestPublisher(
                dapr_client=create_dapr_client(get_dapr_client_settings()),
                pubsub_name=settings.event_pubsub_name,
            ),
        )
        return await relay.relay_once(limit=limit)


def get_ocr_pipeline_run_limits(
    settings: Annotated[
        OcrPipelineRunSettings,
        Depends(get_ocr_pipeline_run_settings),
    ],
) -> OcrPipelineRunLimits:
    """Map service settings to application run limits."""

    return OcrPipelineRunLimits(
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
    limits: Annotated[OcrPipelineRunLimits, Depends(get_ocr_pipeline_run_limits)],
    effective_requirements_policy: Annotated[
        EffectiveAttributeRequirementsPolicy,
        Depends(get_effective_attribute_requirements_policy),
    ],
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
) -> CommittedOcrPipelineRunStarter:
    """Return a starter that commits the run together with its outbox event."""

    return CommittedOcrPipelineRunStarter(
        session_factory=session_factory,
        limits=limits,
        effective_requirements_policy=effective_requirements_policy,
        connector_display_names=_connector_display_names(manifest),
    )


def get_ocr_pipeline_run_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    limits: Annotated[OcrPipelineRunLimits, Depends(get_ocr_pipeline_run_limits)],
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


def get_ocr_pipeline_run_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SqlAlchemyOcrPipelineRunRepository:
    """Return the repository used by internal OCR control-plane routes."""

    return SqlAlchemyOcrPipelineRunRepository(session)


def get_admin_ocr_run_read_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AdminOcrRunReadService:
    """Return the request-scoped administrative OCR read service."""

    return AdminOcrRunReadService(SqlAlchemyAdminOcrRunReadRepository(session))


def get_ocr_event_run_completer(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_database_session_factory),
    ],
) -> CommittedOcrEventRunCompleter:
    """Return the post-commit completion boundary for internal event-mode runs."""

    return CommittedOcrEventRunCompleter(session_factory=session_factory)


def _create_run_service(
    session: AsyncSession,
    *,
    limits: OcrPipelineRunLimits,
    effective_requirements_policy: EffectiveAttributeRequirementsPolicy,
    connector_display_names: Mapping[str, str] | None = None,
) -> OcrPipelineRunService:
    return OcrPipelineRunService(
        repository=SqlAlchemyOcrPipelineRunRepository(session),
        document_reader=SqlAlchemyOcrPipelineRunDocumentReader(session),
        pipeline_reader=SqlAlchemyPublishedOcrPipelineSnapshotReader(session),
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
            dictionary_repository=SqlAlchemyDictionaryRepository(session),
        ),
        connector_display_names=connector_display_names,
    )


def _connector_display_names(manifest: ProfileManifest) -> dict[str, str]:
    return {
        instance.connector_instance_id: instance.safe_metadata.label
        for instance in manifest.connector_instances
    }
