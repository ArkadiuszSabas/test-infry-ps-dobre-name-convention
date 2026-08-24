import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import test from "node:test";

const SRC_ROOT = join(process.cwd(), "src");
const ICON_BUTTON_PATTERN =
  /<Button\b(?=[^>]*\bsize=(?:"icon(?:-[a-z]+)?"|\{\s*"icon(?:-[a-z]+)?"\s*\}))/g;
const ALLOWED_FILES = new Set([
  "components/ui/button.tsx",
  "components/ui/icon-tooltip-button.tsx",
]);

test("icon-only buttons use IconTooltipButton so visible tooltips are required", () => {
  const violations: string[] = [];

  for (const filePath of tsxFiles(SRC_ROOT)) {
    const relativePath = relative(SRC_ROOT, filePath).replaceAll("\\", "/");

    if (ALLOWED_FILES.has(relativePath)) {
      continue;
    }

    const content = readFileSync(filePath, "utf8");
    const matches = content.matchAll(ICON_BUTTON_PATTERN);

    for (const match of matches) {
      const line = content.slice(0, match.index).split("\n").length;
      violations.push(`${relativePath}:${line}`);
    }
  }

  assert.deepEqual(violations, []);
});

test("disabled icon tooltip wrapper does not add unnamed tab stops", () => {
  const content = readFileSync(
    join(SRC_ROOT, "components/ui/icon-tooltip-button.tsx"),
    "utf8",
  );

  assert.doesNotMatch(content, /tabIndex=\{0\}/);
});

function tsxFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((entry) => {
    const filePath = join(directory, entry);
    const stats = statSync(filePath);

    if (stats.isDirectory()) {
      return tsxFiles(filePath);
    }

    return filePath.endsWith(".tsx") ? [filePath] : [];
  });
}
