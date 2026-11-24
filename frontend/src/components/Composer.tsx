import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";

interface Props {
  onSend: (message: string) => Promise<boolean>;
  disabled: boolean;
}

export default function Composer({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = async (e?: FormEvent) => {
    e?.preventDefault();
    const text = value.trim();
    if (!text || disabled) return;
    const sent = await onSend(text);
    if (sent) {
      setValue("");
      if (textareaRef.current) textareaRef.current.style.height = "auto";
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  };

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <form onSubmit={submit} className="border-t border-slate-800/70 bg-[#0a0e1a]/80 px-4 py-3.5 backdrop-blur sm:px-6">
      <div className="mx-auto flex max-w-3xl items-end gap-2.5">
        <div className="flex flex-1 items-end rounded-2xl border border-slate-700/70 bg-slate-900/80 transition focus-within:border-indigo-500/50 focus-within:ring-2 focus-within:ring-indigo-500/20">
          <textarea
            ref={textareaRef}
            data-testid="chat-input"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              autoResize();
            }}
            onKeyDown={onKeyDown}
            placeholder="Message Resilient AI…"
            disabled={disabled}
            maxLength={4000}
            rows={1}
            className="scroll-slim max-h-40 flex-1 resize-none bg-transparent px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none disabled:opacity-60"
          />
          <button
            data-testid="send-button"
            type="submit"
            disabled={disabled || !value.trim()}
            aria-label="Send message"
            className="m-1.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-md shadow-indigo-950/40 transition hover:from-indigo-400 hover:to-violet-500 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 disabled:cursor-not-allowed disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-500 disabled:shadow-none"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </div>
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-[10px] text-slate-600">
        Enter to send · Shift+Enter for a new line
      </p>
    </form>
  );
}
