import { MessageSquare, Plus, Sparkles, X } from "lucide-react";

export interface ConversationSummary {
  id: string;
  title: string;
}

interface Props {
  conversations: ConversationSummary[];
  activeId: string;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onClose: () => void;
}

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onClose,
}: Props) {
  return (
    <aside className="flex h-full w-72 flex-col border-r border-slate-800/70 bg-[#0a0e1a]">
      {/* Branding */}
      <div className="flex items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-950/40">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight text-slate-100">
              Resilient AI
            </p>
            <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
              Gemini · Multi-key
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close sidebar"
          className="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-800 hover:text-slate-300 lg:hidden"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* New chat */}
      <div className="px-3 pb-2">
        <button
          type="button"
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-xl border border-slate-700/70 bg-slate-800/50 px-3.5 py-2.5 text-sm font-medium text-slate-200 transition hover:border-indigo-500/50 hover:bg-indigo-500/10 hover:text-white"
        >
          <Plus className="h-4 w-4 text-indigo-400" />
          New chat
        </button>
      </div>

      {/* Conversation list */}
      <div className="scroll-slim mt-2 flex-1 overflow-y-auto px-3 pb-4">
        {conversations.length > 0 && (
          <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
            This session
          </p>
        )}
        <nav className="space-y-1">
          {conversations.map((c) => {
            const active = c.id === activeId;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => onSelect(c.id)}
                className={`group flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-[13px] transition ${
                  active
                    ? "bg-indigo-500/15 text-indigo-200 ring-1 ring-inset ring-indigo-500/30"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                }`}
              >
                <MessageSquare
                  className={`h-3.5 w-3.5 shrink-0 ${active ? "text-indigo-400" : "text-slate-600 group-hover:text-slate-500"}`}
                />
                <span className="truncate">{c.title}</span>
              </button>
            );
          })}
        </nav>
        {conversations.length === 0 && (
          <p className="px-2 pt-1 text-xs text-slate-600">
            Conversations you start appear here.
          </p>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-slate-800/70 px-4 py-3">
        <p className="text-[11px] leading-relaxed text-slate-600">
          Multi-key failover · LiteLLM cache · SQLite persistence
        </p>
      </div>
    </aside>
  );
}
