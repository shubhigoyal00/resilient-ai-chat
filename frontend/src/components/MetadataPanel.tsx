import type { ChatMetadata } from "../services/api";

function SourceBadge({ source }: { source: ChatMetadata["resolution_source"] }) {
  const isLive = source === "LIVE_INFERENCE";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
        isLive
          ? "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200"
          : "bg-violet-100 text-violet-700 ring-1 ring-violet-200"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${isLive ? "bg-emerald-500" : "bg-violet-500"}`}
      />
      {isLive ? "LIVE INFERENCE" : "LLM CACHE"}
    </span>
  );
}

export default function MetadataPanel({ metadata }: { metadata: ChatMetadata }) {
  return (
    <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="mb-1.5" data-testid="meta-source">
        <SourceBadge source={metadata.resolution_source} />
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] sm:grid-cols-4">
        <div>
          <dt className="font-medium uppercase tracking-wide text-slate-400">Model</dt>
          <dd className="truncate font-mono text-slate-700" data-testid="meta-model">
            {metadata.model}
          </dd>
        </div>
        <div>
          <dt className="font-medium uppercase tracking-wide text-slate-400">Latency</dt>
          <dd className="font-mono text-slate-700" data-testid="meta-latency">
            {metadata.latency_ms} ms
          </dd>
        </div>
        <div>
          <dt className="font-medium uppercase tracking-wide text-slate-400">Input tokens</dt>
          <dd className="font-mono text-slate-700" data-testid="meta-input-tokens">
            {metadata.input_tokens}
          </dd>
        </div>
        <div>
          <dt className="font-medium uppercase tracking-wide text-slate-400">Output tokens</dt>
          <dd className="font-mono text-slate-700" data-testid="meta-output-tokens">
            {metadata.output_tokens}
          </dd>
        </div>
      </dl>
    </div>
  );
}
