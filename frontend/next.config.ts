import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const backendOrigin =
      process.env.BACKEND_ORIGIN ??
      process.env.API_BASE_URL ??
      process.env.NEXT_PUBLIC_API_BASE_URL ??
      "http://127.0.0.1:8000";

    return [
      { source: "/api/:path*", destination: `${backendOrigin}/api/:path*` },
      { source: "/static/:path*", destination: `${backendOrigin}/static/:path*` },
      { source: "/uploads/:path*", destination: `${backendOrigin}/uploads/:path*` },
      { source: "/upload", destination: `${backendOrigin}/upload` },
      { source: "/upload/:path*", destination: `${backendOrigin}/upload/:path*` },
      { source: "/login", destination: `${backendOrigin}/login` },
      { source: "/login/:path*", destination: `${backendOrigin}/login/:path*` },
    ];
  },
};

export default nextConfig;
