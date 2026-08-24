import { ArrowLeftIcon } from "lucide-react";
import type { ComponentProps } from "react";

import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";

interface PageBackLinkProps {
  children: string;
  className?: string;
  href: ComponentProps<typeof Link>["href"];
}

export function PageBackLink({ children, className, href }: PageBackLinkProps) {
  return (
    <Button asChild className={className} variant="ghost">
      <Link href={href}>
        <ArrowLeftIcon data-icon="inline-start" />
        {children}
      </Link>
    </Button>
  );
}
