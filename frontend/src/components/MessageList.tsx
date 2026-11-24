import { useEffect, useRef } from "react";
import MessageBubble, { type DisplayMessage } from "./MessageBubble";

interface Props {
  messages: DisplayMessage[];
  loading: boolean;
}

export default function MessageList({ messages, loading }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6 sm:px-6">
      {messages.length === 0 && !loading && (
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <p className="text-sm font-medium text-slate-500">No messages yet</p>
            <p className="mt-1 text-xs text-slate-400">
              Send a message to start the conversation.
            </p>
          </div>
        </div>
      )}

      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}

      {loading && (
        <div className="flex justify-start">
          <div className="rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <div className="flex items-center gap-1.5" aria-label="Assistant is typing">
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:0ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:300ms]" />
            </div>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
