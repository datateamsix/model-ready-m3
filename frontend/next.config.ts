import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Mission 1's /runs/[runId] moved to the Mission 2 IA's public demo path
  // at /app/demo/runs/[runId] (frontend/docs/mission-2/
  // PREM3_MISSION_2_FRONTEND_EXECUTION_PROMPT_PACK.md, M2-01). Not marked
  // permanent: this redirect is transitional until authenticated
  // Dataset/run routing (/app/w/[workspaceId]/datasets/[datasetId]/
  // runs/[runId]) exists, at which point /runs/[runId] as a concept goes
  // away entirely rather than staying a permanent alias.
  async redirects() {
    return [
      {
        source: "/runs/:runId",
        destination: "/app/demo/runs/:runId",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
