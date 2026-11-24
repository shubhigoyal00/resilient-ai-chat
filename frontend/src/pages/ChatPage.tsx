import { useCallback, useMemo, useState } from "react";
import ChatHeader from "../components/ChatHeader";
import Composer from "../components/Composer";
import MessageList from "../components/MessageList";
import Sidebar, { type ConversationSummary } from "../components/Sidebar";
import type { DisplayMessage } from "../components/MessageBubble";
import {
  ApiError,
  fetchMessages,
  sendChat,
  type StoredMessage,
} from "../services/api";

const newId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const newSession = () => `s-${newId()}`;

const titleFor = (text: string) =>
  text.length > 42 ? `${text.slice(0, 42).trimEnd()}…` : text;

const toDisplay = (m: StoredMessage): DisplayMessage => ({
  id: `db-${m.id}`,
  role: m.role,
  content: m.content,
  metadata: m.metadata ?? undefined,
});

export default function ChatPage() {
  // Fresh session on every page load; conversations started this session
  // can be reopened from the sidebar (history comes from the backend).
  const [sessionId, setSessionId] = useState<string>(newSession);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messagesBySession, setMessagesBySession] = useState<
    Record<string, DisplayMessage[]>
  >({});
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const messages = useMemo(
    () => messagesBySession[sessionId] ?? [],
    [messagesBySession, sessionId],
  );

  const updateSessionMessages = useCallback(
    (sid: string, fn: (prev: DisplayMessage[]) => DisplayMessage[]) => {
      setMessagesBySession((prev) => ({ ...prev, [sid]: fn(prev[sid] ?? []) }));
    },
    [],
  );

  const ensureConversation = useCallback((sid: string, firstMessage: string) => {
    setConversations((prev) => {
      if (prev.some((c) => c.id === sid)) {
        return prev.map((c) =>
          c.id === sid && c.title === "New chat"
            ? { ...c, title: titleFor(firstMessage) }
            : c,
        );
      }
      return [...prev, { id: sid, title: titleFor(firstMessage) }];
    });
  }, []);

  /** Core send path; addUserBubble=false is used by Retry (user bubble exists). */
  const send = useCallback(
    async (sid: string, text: string, addUserBubble: boolean): Promise<boolean> => {
      setLoading(true);
      if (addUserBubble) {
        updateSessionMessages(sid, (prev) => [
          ...prev,
          { id: `u-${newId()}`, role: "user", content: text },
        ]);
      }
      try {
        const res = await sendChat(sid, text);
        updateSessionMessages(sid, (prev) => [
          ...prev,
          {
            id: `a-${newId()}`,
            role: "assistant",
            content: res.reply,
            metadata: res.metadata,
          },
        ]);
        ensureConversation(sid, text);
        return true;
      } catch (err) {
        const detail =
          err instanceof ApiError
            ? `${err.detail} (HTTP ${err.status})`
            : "Network error — is the backend running?";
        updateSessionMessages(sid, (prev) => [
          ...prev,
          { id: `e-${newId()}`, role: "error", content: detail, retryText: text },
        ]);
        ensureConversation(sid, text);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [ensureConversation, updateSessionMessages],
  );

  const handleSend = useCallback(
    (text: string) => send(sessionId, text, true),
    [send, sessionId],
  );

  const handleRetry = useCallback(
    (errorMsgId: string) => {
      const errMsg = messages.find((m) => m.id === errorMsgId);
      if (!errMsg?.retryText) return;
      updateSessionMessages(sessionId, (prev) =>
        prev.filter((m) => m.id !== errorMsgId),
      );
      void send(sessionId, errMsg.retryText, false);
    },
    [messages, send, sessionId, updateSessionMessages],
  );

  const handleNewChat = useCallback(() => {
    setSessionId(newSession());
    setLoading(false);
    setSidebarOpen(false);
  }, []);

  const handleSelect = useCallback(
    async (sid: string) => {
      if (sid === sessionId) {
        setSidebarOpen(false);
        return;
      }
      setSessionId(sid);
      setSidebarOpen(false);
      // Already have this conversation's messages locally?
      if ((messagesBySession[sid] ?? []).length > 0) return;
      setHistoryLoading(true);
      try {
        const stored = await fetchMessages(sid);
        updateSessionMessages(sid, () => stored.map(toDisplay));
      } catch {
        updateSessionMessages(sid, () => []);
      } finally {
        setHistoryLoading(false);
      }
    },
    [sessionId, messagesBySession, updateSessionMessages],
  );

  const activeTitle =
    conversations.find((c) => c.id === sessionId)?.title ?? "New chat";

  return (
    <div className="glow-bg flex h-full bg-[#070a12]">
      {/* Sidebar: static on desktop, overlay on mobile */}
      <div className="hidden lg:block">
        <Sidebar
          conversations={conversations}
          activeId={sessionId}
          onSelect={handleSelect}
          onNewChat={handleNewChat}
          onClose={() => setSidebarOpen(false)}
        />
      </div>
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 z-50 shadow-2xl">
            <Sidebar
              conversations={conversations}
              activeId={sessionId}
              onSelect={handleSelect}
              onNewChat={handleNewChat}
              onClose={() => setSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          title={activeTitle}
          onOpenSidebar={() => setSidebarOpen(true)}
          onNewChat={handleNewChat}
        />
        <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col overflow-hidden">
          <MessageList
            messages={messages}
            loading={loading}
            historyLoading={historyLoading}
            onPrompt={(t) => void handleSend(t)}
            onRetry={handleRetry}
          />
        </main>
        <Composer onSend={handleSend} disabled={loading} />
      </div>
    </div>
  );
}
