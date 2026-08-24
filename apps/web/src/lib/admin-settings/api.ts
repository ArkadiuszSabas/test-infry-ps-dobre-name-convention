import { systemCatalogClient } from "@/lib/system-catalogs/api";

import { attributeCatalogClient } from "./attribute-api";
import { attributeRequirementsCatalogClient } from "./attribute-requirements-api";
import { dictionaryCatalogClient } from "./dictionary-api";
import { documentTypeCatalogClient } from "./document-type-api";

export const adminCatalogClient = {
  ...dictionaryCatalogClient,
  ...documentTypeCatalogClient,
  ...systemCatalogClient,
  ...attributeCatalogClient,
  ...attributeRequirementsCatalogClient,
};
