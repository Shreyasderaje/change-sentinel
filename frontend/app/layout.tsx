import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Change Sentinel | Geospatial Intelligence",
  description:
    "Satellite imagery change review workspace. Run verified analysis in the live Change Sentinel application.",
};

export const viewport: Viewport = {
  themeColor: "#061326",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
