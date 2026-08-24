import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import test from "node:test";

const SRC_ROOT = join(process.cwd(), "src");
const PASSWORD_INPUT_PATH = "components/ui/password-input.tsx";
const RAW_PASSWORD_TYPE_PATTERN =
  /type\s*=\s*(?:["']password["']|\{\s*["']password["']\s*\})/;

test("all password fields use the shared visibility control", () => {
  const violations = tsxFiles(SRC_ROOT)
    .map((filePath) => ({
      content: readFileSync(filePath, "utf8"),
      path: relative(SRC_ROOT, filePath).replaceAll("\\", "/"),
    }))
    .filter(
      ({ content, path }) =>
        path !== PASSWORD_INPUT_PATH && RAW_PASSWORD_TYPE_PATTERN.test(content),
    )
    .map(({ path }) => path);

  assert.deepEqual(violations, []);
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
