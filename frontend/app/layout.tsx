/* eslint-disable @next/next/no-css-tags */
import type { Metadata } from "next";
import "./globals.css";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: {
    default: "Yixun Hong",
    template: "%s | Yixun Hong",
  },
  description: "Personal academic homepage built with Next.js and FastAPI.",
  icons: {
    icon: "/uploads/favicon.png",
  },
};

const themeBootScript = `
  (function () {
    try {
      var saved = localStorage.getItem("theme");
      var sysDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      var theme = saved === "dark" || (!saved && sysDark) ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", theme);
      document.documentElement.style.colorScheme = theme;
    } catch (error) {
      document.documentElement.setAttribute("data-theme", "light");
      document.documentElement.style.colorScheme = "light";
    }
  })();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
        <link rel="stylesheet" href="/static/css/styles.css?v=58" />
      </head>
      <body>
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
