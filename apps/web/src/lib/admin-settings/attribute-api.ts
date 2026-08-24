import { apiFetch } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";

import {
  withSearchParams,
  type AdminCatalogRequestOptions,
} from "./api-helpers";
import type {
  AttributeCategory,
  AttributeCategoryDto,
  AttributeCategoryEnvelopeDto,
  AttributeCategoryListEnvelope,
  AttributeCategoryListEnvelopeDto,
  AttributeDefinition,
  AttributeDefinitionDto,
  AttributeEnvelopeDto,
  AttributeListEnvelope,
  AttributeListEnvelopeDto,
  CatalogStatusFilter,
  DeleteCatalogEntryEnvelope,
  DeleteCatalogEntryResult,
  UpdateAttributeCategoryInput,
  UpdateAttributeInput,
  UpsertAttributeCategoryInput,
  UpsertAttributeInput,
} from "./types";

export interface ListAttributesOptions extends AdminCatalogRequestOptions {
  category?: string | null;
}

export interface ListAttributeCategoriesOptions extends AdminCatalogRequestOptions {
  status: CatalogStatusFilter;
}

export const attributeCatalogClient = {
  async listAttributes(
    options: ListAttributesOptions = {},
  ): Promise<AttributeListEnvelope> {
    return mapAttributeListEnvelope(
      await apiFetch<AttributeListEnvelopeDto>(
        withSearchParams("/attributes", { category: options.category }),
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async listAttributeCategories(
    options: ListAttributeCategoriesOptions,
  ): Promise<AttributeCategoryListEnvelope> {
    return mapAttributeCategoryListEnvelope(
      await apiFetch<AttributeCategoryListEnvelopeDto>(
        withSearchParams("/attributes/categories", { status: options.status }),
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async createAttributeCategory(
    input: UpsertAttributeCategoryInput,
    options: AdminCatalogRequestOptions = {},
  ): Promise<AttributeCategory> {
    return mapAttributeCategory(
      unwrapEnvelope(
        await apiFetch<AttributeCategoryEnvelopeDto>("/attributes/categories", {
          csrfToken: options.csrfToken,
          json: {
            ...(input.externalId ? { external_id: input.externalId } : {}),
            flags: input.flags,
            label: input.label,
          },
          method: "POST",
          signal: options.signal,
        }),
      ),
    );
  },

  async updateAttributeCategory(
    categoryId: string,
    input: UpdateAttributeCategoryInput,
    options: AdminCatalogRequestOptions = {},
  ): Promise<AttributeCategory> {
    return mapAttributeCategory(
      unwrapEnvelope(
        await apiFetch<AttributeCategoryEnvelopeDto>(
          `/attributes/categories/${encodeURIComponent(categoryId)}`,
          {
            csrfToken: options.csrfToken,
            json: {
              flags: input.flags,
              label: input.label,
            },
            method: "PATCH",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deactivateAttributeCategory(
    categoryId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<AttributeCategory> {
    return mapAttributeCategory(
      unwrapEnvelope(
        await apiFetch<AttributeCategoryEnvelopeDto>(
          `/attributes/categories/${encodeURIComponent(categoryId)}/deactivate`,
          {
            csrfToken: options.csrfToken,
            method: "POST",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deleteAttributeCategory(
    categoryId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DeleteCatalogEntryResult> {
    return unwrapEnvelope(
      await apiFetch<DeleteCatalogEntryEnvelope>(
        `/attributes/categories/${encodeURIComponent(categoryId)}`,
        {
          csrfToken: options.csrfToken,
          method: "DELETE",
          signal: options.signal,
        },
      ),
    );
  },

  async createAttribute(
    input: UpsertAttributeInput,
    options: AdminCatalogRequestOptions = {},
  ): Promise<AttributeDefinition> {
    return mapAttributeDefinition(
      unwrapEnvelope(
        await apiFetch<AttributeEnvelopeDto>("/attributes", {
          csrfToken: options.csrfToken,
          json: {
            allowed_values: input.allowedValues,
            category_id: input.categoryId,
            comment: input.comment,
            llm_context: input.llmContext,
            constraints: input.constraints,
            data_type: input.dataType,
            dictionary_id: input.dictionaryId,
            ...(input.externalId ? { external_id: input.externalId } : {}),
            name: input.name,
            source: input.source,
            value_source: input.valueSource,
          },
          method: "POST",
          signal: options.signal,
        }),
      ),
    );
  },

  async updateAttribute(
    attributeId: string,
    input: UpdateAttributeInput,
    options: AdminCatalogRequestOptions = {},
  ): Promise<AttributeDefinition> {
    return mapAttributeDefinition(
      unwrapEnvelope(
        await apiFetch<AttributeEnvelopeDto>(
          `/attributes/${encodeURIComponent(attributeId)}`,
          {
            csrfToken: options.csrfToken,
            json: {
              allowed_values: input.allowedValues,
              category_id: input.categoryId,
              comment: input.comment,
              ...(input.llmContext !== undefined
                ? { llm_context: input.llmContext }
                : {}),
              constraints: input.constraints,
              ...(input.dataType ? { data_type: input.dataType } : {}),
              dictionary_id: input.dictionaryId,
              external_id: input.externalId,
              name: input.name,
              source: input.source,
              value_source: input.valueSource,
            },
            method: "PATCH",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deactivateAttribute(
    attributeId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<AttributeDefinition> {
    return mapAttributeDefinition(
      unwrapEnvelope(
        await apiFetch<AttributeEnvelopeDto>(
          `/attributes/${encodeURIComponent(attributeId)}/deactivate`,
          {
            csrfToken: options.csrfToken,
            method: "POST",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async deleteAttribute(
    attributeId: string,
    options: AdminCatalogRequestOptions = {},
  ): Promise<DeleteCatalogEntryResult> {
    return unwrapEnvelope(
      await apiFetch<DeleteCatalogEntryEnvelope>(
        `/attributes/${encodeURIComponent(attributeId)}`,
        {
          csrfToken: options.csrfToken,
          method: "DELETE",
          signal: options.signal,
        },
      ),
    );
  },
};

function mapAttributeListEnvelope(
  envelope: AttributeListEnvelopeDto,
): AttributeListEnvelope {
  return {
    data: {
      attributes: envelope.data.attributes.map(mapAttributeDefinition),
    },
    meta: {
      categoryCounts: envelope.meta.category_counts,
      totalCount: envelope.meta.total_count,
    },
  };
}

function mapAttributeDefinition(
  attribute: AttributeDefinitionDto,
): AttributeDefinition {
  return {
    allowedValues: attribute.allowed_values,
    category: attribute.category,
    categoryId: attribute.category_id,
    comment: attribute.comment,
    llmContext: attribute.llm_context,
    constraints: attribute.constraints,
    createdAt: attribute.created_at,
    dataType: attribute.data_type,
    dictionaryId: attribute.dictionary_id,
    externalId: attribute.external_id,
    id: attribute.id,
    name: attribute.name,
    schemaVersion: attribute.schema_version,
    source: attribute.source,
    status: attribute.status,
    updatedAt: attribute.updated_at,
    valueSource: attribute.value_source,
  };
}

function mapAttributeCategoryListEnvelope(
  envelope: AttributeCategoryListEnvelopeDto,
): AttributeCategoryListEnvelope {
  return {
    data: {
      categories: envelope.data.categories.map(mapAttributeCategory),
    },
    meta: {
      activeCount: envelope.meta.active_count,
      inactiveCount: envelope.meta.inactive_count,
      returnedCount: envelope.meta.returned_count,
      status: envelope.meta.status,
      totalCount: envelope.meta.total_count,
    },
  };
}

function mapAttributeCategory(
  category: AttributeCategoryDto,
): AttributeCategory {
  return {
    externalId: category.external_id,
    flags: category.flags,
    id: category.id,
    label: category.label,
    status: category.status,
    createdAt: category.created_at,
    updatedAt: category.updated_at,
  };
}
