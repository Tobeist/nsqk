import type { Metadata } from "next";
import "./globals.css";
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
      <body>{children}</body>
    </html>
  );
}
