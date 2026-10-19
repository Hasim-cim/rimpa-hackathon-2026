import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dev only: in production Vercel routes /api/* to the Python service.
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/:path*" }];
  },
};

export default nextConfig;
