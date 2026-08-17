import type { ReactNode } from "react";

/** Alternating full-bleed section band; content stays centered inside. */
export function Section({
  tone = "white",
  slim = false,
  children,
}: {
  tone?: "white" | "light" | "navy";
  slim?: boolean;
  children: ReactNode;
}) {
  const toneClass =
    tone === "light" ? "bg-prem3-light-gray" : tone === "navy" ? "bg-prem3-navy" : "bg-white";
  return (
    <section className={toneClass}>
      <div className={`mx-auto max-w-6xl px-6 ${slim ? "py-8" : "py-16 sm:py-20"}`}>{children}</div>
    </section>
  );
}

export function Eyebrow({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <p
      className={`text-xs font-semibold uppercase tracking-wide ${dark ? "text-prem3-cyan" : "text-prem3-indigo"}`}
    >
      {children}
    </p>
  );
}
