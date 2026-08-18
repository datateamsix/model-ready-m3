import { UserProfile } from "@clerk/nextjs";

/**
 * M2-15: identity/account settings using Clerk's own UserProfile surface
 * (profile fields, connected accounts, security/sessions, org management)
 * rather than a custom-built identity suite, per the prompt's explicit
 * "do not build a custom identity-management suite" instruction. Hash-based
 * internal routing (no `path` prop) since this page isn't a catch-all route.
 */
export default function Page() {
  return (
    <div className="flex flex-col gap-6">
      <h2 className="font-[family-name:var(--font-display)] text-xl font-semibold text-prem3-navy">Account</h2>
      <UserProfile
        routing="hash"
        appearance={{
          variables: {
            colorPrimary: "#3B4BDB",
            colorForeground: "#1A1F4B",
            borderRadius: "0.375rem",
          },
          elements: {
            rootBox: "w-full",
            card: "shadow-none border border-prem3-cool-gray",
          },
        }}
      />
    </div>
  );
}
