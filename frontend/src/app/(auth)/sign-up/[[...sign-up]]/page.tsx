import { SignUp } from "@clerk/nextjs";

/**
 * Optional catch-all route -- see the sign-in page for why. Redirect
 * targets come from NEXT_PUBLIC_CLERK_SIGN_UP_URL / _FALLBACK_REDIRECT_URL
 * in .env.local.
 */
export default function Page() {
  return (
    <SignUp
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
