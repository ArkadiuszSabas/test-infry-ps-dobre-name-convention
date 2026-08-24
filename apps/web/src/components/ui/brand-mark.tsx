import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
}

export function BrandMark({ className }: BrandMarkProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "relative flex size-10 items-center justify-center",
        className,
      )}
    >
      <span className="absolute size-5 translate-x-1 -translate-y-2 rounded-[5px] bg-primary/80" />
      <span className="absolute size-5 -translate-x-1 rounded-[5px] bg-primary" />
      <span className="absolute size-5 translate-x-1 translate-y-2 rounded-[5px] bg-primary/70" />
    </span>
  );
}
