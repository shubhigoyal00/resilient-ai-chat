import {
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { ArrowUp, FileText, Loader2, Paperclip, X } from "lucide-react";
import {
  ApiError,
  attachmentRawUrl,
  uploadAttachment,
  type AttachmentRef,
} from "../services/api";

const ACCEPT = ".jpg,.jpeg,.png,.webp,.pdf,.docx,.txt";
const MAX_ATTACHMENTS = 5;

export interface PendingAttachment extends AttachmentRef {
  status: "uploading" | "ready" | "error";
  error?: string;
  localPreview?: string;
}

interface Props {
  onSend: (message: string, attachments: AttachmentRef[]) => Promise<boolean>;
  disabled: boolean;
  sessionId: string;
}

export default function Composer({ onSend, disabled, sessionId }: Props) {
  const [value, setValue] = useState("");
  const [pending, setPending] = useState<PendingAttachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const uploading = pending.some((p) => p.status === "uploading");
  const ready = pending.filter((p) => p.status === "ready");

  const handleFiles = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    e.target.value = ""; // allow re-selecting the same file
    const slots = MAX_ATTACHMENTS - pending.length;
    for (const file of files.slice(0, Math.max(0, slots))) {
      void processFile(file);
    }
  };

  const processFile = async (file: File) => {
    const tempId = `tmp-${crypto.randomUUID?.() ?? Date.now()}`;
    const localPreview = file.type.startsWith("image/")
      ? URL.createObjectURL(file)
      : undefined;
    setPending((prev) => [
      ...prev,
      {
        id: tempId,
        filename: file.name,
        mime_type: file.type || "application/octet-stream",
        kind: file.type.startsWith("image/") ? "image" : "document",
        status: "uploading",
        localPreview,
      },
    ]);
    try {
      const uploaded = await uploadAttachment(sessionId, file);
      setPending((prev) =>
        prev.map((p) =>
          p.id === tempId
            ? {
                id: uploaded.attachment_id,
                filename: uploaded.filename,
                mime_type: uploaded.mime_type,
                kind: uploaded.kind,
                status: "ready",
                localPreview,
              }
            : p,
        ),
      );
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Upload failed — try again";
      setPending((prev) =>
        prev.map((p) =>
          p.id === tempId ? { ...p, status: "error", error: detail } : p,
        ),
      );
    }
  };

  const removeAttachment = (id: string) =>
    setPending((prev) => prev.filter((p) => p.id !== id));

  const submit = async (e?: FormEvent) => {
    e?.preventDefault();
    const text = value.trim();
    if ((!text && !ready.length) || disabled || uploading) return;
    const sent = await onSend(
      text || "Please analyze the attached file(s).",
      ready.map(({ id, filename, mime_type, kind }) => ({
        id,
        filename,
        mime_type,
        kind,
      })),
    );
    if (sent) {
      setValue("");
      setPending([]);
      if (textareaRef.current) textareaRef.current.style.height = "auto";
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  };

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <form
      onSubmit={submit}
      className="border-t border-slate-800/70 bg-[#0a0e1a]/80 px-4 py-3.5 backdrop-blur sm:px-6"
    >
      <div className="mx-auto max-w-3xl">
        {pending.length > 0 && (
          <div className="mb-2.5 flex flex-wrap gap-2">
            {pending.map((p) => (
              <div
                key={p.id}
                title={p.error ?? p.filename}
                className={`group relative flex items-center gap-2 rounded-xl border px-2.5 py-1.5 text-xs ${
                  p.status === "error"
                    ? "border-red-500/50 bg-red-500/10 text-red-300"
                    : "border-slate-700 bg-slate-800/70 text-slate-300"
                }`}
              >
                {p.status === "uploading" && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-400" />
                )}
                {p.kind === "image" ? (
                  <img
                    src={p.localPreview ?? attachmentRawUrl(p.id)}
                    alt={p.filename}
                    className="h-8 w-8 rounded-md object-cover"
                  />
                ) : (
                  <FileText className="h-4 w-4 text-indigo-400" />
                )}
                <span className="max-w-[140px] truncate">{p.filename}</span>
                {p.status === "error" && (
                  <span className="max-w-[160px] truncate text-[10px] text-red-400">
                    {p.error}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => removeAttachment(p.id)}
                  aria-label={`Remove ${p.filename}`}
                  className="rounded-md p-0.5 text-slate-500 transition hover:bg-slate-700 hover:text-slate-200"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2.5">
          <div className="flex flex-1 items-end rounded-2xl border border-slate-700/70 bg-slate-900/80 transition focus-within:border-indigo-500/50 focus-within:ring-2 focus-within:ring-indigo-500/20">
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPT}
              multiple
              onChange={handleFiles}
              className="hidden"
            />
            <button
              type="button"
              data-testid="attach-button"
              onClick={() => fileRef.current?.click()}
              disabled={disabled || pending.length >= MAX_ATTACHMENTS}
              aria-label="Attach a file"
              title="Attach image or document (JPG, PNG, WEBP, PDF, DOCX, TXT)"
              className="m-1.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-800 hover:text-indigo-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Paperclip className="h-4 w-4" />
            </button>
            <textarea
              ref={textareaRef}
              data-testid="chat-input"
              value={value}
              onChange={(e) => {
                setValue(e.target.value);
                autoResize();
              }}
              onKeyDown={onKeyDown}
              placeholder="Message Resilient AI…"
              disabled={disabled}
              maxLength={4000}
              rows={1}
              className="scroll-slim max-h-40 flex-1 resize-none bg-transparent px-2 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none disabled:opacity-60"
            />
            <button
              data-testid="send-button"
              type="submit"
              disabled={disabled || uploading || (!value.trim() && !ready.length)}
              aria-label="Send message"
              className="m-1.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-md shadow-indigo-950/40 transition hover:from-indigo-400 hover:to-violet-500 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 disabled:cursor-not-allowed disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-500 disabled:shadow-none"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
        </div>
        <p className="mt-2 text-center text-[10px] text-slate-600">
          Enter to send · Shift+Enter for a new line · JPG, PNG, WEBP, PDF,
          DOCX, TXT
        </p>
      </div>
    </form>
  );
}
