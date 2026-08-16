export function isTestEnvironmentReady(): boolean {
  return typeof window !== "undefined";
}
