import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const nextConfig: NextConfig = {
  // 后端 API 代理（开发环境）
  rewrites: async () => [
    {
      source: "/api/data/:path*",
      destination: `${process.env.DATA_SERVICE_URL || "http://localhost:8001"}/:path*`,
    },
    {
      source: "/api/insight/:path*",
      destination: `${process.env.INSIGHT_SERVICE_URL || "http://localhost:8002"}/:path*`,
    },
  ],

  // 允许图片域名（如果用到 Reddit 图片）
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.redd.it" },
      { protocol: "https", hostname: "i.reddit.com" },
    ],
  },
};

export default withNextIntl(nextConfig);
