import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // 按需解析 barrel export，减小 motion 客户端包体
    optimizePackageImports: ["motion"],
  },
};

export default nextConfig;
