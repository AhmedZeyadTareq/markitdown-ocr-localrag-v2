import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The UI runs entirely in the browser, so `next build` emits static files (web/out) that the Python API serves
  output: "export",
  // The dev badge sits on top of the library's status line
  devIndicators: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
