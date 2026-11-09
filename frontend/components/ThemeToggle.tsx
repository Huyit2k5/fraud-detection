"use client";

import { useSyncExternalStore } from "react";

type Theme = "dark" | "light";
export const THEME_STORAGE_KEY = "theme";

// Giao diện hiện tại nằm ở <html data-theme>, được đặt trước khi vẽ trang (script trong layout.tsx).
// Đọc trực tiếp từ DOM và theo dõi thay đổi để mọi nơi dùng chung một nguồn.
function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

const getTheme = (): Theme => (document.documentElement.dataset.theme === "light" ? "light" : "dark");

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getTheme, () => "dark" as Theme);
  const next: Theme = theme === "dark" ? "light" : "dark";

  const toggle = () => {
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // trình duyệt chặn lưu trữ: vẫn đổi được giao diện trong phiên hiện tại
    }
  };

  return (
    <button
      onClick={toggle}
      aria-label={next === "light" ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}
      title={next === "light" ? "Giao diện sáng" : "Giao diện tối"}
      className="rounded-lg border border-line bg-panel-2 px-2.5 py-1 text-sm hover:border-action"
    >
      {theme === "dark" ? "☀️ Sáng" : "🌙 Tối"}
    </button>
  );
}
