interface Props {
  onNewChat: () => void;
}

export default function ChatHeader({ onNewChat }: Props) {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 text-sm font-bold text-white">
          AI
        </div>
        <div>
          <h1 className="text-sm font-semibold text-slate-900">Resilient AI Chat</h1>
          <p className="text-xs text-slate-400">
            Multi-key Gemini backend with caching and failover
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onNewChat}
        className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-400 hover:bg-slate-50"
      >
        New chat
      </button>
    </header>
  );
}
