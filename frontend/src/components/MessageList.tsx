import { useEffect, useRef } from "react";
import MessageBubble, { type DisplayMessage } from "./MessageBubble";
import WelcomeScreen from "./WelcomeScreen";

interface Props {
  messages: DisplayMessage[];
  loading: boolean;
  historyLoading: boolean;
  onPrompt: (text: string) => void;
  onRetry: (retryId: string) => void;
}

export default function MessageList({
  messages,
  loading,
  historyLoading,
  onPrompt,
  onRetry,
}: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (messages.length === 0 && !loading && !historyLoading) {
    return (
      <div className="scroll-slim flex-1 overflow-y-auto">
        <WelcomeScreen onPrompt={onPrompt} />
      </div>
    );
  }

  return (
    <div className="scroll-slim flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-8">
      {historyLoading && (
        <div className="flex justify-center py-6">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-600 border-t-indigo-400" />
            Loading conversation…
          </div>
        </div>
      )}

      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} onRetry={onRetry} />
      ))}

      {loading && (
        <div className="message-in flex justify-start">
          <div className="flex items-center gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-md shadow-indigo-950/40">
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            </div>
            <div className="rounded-2xl rounded-tl-md border border-slate-800 bg-slate-900/60 px-4 py-3">
              <div className="flex items-center gap-1.5" aria-label="Assistant is typing">
                <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
                <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
                <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
              </div>
            </div>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
