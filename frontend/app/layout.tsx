import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Leads Automation",
  description: "Self-hosted lead capture and outreach automation",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
