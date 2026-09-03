"""Map Context Resolver pipeline payloads to document review read models."""

from collections.abc import Mapping, Sequence
from typing import Any, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.application.document_review.read_models import (
    DocumentReviewAttribute,
    DocumentReviewAttributeKind,
    DocumentReviewAttributeSource,
    DocumentReviewAttributeStatus,
    DocumentReviewConsistencyStatus,
    DocumentReviewCoordinateSystem,
    DocumentReviewDataSource,
    DocumentReviewProcessingStatus,
    DocumentReviewResult,
    DocumentReviewValueSource,
)
from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.infrastructure.document_review.consistency_mapper import (
    has_invalid_consistency_metadata,
    review_consistency_from_context_attribute,
)

CONTEXT_RESOLUTION_RESULT_PAYLOAD_KEY = "context_resolution_result"
_CONTEXT_RESOLUTION_MISSING_REASON = "CONTEXT_RESOLUTION_RESULT_MISSING"
_CONTEXT_RESOLUTION_FAILED_REASON = "CONTEXT_RESOLUTION_FAILED"
_CONTEXT_RESOLUTION_INVALID_REASON = "CONTEXT_RESOLUTION_RESULT_INVALID"
_CONTEXT_RESOLUTION_ATTRIBUTES_MISSING_REASON = "CONTEXT_RESOLUTION_ATTRIBUTES_MISSING"
_MAX_ATTRIBUTE_COUNT = 500
_MAX_SOURCE_COUNT = 16
_MAX_REASON_CODE_COUNT = 16
_MAX_LABEL_LENGTH = 200
_MAX_EXTERNAL_ID_LENGTH = 128
_MAX_VALUE_LENGTH = 4_000

_STATUS_BY_VALUE = {
    "present": DocumentReviewAttributeStatus.PRESENT,
    "missing": DocumentReviewAttributeStatus.MISSING,
    "uncertain": DocumentReviewAttributeStatus.UNCERTAIN,
    "conflicting": DocumentReviewAttributeStatus.CONFLICTING,
}
_DATA_TYPE_ALIASES = {
    "amount": AttributeDataType.NUMBER,
    "currency": AttributeDataType.NUMBER,
    "decimal": AttributeDataType.NUMBER,
    "money": AttributeDataType.NUMBER,
    "float": AttributeDataType.NUMBER,
    "int": AttributeDataType.INTEGER,
    "bool": AttributeDataType.BOOLEAN,
    "text": AttributeDataType.STRING,
}
_SOURCE_KIND_BY_VALUE = {
    "ocr_key_value": "ocr_key_value_pair",
    "ocr_line": "ocr_line",
    # Keep the existing Review sorting contract while direct polygons retain the
    # exact structured location or an honest whole-page document fallback.
    "ocr_selection_mark": "ocr_line",
    "ocr_table_cell": "ocr_line",
    "ocr_document": "ocr_line",
}


def review_result_from_context_resolution_payload(
    *,
    document_id: UUID,
    payload: Mapping[str, object] | None,
    source_pipeline_run_id: UUID | None = None,
) -> DocumentReviewResult:
    """Map a stored OCR run payload containing Context Resolver output to review data."""

    context_payload = _context_resolution_payload(payload)
    if context_payload is None:
        return _unavailable_result(
            document_id=document_id,
            processing_status=DocumentReviewProcessingStatus.NOT_AVAILABLE,
            reason_code=_CONTEXT_RESOLUTION_MISSING_REASON,
        )

    status = _optional_text(context_payload.get("status"))
    if status not in {"succeeded", "partial_failed", "failed"}:
        return _unavailable_result(
            document_id=document_id,
            processing_status=DocumentReviewProcessingStatus.FAILED,
            reason_code=_CONTEXT_RESOLUTION_INVALID_REASON,
        )
    if status == "failed":
        return _unavailable_result(
            document_id=document_id,
            processing_status=DocumentReviewProcessingStatus.FAILED,
            reason_code=_CONTEXT_RESOLUTION_FAILED_REASON,
        )

    raw_attributes = _sequence(context_payload.get("attributes"))[:_MAX_ATTRIBUTE_COUNT]
    if any(_has_invalid_consistency_metadata(raw_attribute) for raw_attribute in raw_attributes):
        return _unavailable_result(
            document_id=document_id,
            processing_status=DocumentReviewProcessingStatus.FAILED,
            reason_code=_CONTEXT_RESOLUTION_INVALID_REASON,
        )

    attributes = tuple(
        mapped_attribute
        for index, raw_attribute in enumerate(raw_attributes)
        if (
            mapped_attribute := _review_attribute(
                document_id=document_id,
                index=index,
                raw_attribute=raw_attribute,
                root_payload=payload or {},
            )
        )
        is not None
    )
    return DocumentReviewResult(
        schema_version=2,
        document_id=document_id,
        data_source=DocumentReviewDataSource.PIPELINE,
        processing_status=DocumentReviewProcessingStatus.COMPLETED,
        attributes_available=bool(attributes),
        unavailable_reason_code=None
        if attributes
        else _CONTEXT_RESOLUTION_ATTRIBUTES_MISSING_REASON,
        attributes=attributes,
        source_pipeline_run_id=source_pipeline_run_id,
    )


