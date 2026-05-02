import type { ProgressEvent, StartEvent } from "@lib/types";

interface Props {
  start: StartEvent | null;
  events: ProgressEvent[];
}

export function ProgressBar({ start, events }: Props) {
  const totalSources = start?.total_sources ?? 0;
  const sourceNames = start?.source_names ?? [];
  const completedSources = new Set(events.map((e) => e.source));
  const lastEvent = events.at(-1);
  const percent = lastEvent?.percent ?? 0;
  const totalEmailsSoFar = lastEvent?.total_so_far ?? 0;

  return (
    <div className="space-y-2">
      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-400">
          <span>
            {totalSources > 0 ? (
              <>
                {completedSources.size}/{totalSources} sources
              </>
            ) : (
              <span className="animate-pulse">Starting…</span>
            )}
          </span>
          <span className="font-semibold text-white">{percent}%</span>
        </div>

        <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-brand to-purple-500 rounded-full transition-all duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>

        {totalEmailsSoFar > 0 && (
          <div className="text-xs text-brand font-semibold">
            {totalEmailsSoFar} email{totalEmailsSoFar !== 1 ? "s" : ""} found so far…
          </div>
        )}
      </div>

      {/* Source grid */}
      {sourceNames.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {sourceNames.map((name) => {
            const ev = events.find((e) => e.source === name);
            const done = completedSources.has(name);
            const found = ev?.found ?? 0;
            const skipped = ev?.skipped ?? false;

            return (
              <span
                key={name}
                className={`
                  px-1.5 py-0.5 rounded text-xs font-mono transition-colors
                  ${
                    !done
                      ? "bg-gray-800 text-gray-600 animate-pulse"
                      : skipped
                        ? "bg-gray-800 text-gray-600"
                        : found > 0
                          ? "bg-green-900 text-green-300"
                          : "bg-gray-800 text-gray-400"
                  }
                `}
                title={ev?.errors?.join(", ") ?? ""}
              >
                {done ? (found > 0 ? `✓ ${name} +${found}` : `○ ${name}`) : `… ${name}`}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
