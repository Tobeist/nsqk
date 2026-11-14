import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Trend Detectives · Explorador de tendencias",
  description:
    "Explora tendencias ambientales históricas de regiones de México y Estados Unidos. Prototipo con datos de demostración.",
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