def _has_invalid_consistency_metadata(raw_attribute: object) -> bool:
    attribute = _mapping(raw_attribute)
    return attribute is not None and has_invalid_consistency_metadata(attribute)


def _review_attribute(
    *,
    document_id: UUID,
    index: int,
    raw_attribute: object,
    root_payload: Mapping[str, object],
) -> DocumentReviewAttribute | None:
    attribute_payload = _mapping(raw_attribute)
    if attribute_payload is None:
        return None

    external_id = _optional_text(
        attribute_payload.get("attribute_external_id"),
        max_length=_MAX_EXTERNAL_ID_LENGTH,
    )
    label = (
        _optional_text(
            attribute_payload.get("display_name"),
            max_length=_MAX_LABEL_LENGTH,
        )
        or external_id
    )
    if label is None:
        return None

    value = _optional_text(attribute_payload.get("value"), max_length=_MAX_VALUE_LENGTH)
    status = _attribute_status(attribute_payload.get("status"), value=value)
    consistency = review_consistency_from_context_attribute(attribute_payload)
    required = _strict_bool(attribute_payload.get("required"))
    reason_codes = _reason_codes(attribute_payload.get("reason_codes"))
    manual_input = "MANUAL_INPUT_REQUIRED" in reason_codes
    requires_review = (
        _strict_bool(attribute_payload.get("requires_review"))
        or (required and status != DocumentReviewAttributeStatus.PRESENT)
        or (required and bool(reason_codes))
        or consistency.status == DocumentReviewConsistencyStatus.CONFLICTING
    )
    return DocumentReviewAttribute(
        id=_stable_result_id(
            document_id=document_id, attribute_key=external_id or label, index=index
        ),
        kind=DocumentReviewAttributeKind.CONFIGURED
        if external_id is not None
        else DocumentReviewAttributeKind.UNIDENTIFIED,
        attribute_id=_uuid_or_none(attribute_payload.get("attribute_id")),
        attribute_external_id=external_id,
        label=label,
        data_type=_attribute_data_type(attribute_payload.get("value_type")),
        required=required,
        display_order=(index + 1) * 10,
        value=value,
        display_value=value,
        confidence=_confidence(attribute_payload.get("confidence_score")),
        status=status,
        requires_review=requires_review,
        review_reason_codes=reason_codes,
        sources=_review_sources(attribute_payload.get("sources"), root_payload=root_payload),
        consistency=consistency,
        value_source=(
            DocumentReviewValueSource.MANUAL if manual_input else DocumentReviewValueSource.PIPELINE
        ),
    )


def _review_sources(
    value: object,
    *,
    root_payload: Mapping[str, object],
) -> tuple[DocumentReviewAttributeSource, ...]:
    sources: list[DocumentReviewAttributeSource] = []
    for raw_source in _sequence(value)[:_MAX_SOURCE_COUNT]:
        source = _review_source(raw_source, root_payload=root_payload)
        if source is not None:
            sources.append(source)
    return tuple(sources)


def _review_source(
    value: object,
    *,
    root_payload: Mapping[str, object],
) -> DocumentReviewAttributeSource | None:
    source_payload = _mapping(value)
    if source_payload is None:
        return None

    source_kind = _optional_text(source_payload.get("kind"), max_length=64)
    page_number = _positive_int(source_payload.get("page_number"))
    order_index = _source_order_index(source_payload)
    polygon = _normalized_polygon(source_payload.get("bounding_polygon"))
    source_key = _optional_text(source_payload.get("source_key"), max_length=1_000)
    confidence = _confidence(source_payload.get("confidence"))

    if polygon is None and source_kind == "ocr_key_value":
        key_value_pair = _matching_key_value_pair(source_payload, root_payload=root_payload)
        if key_value_pair is None:
            return None
        polygon = _normalized_polygon(key_value_pair.get("bounding_polygon"))
        page_number = page_number or _positive_int(key_value_pair.get("page_number"))
        order_index = (
            order_index if order_index is not None else _source_order_index(key_value_pair)
        )
        source_key = source_key or _optional_text(key_value_pair.get("key"), max_length=1_000)
        confidence = (
            confidence if confidence is not None else _confidence(key_value_pair.get("confidence"))
        )

    if page_number is None or (polygon is None and source_kind != "ocr_line"):
        return None

    return DocumentReviewAttributeSource(
        kind=_review_source_kind(source_kind),
        page_number=page_number,
        order_index=order_index or 0,
        coordinate_system=DocumentReviewCoordinateSystem.NORMALIZED_0_1,
        bounding_polygon=polygon,
        confidence=confidence,
        source_key=source_key,
    )


