import type { Metadata } from "next";
import "./globals.css";
import { HomeLegacyEffects } from "@/components/home-legacy-effects";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  metadataBase: new URL("https://foreverhyx.top"),
  title: {
    default: "Yixun Hong | Personal Academic Homepage",
    template: "%s | Yixun Hong",
  },
  description: "Yixun Hong (洪奕迅) is an undergraduate student at Zhejiang University majoring in Information Security. Research interests include Computer Architecture, GPU simulation, and High-Performance Computing.",
  keywords: ["Yixun Hong", "洪奕迅", "Zhejiang University", "Information Security", "Computer Architecture", "GPU simulation", "HPC", "personal homepage", "academic homepage"],
  authors: [{ name: "Yixun Hong", url: "https://foreverhyx.top" }],
  creator: "Yixun Hong",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
    },
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://foreverhyx.top",
    siteName: "Yixun Hong's Homepage",
    title: "Yixun Hong | Personal Academic Homepage",
    description: "Yixun Hong (洪奕迅) is an undergraduate student at Zhejiang University majoring in Information Security.",
    images: [
      {
        url: "/uploads/avatar.png",
        width: 256,
        height: 256,
        alt: "Yixun Hong's Avatar",
      },
    ],
  },
  twitter: {
    card: "summary",
    title: "Yixun Hong | Personal Academic Homepage",
    description: "Yixun Hong (洪奕迅) is an undergraduate student at Zhejiang University majoring in Information Security.",
    images: ["/uploads/avatar.png"],
    creator: "@ForeverHYX",
  },
  alternates: {
    canonical: "/",
  },
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
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Noto+Serif+SC:wght@400;500;600;700&display=swap" />
        <link rel="stylesheet" href="/static/css/styles.css?v=72" />
      </head>
      <body>
        <div className="home-lightfield" aria-hidden="true" />
        <HomeLegacyEffects />
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
