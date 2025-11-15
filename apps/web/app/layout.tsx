import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "EcoFood",
  description: "AI-assisted futuristic meal planner"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100 antialiased">
        <div className="relative flex min-h-screen flex-col items-center justify-center px-4 py-10">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(34,211,238,0.12),_transparent_55%),_radial-gradient(circle_at_bottom,_rgba(56,189,248,0.18),_transparent_55%)]" />
          <main className="relative z-10 w-full max-w-5xl">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
