import { FileText } from "lucide-react";
import { attachmentRawUrl, type AttachmentRef } from "../services/api";

/** Attachment previews inside a sent user message: thumbnails for images,
 * filename cards for documents. */
export default function AttachmentChips({
  attachments,
}: {
  attachments: AttachmentRef[];
}) {
  if (!attachments.length) return null;
  return (
    <div className="mb-2 flex flex-wrap gap-2">
      {attachments.map((a) =>
        a.kind === "image" ? (
          <img
            key={a.id}
            src={attachmentRawUrl(a.id)}
            alt={a.filename}
            title={a.filename}
            className="h-16 w-16 rounded-lg border border-white/20 object-cover"
          />
        ) : (
          <span
            key={a.id}
            className="inline-flex max-w-[220px] items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-2.5 py-1.5"
            title={a.filename}
          >
            <FileText className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate text-xs">{a.filename}</span>
          </span>
        ),
      )}
    </div>
  );
}
