import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { insightApi, type Opportunity } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreRing } from "@/components/shared/score-ring";
import { absoluteUrl } from "@/lib/locale-path";

export const dynamic = "force-dynamic";
export const revalidate = 1800;

type PageProps = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "meta" });
  const title = t("opportunities.title");
  const description = t("opportunities.description");
  return {
    title,
    description,
    openGraph: { title: `${title} | Reddit Insight`, description },
  };
}

async function getOpportunities() {
  try {
    return await insightApi.getOpportunities({ page: 1, page_size: 50, min_score: 0 });
  } catch {
    return { items: [], total: 0, page: 1, page_size: 50 };
  }
}

export default async function OpportunitiesPage({ params }: PageProps) {
  const { locale } = await params;
  const data = await getOpportunities();
  const t = await getTranslations("opportunities");
  const ts = await getTranslations("scoreRing");
  const jsonLdName = t("jsonLdName");
  const jsonLdDesc = t("jsonLdDesc");

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-slate-900 mb-3">{t("title")}</h1>
        <p className="text-slate-600 max-w-2xl">{t("subtitle", { count: data.total })}</p>
      </div>

      {data.items.length === 0 ? (
        <div className="py-24 text-center text-slate-400">
          <p className="text-lg">{t("empty")}</p>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((opp, i) => (
            <ListOpportunityCard
              key={opp.id}
              opportunity={opp}
              rank={i + 1}
              painLabel={t("cardPain")}
              wtpLabel={t("cardWtp")}
              easeLabel={t("cardEase")}
              scoreLabel={ts("score")}
            />
          ))}
        </div>
      )}

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "ItemList",
            name: jsonLdName,
            description: jsonLdDesc,
            numberOfItems: data.total,
            itemListElement: data.items.map((opp, i) => ({
              "@type": "ListItem",
              position: i + 1,
              name: opp.title,
              description: String((opp as { description?: string }).description ?? opp.title),
              url: absoluteUrl(locale, `/opportunities/${opp.id}`),
            })),
          }),
        }}
      />
    </div>
  );
}

function ListOpportunityCard({
  opportunity: opp,
  rank,
  painLabel,
  wtpLabel,
  easeLabel,
  scoreLabel,
}: {
  opportunity: Opportunity;
  rank: number;
  painLabel: string;
  wtpLabel: string;
  easeLabel: string;
  scoreLabel: string;
}) {
  return (
    <Link href={`/opportunities/${opp.id}`}>
      <Card className="h-full hover:shadow-md transition-all cursor-pointer group border-slate-200">
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex gap-2 items-center">
              <span className="text-sm text-slate-400 font-medium">#{rank}</span>
              <Badge variant="info" className="text-xs">
                r/{opp.subreddit_name}
              </Badge>
            </div>
            <ScoreRing score={opp.score} size="sm" label={scoreLabel} />
          </div>

          <h2 className="font-semibold text-slate-900 mb-2 leading-tight group-hover:text-blue-700 transition-colors">
            {opp.title}
          </h2>
          <p className="text-sm text-slate-500 mb-4 line-clamp-2">
            {String((opp as { description?: string }).description ?? opp.recommendation ?? "")}
          </p>

          {opp.target_audience && (
            <p className="text-xs text-slate-400 mb-3">👥 {opp.target_audience}</p>
          )}

          {opp.monetization_model && (
            <Badge variant="outline" className="text-xs mb-3">
              {opp.monetization_model}
            </Badge>
          )}

          <div className="grid grid-cols-3 gap-2 text-center mt-3">
            {[
              { label: painLabel, value: opp.pain_point_intensity, color: "text-red-600" },
              { label: wtpLabel, value: opp.willingness_to_pay_score, color: "text-green-600" },
              { label: easeLabel, value: 10 - opp.tech_difficulty + 1, color: "text-blue-600" },
            ].map((m) => (
              <div key={m.label} className="rounded-md bg-slate-50 py-1.5">
                <p className={`text-sm font-bold ${m.color}`}>{m.value}/10</p>
                <p className="text-xs text-slate-400">{m.label}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
