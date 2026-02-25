import type { Metadata } from "next";
import "@/styles/globals.css";
import { ClientShell } from "./client-shell";

export const metadata: Metadata = {
  title: "Athena — C5ISR Command Platform",
  description: "AI-driven C5ISR cyber operations command platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <ClientShell>{children}</ClientShell>
      </body>
    </html>
  );
}
