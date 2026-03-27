import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { Lightbulb, TrendingUp, Users, Zap } from "lucide-react";
import { insightApi, type Opportunity } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreRing } from "@/components/shared/score-ring";
import { withLocalePrefix } from "@/lib/locale-path";

export const dynamic = "force-dynamic";
export const revalidate = 3600;

type PageProps = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "meta" });
  const title = t("home.title");
  const description = t("home.description");
  return {
    title,
    description,
    openGraph: { title, description },
  };
}

async function getTopOpportunities(): Promise<Opportunity[]> {
  try {
    return await insightApi.getTopOpportunities(12);
  } catch {
    return [];
  }
}

export default async function HomePage({ params }: PageProps) {
  const { locale } = await params;
  const opportunities = await getTopOpportunities();
  const t = await getTranslations("home");
  const tm = await getTranslations({ locale, namespace: "meta" });
  const ts = await getTranslations("scoreRing");
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  const oppSearchTemplate = `${siteUrl}${withLocalePrefix(locale, "/opportunities")}?search={search_term_string}`;

  return (
    <div className="min-h-screen">
      <section className="bg-gradient-to-b from-slate-900 to-slate-800 py-20 text-white">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-sm">
            <Zap className="h-4 w-4 text-yellow-400" />
            <span>{t("heroBadge")}</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold leading-tight mb-6">
            {t("heroTitleLine1")}
            <br />
            <span className="text-blue-400">{t("heroTitleLine2")}</span>
          </h1>
          <p className="text-xl text-slate-300 mb-8 max-w-2xl mx-auto">{t("heroBody")}</p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/opportunities"
              className="rounded-lg bg-blue-500 px-6 py-3 font-semibold hover:bg-blue-600 transition-colors"
            >
              {t("ctaBrowse")}
            </Link>
            <Link
              href="#featured"
              className="rounded-lg bg-white/10 px-6 py-3 font-semibold hover:bg-white/20 transition-colors"
            >
              {t("ctaFeatured")}
            </Link>
          </div>
        </div>
      </section>

      <section className="border-b bg-white py-6">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap justify-center gap-12 text-center">
            {[
              { icon: TrendingUp, label: t("statPosts"), value: "10,000+" },
              { icon: Users, label: t("statCommunities"), value: "50+" },
              { icon: Lightbulb, label: t("statOpportunities"), value: String(opportunities.length) },
            ].map((item) => (
              <div key={item.label} className="flex flex-col items-center gap-1">
                <item.icon className="h-6 w-6 text-blue-500" />
                <p className="text-2xl font-bold text-slate-900">{item.value}</p>
                <p className="text-sm text-slate-500">{item.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="featured" className="py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-10 text-center">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">{t("featuredTitle")}</h2>
            <p className="text-slate-600 max-w-xl mx-auto">{t("featuredSubtitle")}</p>
          </div>

          {opportunities.length === 0 ? (
            <div className="text-center py-16 text-slate-400">
              <Lightbulb className="h-12 w-12 mx-auto mb-4 opacity-30" />
              <p>{t("emptyOpportunities")}</p>
            </div>
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {opportunities.map((opp, i) => (
                <HomeOpportunityCard
                  key={opp.id}
                  opportunity={opp}
                  rank={i + 1}
                  painLabel={t("cardPain")}
                  wtpLabel={t("cardWtp")}
                  difficultyLabel={t("cardDifficulty")}
                  scoreLabel={ts("score")}
                />
              ))}
            </div>
          )}

          {opportunities.length > 0 && (
            <div className="mt-10 text-center">
              <Link
                href="/opportunities"
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-6 py-3 text-sm font-medium hover:bg-slate-50 transition-colors"
              >
                {t("viewAll")}
              </Link>
            </div>
          )}
        </div>
      </section>

      <section className="bg-slate-50 py-16 border-t">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-slate-900 mb-10 text-center">{t("howTitle")}</h2>
          <div className="grid gap-8 sm:grid-cols-3">
            {[
              { step: "1", title: t("how1Title"), desc: t("how1Desc") },
              { step: "2", title: t("how2Title"), desc: t("how2Desc") },
              { step: "3", title: t("how3Title"), desc: t("how3Desc") },
            ].map((item) => (
              <div key={item.step} className="flex flex-col items-center text-center">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-700 font-bold text-xl">
                  {item.step}
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">{item.title}</h3>
                <p className="text-sm text-slate-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "WebSite",
            name: "Reddit Insight",
            url: siteUrl,
            description: tm("root.description"),
            potentialAction: {
              "@type": "SearchAction",
              target: { "@type": "EntryPoint", urlTemplate: oppSearchTemplate },
              "query-input": "required name=search_term_string",
            },
          }),
        }}
      />
    </div>
  );
}

async function HomeOpportunityCard({
  opportunity: opp,
  rank,
  painLabel,
  wtpLabel,
  difficultyLabel,
  scoreLabel,
}: {
  opportunity: Opportunity;
  rank: number;
  painLabel: string;
  wtpLabel: string;
  difficultyLabel: string;
  scoreLabel: string;
}) {
  return (
    <Link href={`/opportunities/${opp.id}`}>
      <Card className="h-full hover:shadow-md transition-shadow cursor-pointer group">
        <CardContent className="p-5">
          <div className="flex items-start justify-between mb-3">
            <span className="text-xs text-slate-400 font-medium">#{rank}</span>
            <ScoreRing score={opp.score} size="sm" label={scoreLabel} />
          </div>
          <h3 className="font-semibold text-slate-900 mb-2 leading-tight group-hover:text-blue-700 transition-colors">
            {opp.title}
          </h3>
          <p className="text-sm text-slate-500 mb-4 line-clamp-2">
            {String((opp as { description?: string }).description ?? opp.recommendation ?? "")}
          </p>
          <div className="flex flex-wrap gap-2">
            <Badge variant="info" className="text-xs">
              r/{opp.subreddit_name}
            </Badge>
            {opp.monetization_model && (
              <Badge variant="outline" className="text-xs">
                {opp.monetization_model}
              </Badge>
            )}
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            {[
              { label: painLabel, value: opp.pain_point_intensity },
              { label: wtpLabel, value: opp.willingness_to_pay_score },
              { label: difficultyLabel, value: 10 - opp.tech_difficulty + 1 },
            ].map((m) => (
              <div key={m.label} className="rounded-md bg-slate-50 py-1.5">
                <p className="text-sm font-bold text-slate-700">{m.value}/10</p>
                <p className="text-xs text-slate-400">{m.label}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
