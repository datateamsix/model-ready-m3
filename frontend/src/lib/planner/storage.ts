import { PLANNER_MANIFEST_VERSION } from "./manifest";
import type { PlannerIntake, PlannerResult } from "./types";

/**
 * M2-08: local-only, versioned, expiration-aware storage for the anonymous
 * Planner draft/result -- never sent anywhere, never a secret credential or
 * raw uploaded file. Storing the manifest version alongside the data means
 * a stale draft from a previous manifest is discarded rather than
 * silently reused against content it was never generated for.
 */
const STORAGE_KEY = "prem3.planner.draft.v1";
const EXPIRATION_MS = 14 * 24 * 60 * 60 * 1000; // 14 days

interface StoredPlannerState {
  manifestVersion: string;
  storedAt: string;
  intake: PlannerIntake;
  result: PlannerResult | null;
}

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function savePlannerState(intake: PlannerIntake, result: PlannerResult | null): void {
  if (!isBrowser()) return;
  const payload: StoredPlannerState = {
    manifestVersion: PLANNER_MANIFEST_VERSION,
    storedAt: new Date().toISOString(),
    intake,
    result,
  };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Storage can fail (quota, private mode); the Planner still works in
    // memory for the current session, it just won't survive a reload.
  }
}

export function loadPlannerState(now: Date = new Date()): { intake: PlannerIntake; result: PlannerResult | null } | null {
  if (!isBrowser()) return null;

  let raw: string | null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
  if (!raw) return null;

  let parsed: StoredPlannerState;
  try {
    parsed = JSON.parse(raw);
  } catch {
    clearPlannerState();
    return null;
  }

  if (parsed.manifestVersion !== PLANNER_MANIFEST_VERSION) {
    clearPlannerState();
    return null;
  }

  const storedAt = new Date(parsed.storedAt).getTime();
  if (Number.isNaN(storedAt) || now.getTime() - storedAt > EXPIRATION_MS) {
    clearPlannerState();
    return null;
  }

  return { intake: parsed.intake, result: parsed.result };
}

export function clearPlannerState(): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to do if storage is unavailable.
  }
}
