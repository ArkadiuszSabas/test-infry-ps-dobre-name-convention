import type { ReactNode } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { TableCell, TableRow } from "@/components/ui/table";

interface TableEmptyStateProps {
  columns: number;
  description?: ReactNode;
  title: ReactNode;
}

export function TableEmptyState({
  columns,
  description,
  title,
}: TableEmptyStateProps) {
  return (
    <TableRow className="hover:bg-transparent">
      <TableCell className="whitespace-normal p-6" colSpan={columns}>
        <EmptyState description={description} title={title} />
      </TableCell>
    </TableRow>
  );
}
