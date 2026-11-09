import type { Metadata } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import Script from "next/script";

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

// Đặt giao diện sáng/tối trước khi trang hydrate (tránh nháy màu): lựa chọn đã lưu, nếu chưa có thì theo hệ thống.
const THEME_SCRIPT = `try{var t=localStorage.getItem("theme");if(t!=="light"&&t!=="dark"){t=matchMedia("(prefers-color-scheme: light)").matches?"light":"dark"}document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // data-theme do script dưới đây đặt ở trình duyệt -> khác HTML máy chủ, bỏ qua cảnh báo hydration.
    <html lang="vi" className={beVietnam.variable} suppressHydrationWarning>
      <body className="min-h-dvh antialiased">
        <Header />
        <main className="px-5 py-4">{children}</main>
        <Script id="theme-init" strategy="beforeInteractive">
          {THEME_SCRIPT}
        </Script>
      </body>
    </html>
  );
}
