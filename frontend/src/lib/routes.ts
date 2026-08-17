/**
 * Typed route builders for every internal href in the app. Mission 2's
 * information architecture (docs/superpowers/specs/2026-08-17-prem3-mission-2-commercial-model.md;
 * full route table in frontend/docs/mission-2/PREM3_MISSION_2_FRONTEND_EXECUTION_PROMPT_PACK.md's
 * M2-01). `workspaceId` is the internal identifier that stays in the URL — customer-facing copy
 * calls it "MMM Project," but the route/contract field name is unchanged.
 *
 * Internal `<Link>`/`redirect()` targets must use these, not raw template-literal strings, so
 * the route shape only needs to change in one place.
 */
export const routes = {
  // Public marketing
  home: () => "/",
  howItWorks: () => "/how-it-works",
  pricing: () => "/pricing",
  planner: () => "/planner",
  start: () => "/start",
  signIn: () => "/sign-in",
  signUp: () => "/sign-up",
  privacy: () => "/privacy",
  terms: () => "/terms",

  // Public demo (signed-out reachable, fixture-backed)
  publicDemoRun: (runId: string) => `/app/demo/runs/${runId}`,

  // Authenticated product
  app: () => "/app",
  workspace: (workspaceId: string) => `/app/w/${workspaceId}`,
  workspacePlans: (workspaceId: string) => `/app/w/${workspaceId}/plans`,
  workspacePlan: (workspaceId: string, planningRunId: string) =>
    `/app/w/${workspaceId}/plans/${planningRunId}`,
  workspaceDatasets: (workspaceId: string) => `/app/w/${workspaceId}/datasets`,
  workspaceDataset: (workspaceId: string, datasetId: string) =>
    `/app/w/${workspaceId}/datasets/${datasetId}`,
  workspaceDatasetRun: (workspaceId: string, datasetId: string, runId: string) =>
    `/app/w/${workspaceId}/datasets/${datasetId}/runs/${runId}`,
  workspaceTaskmaster: (workspaceId: string) => `/app/w/${workspaceId}/taskmaster`,
  settingsAccount: () => "/app/settings/account",
  settingsBilling: () => "/app/settings/billing",
} as const;