def _matching_key_value_pair(
    source_payload: Mapping[str, object],
    *,
    root_payload: Mapping[str, object],
) -> Mapping[str, object] | None:
    page_number = _positive_int(source_payload.get("page_number"))
    key_value_index = _positive_int(source_payload.get("key_value_index"))
    if page_number is None or key_value_index is None:
        return None

    ocr_payload = _ocr_payload(root_payload)
    for raw_pair in _sequence(ocr_payload.get("key_value_pairs")):
        pair = _mapping(raw_pair)
        if pair is None:
            continue
        if (
            _positive_int(pair.get("page_number")) == page_number
            and _positive_int(pair.get("order_index")) == key_value_index
        ):
            return pair
    return None


def _context_resolution_payload(
    payload: Mapping[str, object] | None,
) -> Mapping[str, object] | None:
    if payload is None:
        return None

    nested = _mapping(payload.get(CONTEXT_RESOLUTION_RESULT_PAYLOAD_KEY))
    if nested is not None:
        return nested
    if "attributes" in payload and "status" in payload:
        return payload
    return None


def _ocr_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    nested = _mapping(payload.get("ocr_result"))
    return nested or payload


def _unavailable_result(
    *,
    document_id: UUID,
    processing_status: DocumentReviewProcessingStatus,
    reason_code: str,
) -> DocumentReviewResult:
    return DocumentReviewResult(
        schema_version=1,
        document_id=document_id,
        data_source=DocumentReviewDataSource.PIPELINE,
        processing_status=processing_status,
        attributes_available=False,
        unavailable_reason_code=reason_code,
        attributes=(),
    )


def _stable_result_id(*, document_id: UUID, attribute_key: str, index: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"docmind:document-review:{document_id}:{attribute_key}:{index}")


def _attribute_status(raw_status: object, *, value: str | None) -> DocumentReviewAttributeStatus:
    status = _optional_text(raw_status)
    if status is not None and status in _STATUS_BY_VALUE:
        return _STATUS_BY_VALUE[status]
    if value is None:
        return DocumentReviewAttributeStatus.MISSING
    return DocumentReviewAttributeStatus.UNCERTAIN


def _attribute_data_type(value: object) -> AttributeDataType:
    raw_value = _optional_text(value, max_length=64)
    if raw_value is None:
        return AttributeDataType.STRING

    normalized = raw_value.lower()
    if normalized in _DATA_TYPE_ALIASES:
        return _DATA_TYPE_ALIASES[normalized]
    try:
        return AttributeDataType(normalized)
    except ValueError:
        return AttributeDataType.STRING


def _review_source_kind(value: str | None) -> str:
    if value is None:
        return "ocr_source"
    return _SOURCE_KIND_BY_VALUE.get(value, value)


def _source_order_index(payload: Mapping[str, object]) -> int | None:
    order_index = _non_negative_int(payload.get("order_index"))
    if order_index is not None:
        return order_index
    return _positive_int(payload.get("key_value_index")) or _positive_int(
        payload.get("line_number")
    )


def _reason_codes(value: object) -> tuple[str, ...]:
    codes: list[str] = []
    for raw_code in _sequence(value)[:_MAX_REASON_CODE_COUNT]:
        code = _optional_text(raw_code, max_length=80)
        if code is not None and code.replace("_", "").isalnum() and code[0].isalpha():
            codes.append(code.upper())
    return tuple(dict.fromkeys(codes))


def _normalized_polygon(value: object) -> tuple[float, ...] | None:
    items = _sequence(value)
    if len(items) < 8 or len(items) > 16 or len(items) % 2 != 0:
        return None

    coordinates: list[float] = []
    for item in items:
        if isinstance(item, bool) or not isinstance(item, int | float):
            return None
        coordinate = float(item)
        if coordinate < 0 or coordinate > 1:
            return None
        coordinates.append(round(coordinate, 6))
    return tuple(coordinates)


def _confidence(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return round(max(0.0, min(1.0, float(value))), 6)


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _strict_bool(value: object) -> bool:
    return value if isinstance(value, bool) else False


def _uuid_or_none(value: object) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _optional_text(value: object, *, max_length: int = 1_000) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped[:max_length]


def _mapping(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    return cast(Mapping[str, object], value)


def _sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(cast(Sequence[Any], value))
    return ()
