import { SignIn } from "@clerk/nextjs";

/**
 * Optional catch-all route (Clerk's required pattern for a dedicated,
 * branded sign-in page in the App Router -- it needs to own every
 * sub-path under /sign-in for multi-step flows like SSO callbacks).
 * Redirect targets and Account-Portal opt-out come from
 * NEXT_PUBLIC_CLERK_SIGN_IN_URL / _FALLBACK_REDIRECT_URL in .env.local.
 */
export default function Page() {
  return (
    <SignIn
      appearance={{
        variables: {
          colorPrimary: "#3B4BDB",
          colorForeground: "#1A1F4B",
          borderRadius: "0.375rem",
        },
        elements: {
          card: "shadow-none border border-prem3-cool-gray",
        },
      }}
    />
  );
}
