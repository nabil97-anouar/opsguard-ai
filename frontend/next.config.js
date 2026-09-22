/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep production browser verification separate from a running dev server.
  distDir: process.env.OPSGUARD_NEXT_DIST_DIR || ".next",
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false
};

module.exports = nextConfig;
