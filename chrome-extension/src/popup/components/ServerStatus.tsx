interface Props {
  online: boolean | null;
}

export function ServerStatus({ online }: Props) {
  if (online === null) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span className="animate-pulse">●</span>
        Checking server…
      </div>
    );
  }

  if (online) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-400">
        <span>●</span>
        <span>Server online</span>
        <span className="text-gray-600">localhost:8765</span>
      </div>
    );
  }

  return (
    <div className="bg-yellow-950 border border-yellow-800 rounded-lg px-3 py-2 text-yellow-300 text-xs space-y-1">
      <div className="flex items-center gap-1.5 font-semibold">
        <span>○</span> Server offline
      </div>
      <div>
        Start the API server:
        <code className="block mt-1 bg-gray-900 px-2 py-1 rounded font-mono">
          coldreach serve
        </code>
      </div>
    </div>
  );
}
