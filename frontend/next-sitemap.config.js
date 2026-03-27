/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
  generateRobotsTxt: true,
  changefreq: "daily",
  priority: 0.7,
  sitemapSize: 5000,

  exclude: ["/admin", "/admin/*", "/api/*"],

  robotsTxtOptions: {
    policies: [
      { userAgent: "*", allow: "/" },
      { userAgent: "*", disallow: ["/admin", "/api"] },
    ],
    additionalSitemaps: [
      `${process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"}/sitemap.xml`,
    ],
  },

  // 动态生成商机页面 sitemap，按 opportunity_score 设置 priority
  additionalPaths: async (config) => {
    const result = [];
    try {
      const INSIGHT_SERVICE_URL =
        process.env.INSIGHT_SERVICE_URL || "http://localhost:8002";
      const res = await fetch(
        `${INSIGHT_SERVICE_URL}/api/opportunities?page_size=100&min_score=0`
      );
      if (res.ok) {
        const data = await res.json();
        for (const opp of data.items || []) {
          const priority = Math.min(0.9, 0.4 + (opp.score / 100) * 0.5);
          result.push({
            loc: `/opportunities/${opp.id}`,
            changefreq: "weekly",
            priority: parseFloat(priority.toFixed(2)),
            lastmod: opp.updated_at || new Date().toISOString(),
          });
        }
      }
    } catch (e) {
      console.warn("[sitemap] Could not fetch opportunities:", e.message);
    }
    return result;
  },
};
