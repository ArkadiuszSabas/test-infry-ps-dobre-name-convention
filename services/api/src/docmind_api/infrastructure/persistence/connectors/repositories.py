"""PostgreSQL repository for connector configuration."""

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.domain.connectors.configuration import ConnectorInstanceConfiguration
from docmind_api.infrastructure.persistence.connectors.tables import (
    connector_instance_configurations_table,
)


class SqlAlchemyConnectorConfigurationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, connector_instance_id: str) -> ConnectorInstanceConfiguration | None:
        row = (
            (
                await self._session.execute(
                    select(connector_instance_configurations_table).where(
                        connector_instance_configurations_table.c.connector_instance_id
                        == connector_instance_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        return _record(row) if row is not None else None

    async def save(
        self,
        value: ConnectorInstanceConfiguration,
        *,
        expected_updated_at: datetime | None,
        expected_api_key_hash: str | None,
    ) -> ConnectorInstanceConfiguration | None:
        values = {
            "values": dict(value.values),
            "api_key_salt": value.api_key_salt,
            "api_key_hash": value.api_key_hash,
            "updated_at": value.updated_at,
        }
        if expected_updated_at is None:
            statement = (
                insert(connector_instance_configurations_table)
                .values(
                    connector_instance_id=value.connector_instance_id,
                    created_at=value.created_at,
                    **values,
                )
                .on_conflict_do_nothing()
                .returning(connector_instance_configurations_table)
            )
        else:
            statement = (
                update(connector_instance_configurations_table)
                .where(
                    connector_instance_configurations_table.c.connector_instance_id
                    == value.connector_instance_id,
                    connector_instance_configurations_table.c.updated_at == expected_updated_at,
                    connector_instance_configurations_table.c.api_key_hash == expected_api_key_hash,
                )
                .values(**values)
                .returning(connector_instance_configurations_table)
            )
        row = (await self._session.execute(statement)).mappings().one_or_none()
        return _record(row) if row is not None else None


def _record(row: RowMapping) -> ConnectorInstanceConfiguration:
    raw_values = row["values"]
    values: Mapping[object, object]
    if isinstance(raw_values, Mapping):
        values = cast(Mapping[object, object], raw_values)
    else:
        values = {}
    return ConnectorInstanceConfiguration(
        connector_instance_id=str(row["connector_instance_id"]),
        values={str(key): str(value) for key, value in values.items()},
        api_key_salt=str(row["api_key_salt"]) if row["api_key_salt"] is not None else None,
        api_key_hash=str(row["api_key_hash"]) if row["api_key_hash"] is not None else None,
        created_at=cast(datetime, row["created_at"]),
        updated_at=cast(datetime, row["updated_at"]),
    )
