import assert from "node:assert/strict";
import test from "node:test";

import { archiveFolderUrl } from "./archive-url";

test("builds the SharePoint folder URL from a document permalink", () => {
  assert.equal(
    archiveFolderUrl(
      "https://tenant.sharepoint.com/sites/archive/Shared%20Documents/2026/C-100/invoice.pdf?web=1",
    ),
    "https://tenant.sharepoint.com/sites/archive/Shared%20Documents/2026/C-100/",
  );
});
