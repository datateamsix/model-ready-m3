import type { Metadata } from "next";
import { Inter } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

// PreM3's preferred display typeface (brand/brand-assets/tokens/prem3.tokens.json:
// typography.display). Self-hosted from the approved package under
// brand/brand-assets/fonts/Satoshi_Complete (ITF Free Font License -- self-hosting
// permitted, see .../License/FFL.txt). Only the two variable-font woff2 files are
// loaded here: Satoshi's variable font covers the full weight 300-900 range in one
// file per style, and every browser with variable-font support already supports
// woff2, so the static per-weight files and legacy woff/eot/ttf formats the
// package also ships aren't needed for web use.
const satoshi = localFont({
  src: [
    { path: "../fonts/satoshi/Satoshi-Variable.woff2", weight: "300 900", style: "normal" },
    { path: "../fonts/satoshi/Satoshi-VariableItalic.woff2", weight: "300 900", style: "italic" },
  ],
  variable: "--font-satoshi",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PreM3 — Map. Mend. Model.",
  description: "A self-learning, autonomous pre-modeling agent for Google Meridian.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${satoshi.variable}`}>
      <body className="font-[family-name:var(--font-ui)] antialiased">{children}</body>
    </html>
  );
}
