import type { ReviewFieldItem } from "./types";

export interface ReviewFieldDisplayValuePresentation {
  value: string;
  isNumbered: boolean;
}

export function getReviewFieldDisplayValues(
  field: Pick<ReviewFieldItem, "displayValue" | "value"> & {
    presentationRows?: readonly (readonly string[])[];
  },
): string[] {
  return getReviewFieldDisplayValuePresentations(field).map(
    (presentation) => presentation.value,
  );
}

export function getReviewFieldDisplayValuePresentations(
  field: Pick<ReviewFieldItem, "displayValue" | "value"> & {
    presentationRows?: readonly (readonly string[])[];
  },
): ReviewFieldDisplayValuePresentation[] {
  const displayValue = field.displayValue ?? field.value;
  const tableEvidenceRows = parseTableEvidenceRows(displayValue);
  if (tableEvidenceRows !== null) {
    return coalesceDisplayValuePresentations(tableEvidenceRows);
  }

  const displayValues = getLegacyReviewDisplayValues(displayValue);
  const presentationRows = field.presentationRows
    ?.map((row) =>
      row.map((cell) => formatReviewDisplayText(cell)).filter(Boolean),
    )
    .filter((row) => row.length > 0);
  if (
    presentationRows?.length &&
    isMultiValueDisplayText(displayValue) &&
    presentationRowsMatchDisplayValue(presentationRows.flat(), displayValue)
  ) {
    return coalesceDisplayValuePresentations(
      presentationRows.map((row) => ({
        value: row.join(" · "),
        isNumbered: hasNumberedStructuralPrefix(row),
      })),
    );
  }

  return displayValues.map((value) => ({
    value,
    isNumbered: isNumberedDisplayValue(value),
  }));
}

function getLegacyReviewDisplayValues(value: string | null): string[] {
  if (value === null) return [];

  const lines = value.replaceAll("|", "\n").split(/\r?\n/);
  const parts = lines.flatMap((line) => splitInlineNumberedParts(line.trim()));
  const values: string[] = [];
  let pendingNumber: string | null = null;
  for (const [index, part] of parts.entries()) {
    const trailingNumber = part.match(/^(.*?);\s*(\d+)$/);
    if (trailingNumber && index < parts.length - 1) {
      const precedingValue = trailingNumber[1].trim();
      const valueWithPendingNumber = [pendingNumber, precedingValue]
        .filter(Boolean)
        .join(" ");
      if (valueWithPendingNumber) values.push(valueWithPendingNumber);
      pendingNumber = trailingNumber[2];
      continue;
    }

    values.push(pendingNumber ? `${pendingNumber} ${part}` : part);
    pendingNumber = null;
  }

  return coalesceStructuralFragments(
    values.map(formatReviewDisplayText),
    (item) => item,
    (_items, value) => value,
    { joinSplitNumberedPrefixes: true },
  );
}

function splitInlineNumberedParts(value: string): string[] {
  const boundaries = [0];
  for (const match of value.matchAll(/\s+(?=\d+[.)]\s+)/g)) {
    boundaries.push(match.index + match[0].length);
  }

  return boundaries
    .map((start, index) => value.slice(start, boundaries[index + 1]).trim())
    .filter(Boolean);
}

function isNumberedDisplayValue(value: string): boolean {
  return /^\d+[.)]\s/.test(value);
}

function formatReviewDisplayText(value: string): string {
  return value
    .replaceAll(":selected:", "☑")
    .replaceAll(":unselected:", "☐")
    .trim();
}

function isMultiValueDisplayText(value: string | null): boolean {
  return value !== null && /(?:\r?\n|[|;•·])/.test(value);
}

function presentationRowsMatchDisplayValue(
  presentationRows: readonly string[],
  displayValue: string | null,
): boolean {
  if (displayValue === null) return false;

  return (
    normalizeReviewDisplayText(presentationRows.join(" ")) ===
    normalizeReviewDisplayText(displayValue.replace(/(?:\r?\n|[|;•·])/g, " "))
  );
}

function normalizeReviewDisplayText(value: string): string {
  return formatReviewDisplayText(value).replace(/\s+/g, " ");
}

function parseTableEvidenceRows(
  value: string | null,
): ReviewFieldDisplayValuePresentation[] | null {
  if (value === null) return null;

  const rows: ReviewFieldDisplayValuePresentation[] = [];
  let position = 0;
  while (position < value.length) {
    const prefix = /\s*Table\s+\d+\s*,\s*row\s+\d+\s*,\s*cells\s*:\s*/y;
    prefix.lastIndex = position;
    const match = prefix.exec(value);
    if (match === null) return null;

    const cells = parseQuotedCellList(value, prefix.lastIndex);
    if (cells === null) return null;
    rows.push({
      value: cells.cells.join(" · "),
      isNumbered: hasNumberedStructuralPrefix(cells.cells),
    });

    position = skipTableEvidenceSeparator(value, cells.end);
    if (position === value.length) break;
    if (value.startsWith("Table", position)) continue;

    const trailingText = formatReviewDisplayText(value.slice(position));
    if (trailingText) {
      rows.push({
        value: trailingText,
        isNumbered: isNumberedDisplayValue(trailingText),
      });
    }
    break;
  }

  return rows.length > 0 ? rows : null;
}

