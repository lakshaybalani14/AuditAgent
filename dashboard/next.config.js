const nextConfig = {
  // Allows isolated builds without cleaning or competing with a running dev server.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

module.exports = nextConfig;
