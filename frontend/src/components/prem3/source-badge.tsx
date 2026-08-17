import { ExternalLink } from "lucide-react";

export function SourceBadge({ sourceRef }: { sourceRef: string }) {
  const isUrl = sourceRef.startsWith("http://") || sourceRef.startsWith("https://");

  if (isUrl) {
    return (
      <a
        href={sourceRef}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1 rounded border border-prem3-cool-gray px-2 py-0.5 text-xs text-prem3-indigo hover:underline"
      >
        {sourceRef}
        <ExternalLink className="size-3" aria-hidden="true" />
      </a>
    );
  }

  return (
    <span className="inline-flex items-center rounded border border-prem3-cool-gray px-2 py-0.5 text-xs text-prem3-navy/70">
      {sourceRef}
    </span>
  );
}
