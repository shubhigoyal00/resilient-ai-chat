import { Menu, Plus } from "lucide-react";

interface Props {
  title: string;
  onOpenSidebar: () => void;
  onNewChat: () => void;
}

/** Slim top bar: hamburger on mobile, conversation title, quick New chat. */
export default function ChatHeader({ title, onOpenSidebar, onNewChat }: Props) {
  return (
    <header className="flex items-center justify-between border-b border-slate-800/70 bg-[#0a0e1a]/80 px-3 py-2.5 backdrop-blur sm:px-5">
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          onClick={onOpenSidebar}
          aria-label="Open sidebar"
          className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-slate-200 lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
        <h1 className="truncate text-sm font-medium text-slate-200">{title}</h1>
      </div>
      <button
        type="button"
        onClick={onNewChat}
        className="flex items-center gap-1.5 rounded-lg border border-slate-700/70 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-indigo-500/40 hover:bg-indigo-500/10 hover:text-white"
      >
        <Plus className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">New chat</span>
      </button>
    </header>
  );
}
