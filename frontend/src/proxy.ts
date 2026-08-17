import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

/**
 * Next.js 16 renamed middleware.ts -> proxy.ts (same file convention, new
 * name/export). See docs/guides/upgrading/version-16.mdx. This is the
 * server-side identity boundary for Mission 2 (M2-06): everything under
 * /app EXCEPT the public fixture demo stays gated behind a signed-in
 * session. Public marketing, the free Planner, /start, and the sign-in/up
 * flows themselves are never gated -- gating them would break the
 * "public Planner works signed out" and "public demo remains public"
 * acceptance criteria.
 */
const isPublicRoute = createRouteMatcher([
  "/",
  "/how-it-works",
  "/pricing",
  "/planner(.*)",
  "/start(.*)",
  "/privacy",
  "/terms",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/app/demo(.*)",
]);

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files, unless present in search params.
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes, including the prem3-api BFF.
    "/(api|trpc)(.*)",
    // Always run for Clerk's own frontend API routes.
    "/__clerk/(.*)",
  ],
};
