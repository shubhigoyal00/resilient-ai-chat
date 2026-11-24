import { useState, type FormEvent, type KeyboardEvent } from "react";

interface Props {
  onSend: (message: string) => Promise<boolean>;
  disabled: boolean;
}

export default function Composer({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");

  const submit = async (e?: FormEvent) => {
    e?.preventDefault();
    const text = value.trim();
    if (!text || disabled) return;
    const sent = await onSend(text);
    if (sent) setValue(""); // clear only after a successful send
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      void submit();
    }
  };

  return (
    <form
      onSubmit={submit}
      className="border-t border-slate-200 bg-white px-4 py-3 sm:px-6"
    >
      <div className="mx-auto flex max-w-3xl items-center gap-2">
        <input
          data-testid="chat-input"
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type your message…"
          disabled={disabled}
          maxLength={4000}
          className="flex-1 rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition focus:border-slate-500 focus:bg-white focus:ring-2 focus:ring-slate-200 disabled:opacity-60"
        />
        <button
          data-testid="send-button"
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </form>
  );
}
