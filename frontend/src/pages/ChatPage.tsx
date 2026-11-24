import { useCallback, useState } from "react";
import ChatHeader from "../components/ChatHeader";
import Composer from "../components/Composer";
import MessageList from "../components/MessageList";
import type { DisplayMessage } from "../components/MessageBubble";
import { ApiError, sendChat } from "../services/api";

const newId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export default function ChatPage() {
  // A fresh session on every page load; all messages share it.
  const [sessionId, setSessionId] = useState<string>(() => `s-${newId()}`);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = useCallback(
    async (text: string): Promise<boolean> => {
      setLoading(true);
      setMessages((prev) => [
        ...prev,
        { id: `u-${newId()}`, role: "user", content: text },
      ]);
      try {
        const res = await sendChat(sessionId, text);
        setMessages((prev) => [
          ...prev,
          {
            id: `a-${newId()}`,
            role: "assistant",
            content: res.reply,
            metadata: res.metadata,
          },
        ]);
        return true;
      } catch (err) {
        const detail =
          err instanceof ApiError
            ? `${err.detail} (HTTP ${err.status})`
            : "Network error — is the backend running?";
        setMessages((prev) => [
          ...prev,
          { id: `e-${newId()}`, role: "error", content: detail },
        ]);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [sessionId],
  );

  const handleNewChat = useCallback(() => {
    setSessionId(`s-${newId()}`);
    setMessages([]);
    setLoading(false);
  }, []);

  return (
    <div className="flex h-full flex-col bg-slate-100">
      <ChatHeader onNewChat={handleNewChat} />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col overflow-hidden">
        <MessageList messages={messages} loading={loading} />
      </main>
      <Composer onSend={handleSend} disabled={loading} />
    </div>
  );
}
