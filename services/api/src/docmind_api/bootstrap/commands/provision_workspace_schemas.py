"""One-shot API-migrator command for durable workspace-schema preparation."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from docmind_api.infrastructure.persistence.sql import create_database_engine
from docmind_api.infrastructure.persistence.workspaces.provisioning import (
    WorkspaceProvisioningConnectionLostError,
    WorkspaceProvisioningOutcome,
    WorkspaceProvisioningResult,
    provision_workspace_requests,
)
from docmind_api.settings import get_database_migration_settings, get_database_settings


class WorkspaceSchemaProvisioner(Protocol):
    """Command dependency that executes selected durable requests."""

    async def __call__(
        self,
        *,
        request_id: UUID | None,
    ) -> tuple[WorkspaceProvisioningResult, ...]: ...


def main(
    argv: Sequence[str] | None = None,
    *,
    provisioner: WorkspaceSchemaProvisioner | None = None,
) -> int:
    """Run a specified durable request or drain pending requests sequentially."""

    args = _build_parser().parse_args(argv)
    command_provisioner = provisioner or provision_workspace_schemas
    try:
        results = asyncio.run(command_provisioner(request_id=args.request_id))
    except WorkspaceProvisioningConnectionLostError:
        sys.stderr.write("Workspace provisioning stopped without recording an outcome.\n")
        return 2
    except Exception:
        sys.stderr.write("Workspace provisioning command failed.\n")
        return 2

    _write_summary(results)
    return int(any(result.outcome is WorkspaceProvisioningOutcome.FAILED for result in results))


async def provision_workspace_schemas(
    *,
    request_id: UUID | None,
) -> tuple[WorkspaceProvisioningResult, ...]:
    """Compose the migrator-only engine and transactional provisioning adapter."""

    engine = create_database_engine(get_database_settings())
    try:
        migration_settings = get_database_migration_settings()
        return await provision_workspace_requests(
            engine=engine,
            request_id=request_id,
            runtime_principal_name=migration_settings.runtime_principal_name,
        )
    finally:
        await engine.dispose()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare registered workspace schemas through the API migrator identity.",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--request-id",
        type=UUID,
        help="Execute exactly one durable provisioning request.",
    )
    selection.add_argument(
        "--pending",
        action="store_true",
        help="Drain pending requests in creation order (the default).",
    )
    return parser


def _write_summary(results: tuple[WorkspaceProvisioningResult, ...]) -> None:
    counts = {outcome: 0 for outcome in WorkspaceProvisioningOutcome}
    for result in results:
        counts[result.outcome] += 1
    sys.stdout.write(
        "Workspace provisioning completed. "
        f"succeeded={counts[WorkspaceProvisioningOutcome.SUCCEEDED]} "
        f"failed={counts[WorkspaceProvisioningOutcome.FAILED]} "
        f"already_completed={counts[WorkspaceProvisioningOutcome.ALREADY_COMPLETED]}\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
