import type { ProgressEvent } from "@lib/types";

interface Props {
  events: ProgressEvent[];
}

export function ProgressBar({ events }: Props) {
  const totalSoFar = events.at(-1)?.total_so_far ?? 0;
  const lastSource = events.at(-1)?.source ?? "";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-gray-400">
        <span className="animate-pulse">Scanning sources…</span>
        {totalSoFar > 0 && (
          <span className="text-brand font-semibold">{totalSoFar} found</span>
        )}
      </div>

      {/* Source pills */}
      <div className="flex flex-wrap gap-1">
        {events.map((ev) => (
          <span
            key={ev.source}
            className={`
              px-1.5 py-0.5 rounded text-xs font-mono
              ${ev.found > 0 ? "bg-green-900 text-green-300" : "bg-gray-800 text-gray-500"}
            `}
          >
            {ev.source}
            {ev.found > 0 && ` +${ev.found}`}
          </span>
        ))}
      </div>

      {lastSource && (
        <div className="text-xs text-gray-600 truncate">↳ {lastSource}</div>
      )}
    </div>
  );
}
