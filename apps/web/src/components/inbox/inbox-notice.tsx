import { Notice } from "@/components/ui/notice";

export interface InboxNoticeProps {
  description?: string;
  title: string;
  tone?: "default" | "danger";
}

export function InboxNotice({
  description,
  title,
  tone = "default",
}: InboxNoticeProps) {
  return <Notice description={description} title={title} tone={tone} />;
}
