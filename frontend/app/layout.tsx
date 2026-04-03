/* eslint-disable @next/next/no-css-tags */
import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { ContentEnhancer } from "@/components/content-enhancer";
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
        <link rel="stylesheet" href="/static/css/styles.css?v=55" />
        <link
          rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css"
          id="hljs-light"
        />
        <link
          rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css"
          id="hljs-dark"
        />
      </head>
      <body>
        <SiteHeader />
        {children}
        <SiteFooter />
        <Script
          src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
          strategy="afterInteractive"
        />
        <ContentEnhancer />
      </body>
    </html>
  );
}
