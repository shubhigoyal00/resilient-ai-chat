import type { ChatMetadata } from "../services/api";
import MetadataPanel from "./MetadataPanel";

export interface DisplayMessage {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
  metadata?: ChatMetadata;
}

export default function MessageBubble({ message }: { message: DisplayMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-slate-900 px-4 py-2.5 text-sm text-white shadow-sm sm:max-w-[70%]">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="flex justify-start" data-testid="chat-error">
        <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700 sm:max-w-[70%]">
          <p className="font-medium">Something went wrong</p>
          <p className="mt-0.5 whitespace-pre-wrap break-words text-red-600">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start" data-testid="assistant-message">
      <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 shadow-sm sm:max-w-[70%]">
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
        {message.metadata && <MetadataPanel metadata={message.metadata} />}
      </div>
    </div>
  );
}