function skipTableEvidenceSeparator(value: string, position: number): number {
  position = skipWhitespace(value, position);
  if (value[position] === ";") position += 1;
  return skipWhitespace(value, position);
}

function coalesceDisplayValuePresentations(
  presentations: readonly ReviewFieldDisplayValuePresentation[],
): ReviewFieldDisplayValuePresentation[] {
  return coalesceStructuralFragments(
    presentations,
    (presentation) => presentation.value,
    (mergedPresentations, value) => ({
      value,
      isNumbered:
        isNumberedDisplayValue(value) ||
        mergedPresentations.some((presentation) => presentation.isNumbered),
    }),
    { joinSplitNumberedPrefixes: true },
  );
}

function hasNumberedStructuralPrefix(cells: readonly string[]): boolean {
  const firstCell = cells[0];
  return (
    firstCell !== undefined &&
    (standaloneNumber(firstCell) !== null || isNumberedDisplayValue(firstCell))
  );
}

function parseQuotedCellList(
  value: string,
  start: number,
): { cells: string[]; end: number } | null {
  if (value[start] !== "[") return null;

  const cells: string[] = [];
  let position = start + 1;
  while (position < value.length) {
    position = skipWhitespace(value, position);
    if (value[position] === "]") {
      return cells.length > 0 ? { cells, end: position + 1 } : null;
    }

    const quote = value[position];
    if (quote !== "'" && quote !== '"') return null;
    position += 1;

    let cell = "";
    let closed = false;
    while (position < value.length) {
      const character = value[position]!;
      position += 1;
      if (character === quote) {
        closed = true;
        break;
      }
      if (character === "\\") {
        const escaped = value[position];
        if (escaped === undefined) return null;
        position += 1;
        cell += unescapeTableCellCharacter(escaped);
        continue;
      }
      cell += character;
    }
    if (!closed) return null;

    const trimmedCell = cell.trim();
    if (trimmedCell) cells.push(formatReviewDisplayText(trimmedCell));
    position = skipWhitespace(value, position);
    if (value[position] === ",") {
      position += 1;
      continue;
    }
    if (value[position] !== "]") return null;
    return cells.length > 0 ? { cells, end: position + 1 } : null;
  }

  return null;
}

function skipWhitespace(value: string, position: number): number {
  while (/\s/.test(value[position] ?? "")) position += 1;
  return position;
}

function unescapeTableCellCharacter(character: string): string {
  const escapedCharacters: Record<string, string> = {
    n: "\n",
    r: "\r",
    t: "\t",
  };
  return escapedCharacters[character] ?? character;
}

function coalesceStructuralFragments<T>(
  values: readonly T[],
  getValue: (item: T) => string,
  mergeItems: (items: readonly T[], value: string) => T,
  options: { joinSplitNumberedPrefixes?: boolean } = {},
): T[] {
  const result: T[] = [];
  for (let index = 0; index < values.length; index += 1) {
    const item = values[index]!;
    const value = getValue(item);
    const next = values[index + 1];
    const afterNext = values[index + 2];
    const nextValue = next === undefined ? undefined : getValue(next);
    const afterNextValue =
      afterNext === undefined ? undefined : getValue(afterNext);
    const number = standaloneNumber(value);

    if (
      value === "§" &&
      next !== undefined &&
      afterNext !== undefined &&
      nextValue !== undefined &&
      afterNextValue !== undefined &&
      standaloneNumber(nextValue) !== null &&
      startsWithNumberedPrefix(afterNextValue, nextValue)
    ) {
      result.push(
        mergeItems([item, next, afterNext], `${value} ${afterNextValue}`),
      );
      index += 2;
      continue;
    }

    if (
      number !== null &&
      next !== undefined &&
      nextValue !== undefined &&
      startsWithNumberedPrefix(nextValue, value)
    ) {
      if (result.at(-1) !== undefined && getValue(result.at(-1)!) === "§") {
        result[result.length - 1] = mergeItems(
          [result.at(-1)!, item, next],
          `§ ${nextValue}`,
        );
      } else {
        result.push(mergeItems([item, next], nextValue));
      }
      index += 1;
      continue;
    }

    if (
      options.joinSplitNumberedPrefixes &&
      number !== null &&
      number.length === 1 &&
      next !== undefined &&
      nextValue !== undefined &&
      startsWithSingleDigitNumberedPrefix(nextValue)
    ) {
      result.push(mergeItems([item, next], `${number}${nextValue}`));
      index += 1;
      continue;
    }

    result.push(item);
  }
  return result;
}

function standaloneNumber(value: string): string | null {
  return /^\d+$/.test(value) ? value : null;
}

function startsWithNumberedPrefix(value: string, number: string): boolean {
  return value.startsWith(`${number}.`) || value.startsWith(`${number})`);
}

function startsWithSingleDigitNumberedPrefix(value: string): boolean {
  return /^\d[.)](?:\s|$)/.test(value);
}
