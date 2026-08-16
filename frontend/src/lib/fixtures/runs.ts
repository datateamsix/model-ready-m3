import type { RunSummary } from "@/types/run";
import { musicCenterDatasetARun } from "./music-center-run";

export const RUN_LIST: RunSummary[] = [musicCenterDatasetARun];

export const RUNS_BY_ID: Record<string, RunSummary> = Object.fromEntries(
  RUN_LIST.map((run) => [run.run_id, run]),
);
