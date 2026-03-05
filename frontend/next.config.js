const createNextIntlPlugin = require("next-intl/plugin");
const withNextIntl = createNextIntlPlugin();

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["three", "react-force-graph-3d"],
  async redirects() {
    return [
      { source: "/c5isr", destination: "/warroom", permanent: true },
      { source: "/navigator", destination: "/planner", permanent: true },
      { source: "/monitor", destination: "/warroom", permanent: true },
    ];
  },
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://backend:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
    ];
  },
};

module.exports = withNextIntl(nextConfig);
