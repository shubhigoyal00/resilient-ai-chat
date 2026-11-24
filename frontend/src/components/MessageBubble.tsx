import { AlertTriangle, RotateCcw, Sparkles } from "lucide-react";
import type { ChatMetadata } from "../services/api";
import Markdown from "./Markdown";
import MetadataPanel from "./MetadataPanel";

export interface DisplayMessage {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
  metadata?: ChatMetadata;
  retryText?: string;
}

interface Props {
  message: DisplayMessage;
  onRetry?: (retryId: string) => void;
}

export default function MessageBubble({ message, onRetry }: Props) {
  if (message.role === "user") {
    return (
      <div className="message-in flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-br from-indigo-600 to-indigo-700 px-4 py-2.5 text-sm leading-relaxed text-white shadow-lg shadow-indigo-950/30 sm:max-w-[75%]">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="message-in flex justify-start" data-testid="chat-error">
        <div className="max-w-[85%] rounded-2xl rounded-bl-md border border-red-500/30 bg-red-500/10 px-4 py-3 sm:max-w-[75%]">
          <div className="flex items-center gap-2 text-sm font-medium text-red-300">
            <AlertTriangle className="h-4 w-4" />
            Something went wrong
          </div>
          <p className="mt-1 whitespace-pre-wrap break-words text-[13px] text-red-200/80">
            {message.content}
          </p>
          {onRetry && message.retryText && (
            <button
              type="button"
              onClick={() => onRetry(message.id)}
              className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg border border-red-500/40 px-2.5 py-1 text-xs font-medium text-red-300 transition hover:bg-red-500/10"
            >
              <RotateCcw className="h-3 w-3" />
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="message-in flex justify-start" data-testid="assistant-message">
      <div className="flex max-w-[92%] gap-3 sm:max-w-[80%]">
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-md shadow-indigo-950/40">
          <Sparkles className="h-3.5 w-3.5 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="rounded-2xl rounded-tl-md border border-slate-800 bg-slate-900/60 px-4 py-3">
            <Markdown text={message.content} />
          </div>
          {message.metadata && <MetadataPanel metadata={message.metadata} />}
        </div>
      </div>
    </div>
  );
}
