import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // The repo root has its own package.json (for the dev script),
  // so tell Next.js explicitly that this folder is the frontend's root.
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;