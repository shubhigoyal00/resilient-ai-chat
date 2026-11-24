import { ArrowRight, Sparkles } from "lucide-react";

const SUGGESTIONS = [
  {
    title: "Explain failover",
    prompt: "Explain how multi-key API failover works in one paragraph.",
  },
  {
    title: "Write some code",
    prompt: "Write a Python function that retries an HTTP request with exponential backoff.",
  },
  {
    title: "Design a schema",
    prompt: "Design a SQLite schema for a chat app with sessions and messages.",
  },
  {
    title: "Test the cache",
    prompt: "Reply with exactly: cache layer verified.",
  },
];

interface Props {
  onPrompt: (text: string) => void;
}

export default function WelcomeScreen({ onPrompt }: Props) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-10">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-xl shadow-indigo-950/50">
        <Sparkles className="h-6 w-6 text-white" />
      </div>
      <h1 className="bg-gradient-to-r from-slate-100 via-indigo-200 to-slate-100 bg-clip-text text-center text-2xl font-semibold tracking-tight text-transparent sm:text-3xl">
        Resilient AI
      </h1>
      <p className="mt-2 max-w-md text-center text-sm leading-relaxed text-slate-400">
        A Gemini-backed assistant with multi-key failover, LiteLLM response
        caching and per-request inference metadata.
      </p>

      <div className="mt-8 grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.title}
            type="button"
            onClick={() => onPrompt(s.prompt)}
            className="group flex items-start justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-3.5 text-left transition hover:border-indigo-500/40 hover:bg-slate-800/60"
          >
            <span>
              <span className="block text-sm font-medium text-slate-200">
                {s.title}
              </span>
              <span className="mt-0.5 line-clamp-2 block text-xs leading-relaxed text-slate-500">
                {s.prompt}
              </span>
            </span>
            <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-slate-600 transition group-hover:translate-x-0.5 group-hover:text-indigo-400" />
          </button>
        ))}
      </div>
    </div>
  );
}
