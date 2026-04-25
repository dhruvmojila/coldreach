import { useState } from "react";
import type { JobContext } from "@lib/types";
import { resolveCompany } from "@lib/api";

interface Props {
  context: JobContext;
  onUseDomain: (domain: string) => void;
}

const SOURCE_LABELS: Record<JobContext["source"], string> = {
  greenhouse: "Greenhouse",
  lever: "Lever",
  indeed: "Indeed",
  linkedin: "LinkedIn",
  workable: "Workable",
  manual: "Manual",
};

export function JobDetected({ context, onUseDomain }: Props) {
  const [resolving, setResolving] = useState(false);

  const handleUse = async () => {
    if (context.domain) {
      onUseDomain(context.domain);
      return;
    }
    // Resolve company → domain via the API
    setResolving(true);
    const domain = await resolveCompany(context.company);
    setResolving(false);
    if (domain) {
      onUseDomain(domain);
    } else {
      // Fallback: let user type it
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <span className="text-green-400">●</span>
          Job detected · {SOURCE_LABELS[context.source]}
        </div>
      </div>

      <div className="font-semibold text-white truncate" title={context.company}>
        {context.company}
      </div>

      {context.jobTitle && (
        <div className="text-xs text-gray-400 truncate" title={context.jobTitle}>
          {context.jobTitle}
        </div>
      )}

      <button
        onClick={handleUse}
        disabled={resolving}
        className="mt-1 text-xs text-brand hover:text-blue-300 transition-colors disabled:opacity-50"
      >
        {resolving ? "Resolving domain…" : `Use "${context.company}" →`}
      </button>
    </div>
  );
}
