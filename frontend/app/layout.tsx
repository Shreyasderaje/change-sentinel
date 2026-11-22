import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Change Sentinel 2.0 | Geospatial Intelligence",
  description:
    "Transform satellite imagery into actionable geospatial intelligence. Detect candidate changes, understand their context, and coordinate human verification.",
};

export const viewport: Viewport = {
  themeColor: "#061326",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>{children}</body>
    </html>
  );
}
