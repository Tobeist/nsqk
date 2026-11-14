import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import "./refinements.css";
const plex = localFont({
  src: "../public/fonts/ibm-plex-sans.ttf",
  display: "swap",
  variable: "--font-plex",
  weight: "100 700",
});
export const metadata: Metadata = {
  title: "Trend Detectives · Explorador de tendencias",
  description:
    "Explora temperatura y lluvia con series NASA procesadas para una caja del noreste de México, 1992–2024.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body className={plex.variable}>{children}</body>
    </html>
  );
}
