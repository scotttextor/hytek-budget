import type { NextConfig } from "next";

// MOTHBALLED 2026-04-22 — app superseded by hytek-install.
// Every HTTP path redirects to the new app's dashboard.
// Using 307 (temporary) rather than 308 so browsers don't aggressively cache
// the redirect — lets us un-mothball later if needed.
//
// To un-mothball: delete the `redirects()` block below and redeploy.
const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/:path*",
        destination: "https://hytek-install.vercel.app/dashboard",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
