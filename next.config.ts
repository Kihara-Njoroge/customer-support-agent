import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',  // This exports static HTML/JS files
  images: {
    unoptimized: true  // Required for static export
  },
  // Local dev only: browser calls /api on :3000; forward to FastAPI on :8000.
  // (Ignored when you `next build` with static export — use Docker or App Runner for prod.)
  async rewrites() {
    const backend = process.env.BACKEND_URL ?? 'http://localhost:8000';
    return [
      { source: '/api', destination: `${backend}/api` },
      { source: '/api/:path*', destination: `${backend}/api/:path*` },
      { source: '/history', destination: `${backend}/history` },
      { source: '/history/:path*', destination: `${backend}/history/:path*` },
    ];
  },
};

export default nextConfig;