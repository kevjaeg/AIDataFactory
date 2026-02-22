import type { Metadata } from "next";
import { JetBrains_Mono, Inter } from "next/font/google";
import { Sidebar } from "@/components/layout/Sidebar";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Data Factory",
  description: "Production-grade LLM training data pipeline",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased bg-[#0a0a0f] text-[#e0e0e0] min-h-screen`}
      >
        <Sidebar />
        <main className="ml-56 min-h-screen p-6 transition-all duration-300">
          {children}
        </main>
      </body>
    </html>
  );
}
