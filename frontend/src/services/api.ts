const BASE_URL: string = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type ResolutionSource = "LIVE_INFERENCE" | "LLM_CACHE";

export interface ChatMetadata {
  resolution_source: ResolutionSource;
  model: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  key_id: string | null;
  fallback_attempts: number;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  metadata: ChatMetadata;
}

/** Attachment reference stored on user messages / used for rendering. */
export interface AttachmentRef {
  id: string;
  filename: string;
  mime_type: string;
  kind: "image" | "document";
}

export interface StoredMessage {
  id: number;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  metadata:
    | (ChatMetadata & { attachments?: AttachmentRef[] })
    | { attachments?: AttachmentRef[] }
    | null;
  created_at: string;
}

export interface UploadedAttachment {
  attachment_id: string;
  filename: string;
  mime_type: string;
  kind: "image" | "document";
  text_chars: number | null;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function parseError(res: Response): Promise<never> {
  let detail = `Request failed with status ${res.status}`;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
    else if (Array.isArray(body?.detail)) detail = "Invalid request payload";
  } catch {
    /* keep default */
  }
  throw new ApiError(res.status, detail);
}

export function attachmentRawUrl(id: string): string {
  return `${BASE_URL}/attachments/${encodeURIComponent(id)}/raw`;
}

export async function uploadAttachment(
  sessionId: string,
  file: File,
): Promise<UploadedAttachment> {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/attachments`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) await parseError(res);
  return (await res.json()) as UploadedAttachment;
}

export async function sendChat(
  sessionId: string,
  message: string,
  opts?: { systemPrompt?: string; attachmentIds?: string[] },
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      ...(opts?.systemPrompt ? { system_prompt: opts.systemPrompt } : {}),
      ...(opts?.attachmentIds?.length
        ? { attachment_ids: opts.attachmentIds }
        : {}),
    }),
  });
  if (!res.ok) await parseError(res);
  return (await res.json()) as ChatResponse;
}

export async function fetchMessages(sessionId: string): Promise<StoredMessage[]> {
  const res = await fetch(
    `${BASE_URL}/sessions/${encodeURIComponent(sessionId)}/messages`,
  );
  if (!res.ok) await parseError(res);
  return (await res.json()) as StoredMessage[];
}
