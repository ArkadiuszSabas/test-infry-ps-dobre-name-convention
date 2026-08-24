import { Badge } from "@/components/ui/badge";

export const IS_METADATA_FLAG = "isMetadata";

interface AttributeCategoryFlagBadgesProps {
  emptyLabel: string;
  flags: Record<string, boolean>;
  isMetadataLabel: string;
}

export function AttributeCategoryFlagBadges({
  emptyLabel,
  flags,
  isMetadataLabel,
}: AttributeCategoryFlagBadgesProps) {
  const activeFlags = getActiveFlagIds(flags);

  if (activeFlags.length === 0) {
    return <span className="text-muted-foreground">{emptyLabel}</span>;
  }

  return (
    <div className="flex flex-wrap gap-1">
      {activeFlags.map((flag) => (
        <Badge key={flag} variant="secondary">
          {getFlagLabel(flag, isMetadataLabel)}
        </Badge>
      ))}
    </div>
  );
}

function getActiveFlagIds(flags: Record<string, boolean>) {
  return Object.entries(flags)
    .filter(([, enabled]) => enabled)
    .map(([flag]) => flag)
    .sort();
}

function getFlagLabel(flag: string, isMetadataLabel: string) {
  if (flag === IS_METADATA_FLAG) {
    return isMetadataLabel;
  }

  return flag.replaceAll("_", " ");
}
