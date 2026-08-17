import type { PreM3DataSource, RunResponseSet } from "./data-source";
import type { ExperienceBundle } from "@/types/mel";
import type { DomainView } from "@/types/domain-view";
import type { ArtifactRef } from "@/lib/format/proof";
import type { RunSummary } from "@/types/run";

/**
 * Documented gap, not a placeholder feature: Mission 1 has no private
 * Cloud Run backend to call (see frontend/README.md's "Service Boundary"
 * and "Private Cloud Run Integration" sections). This class exists so the
 * PreM3DataSource shape it will implement is pinned in code, and so
 * switching `preM3DataSource` in fixture-data-source.ts to this
 * implementation later is a one-line change. Every method fails loudly
 * rather than returning fabricated data.
 */
export class ApiPreM3DataSource implements PreM3DataSource {
  private unimplemented(method: string): never {
    throw new Error(
      `ApiPreM3DataSource.${method} is not implemented: no private PreM3 Cloud Run endpoint exists yet.`,
    );
  }

  async listRuns(): Promise<RunSummary[]> {
    this.unimplemented("listRuns");
  }

  async getRun(): Promise<RunSummary | null> {
    this.unimplemented("getRun");
  }

  async getRunResponses(): Promise<RunResponseSet> {
    this.unimplemented("getRunResponses");
  }

  async getArtifacts(): Promise<ArtifactRef[]> {
    this.unimplemented("getArtifacts");
  }

  async getExperience(): Promise<ExperienceBundle | null> {
    this.unimplemented("getExperience");
  }

  async getDomainView(): Promise<DomainView> {
    this.unimplemented("getDomainView");
  }
}
