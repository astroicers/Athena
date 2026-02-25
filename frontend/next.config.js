/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["three", "react-force-graph-3d"],
};

module.exports = nextConfig;
