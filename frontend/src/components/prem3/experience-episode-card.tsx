import type { ExperienceEpisode } from "@/types/mel";

export function ExperienceEpisodeCard({ episode }: { episode: ExperienceEpisode }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-prem3-navy">Experience episode</p>
        <span className="rounded border border-prem3-cool-gray px-2 py-0.5 text-xs font-medium text-prem3-navy/70">
          {episode.terminal_outcome}
        </span>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs text-prem3-navy/70">
        <div>
          <dt className="uppercase tracking-wide">Episode</dt>
          <dd className="mt-0.5 text-prem3-navy">{episode.episode_id}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">DOMAIN_VIEW used</dt>
          <dd className="mt-0.5 text-prem3-navy">{episode.domain_view_version}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Learning eligible</dt>
          <dd className="mt-0.5 text-prem3-navy">{episode.learning_eligible ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Holdout</dt>
          <dd className="mt-0.5 text-prem3-navy">{episode.holdout ? "Yes — sealed" : "No"}</dd>
        </div>
      </dl>
    </div>
  );
}
