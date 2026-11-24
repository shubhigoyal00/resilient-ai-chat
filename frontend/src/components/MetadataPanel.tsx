import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Cpu,
  Database,
  KeyRound,
  RefreshCw,
  Timer,
  Zap,
} from "lucide-react";
import type { ChatMetadata } from "../services/api";

function SourceBadge({ source }: { source: ChatMetadata["resolution_source"] }) {
  const isLive = source === "LIVE_INFERENCE";
  const Icon = isLive ? Zap : Database;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ring-1 ring-inset ${
        isLive
          ? "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30"
          : "bg-violet-500/10 text-violet-300 ring-violet-500/30"
      }`}
    >
      <Icon className="h-3 w-3" />
      {isLive ? "Live Inference" : "LLM Cache"}
    </span>
  );
}

function Stat({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof Cpu;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="h-3.5 w-3.5 shrink-0 text-slate-500" />
      <span className="text-slate-500">{label}</span>
      <span className="font-mono text-slate-300">{children}</span>
    </div>
  );
}

export default function MetadataPanel({ metadata }: { metadata: ChatMetadata }) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border border-slate-800/80 bg-slate-900/70 px-3.5 py-2.5 text-[11px]">
      <span data-testid="meta-source">
        <SourceBadge source={metadata.resolution_source} />
      </span>
      <Stat icon={Cpu} label="Model">
        <span data-testid="meta-model">{metadata.model}</span>
      </Stat>
      <Stat icon={Timer} label="Latency">
        <span data-testid="meta-latency">{metadata.latency_ms} ms</span>
      </Stat>
      <Stat icon={ArrowDownToLine} label="In">
        <span data-testid="meta-input-tokens">{metadata.input_tokens}</span>
      </Stat>
      <Stat icon={ArrowUpFromLine} label="Out">
        <span data-testid="meta-output-tokens">{metadata.output_tokens}</span>
      </Stat>
      {metadata.key_id !== null && (
        <Stat icon={KeyRound} label="Key">
          {metadata.key_id}
        </Stat>
      )}
      <Stat icon={RefreshCw} label="Fallbacks">
        {metadata.fallback_attempts}
      </Stat>
    </div>
  );
}
