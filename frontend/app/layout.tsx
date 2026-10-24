import type { Metadata } from "next";
import { Be_Vietnam_Pro } from "next/font/google";

import { Header } from "@/components/Header";

import "./globals.css";

const beVietnam = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700", "800", "900"],
  variable: "--font-be-vietnam",
});

export const metadata: Metadata = {
  title: "Fraud Detection – Phát hiện giao dịch bất thường",
  description: "Giám sát giao dịch thẻ, phát hiện gian lận và giải thích lý do bằng mô hình học máy.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi" className={beVietnam.variable}>
      <body className="min-h-dvh antialiased">
        <Header />
        <main className="px-5 py-4">{children}</main>
      </body>
    </html>
  );
}
