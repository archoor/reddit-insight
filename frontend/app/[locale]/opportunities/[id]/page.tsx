import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { notFound } from "next/navigation";
import { insightApi, type OpportunityDetail } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreRing } from "@/components/shared/score-ring";
import { ArrowLeft, CheckCircle, AlertTriangle, Users, DollarSign, Code2, TrendingUp } from "lucide-react";

interface PageProps {
  params: Promise<{ locale: string; id: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id, locale } = await params;
  const t = await getTranslations({ locale, namespace: "opportunityDetail" });
  try {
    const opp = await insightApi.getOpportunity(parseInt(id));
    return {
      title: opp.title,
      description: opp.description,
      openGraph: { title: opp.title, description: opp.description, type: "article" },
    };
  } catch {
    return { title: t("notFoundTitle") };
  }
}

async function getOpportunity(id: number): Promise<OpportunityDetail | null> {
  try {
    return await insightApi.getOpportunity(id);
  } catch {
    return null;
  }
}

export default async function OpportunityDetailPage({ params }: PageProps) {
  const { id } = await params;
  const opp = await getOpportunity(parseInt(id));
  const t = await getTranslations("opportunityDetail");
  const ts = await getTranslations("scoreRing");

  if (!opp) notFound();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: opp.title,
    description: opp.description,
    author: { "@type": "Organization", name: "Reddit Insight" },
    datePublished: opp.created_at,
    about: {
      "@type": "Thing",
      name: opp.target_audience,
      description: opp.description,
    },
  };

  const metrics = [
    { label: t("painIntensity"), value: opp.pain_point_intensity, max: 10, color: "bg-red-500" },
    { label: t("willingnessToPay"), value: opp.willingness_to_pay_score, max: 10, color: "bg-green-500" },
    { label: t("easeOfBuild"), value: 10 - opp.tech_difficulty + 1, max: 10, color: "bg-blue-500" },
    { label: t("sustainability"), value: opp.sustainability_score, max: 10, color: "bg-purple-500" },
  ];

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
      <Link
        href="/opportunities"
        className="mb-6 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("back")}
      </Link>

      <div className="mb-8 flex items-start gap-6">
        <ScoreRing score={opp.score} size="lg" label={ts("score")} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap gap-2 mb-3">
            <Badge variant="info">r/{opp.subreddit_name}</Badge>
            {opp.monetization_model && <Badge variant="outline">{opp.monetization_model}</Badge>}
          </div>
          <h1 className="text-2xl font-bold text-slate-900 leading-tight mb-3">{opp.title}</h1>
          <p className="text-slate-600">{opp.description}</p>
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4" /> {t("scoreBreakdown")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {metrics.map((m) => (
              <div key={m.label} className="text-center">
                <div className="relative h-2 bg-slate-100 rounded-full mb-2">
                  <div
                    className={`absolute left-0 top-0 h-full rounded-full ${m.color}`}
                    style={{ width: `${(m.value / m.max) * 100}%` }}
                  />
                </div>
                <p className="text-lg font-bold text-slate-800">
                  {m.value}
                  <span className="text-sm text-slate-400">/{m.max}</span>
                </p>
                <p className="text-xs text-slate-500">{m.label}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-5 sm:grid-cols-2 mb-6">
        {opp.target_audience && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Users className="h-4 w-4" /> {t("targetAudience")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-700">{opp.target_audience}</p>
            </CardContent>
          </Card>
        )}
        {opp.monetization_model && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <DollarSign className="h-4 w-4" /> {t("monetization")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-700">{opp.monetization_model}</p>
              {opp.market_size_estimate && (
                <p className="text-sm text-slate-500 mt-2">{opp.market_size_estimate}</p>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {opp.key_features && opp.key_features.length > 0 && (
        <Card className="mb-5">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Code2 className="h-4 w-4" /> {t("mvpFeatures")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {opp.key_features.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {opp.competitors && opp.competitors.length > 0 && (
        <Card className="mb-5">
          <CardHeader>
            <CardTitle className="text-base">{t("competitors")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {opp.competitors.map((c, i) => (
                <Badge key={i} variant="secondary">
                  {c}
                </Badge>
              ))}
            </div>
            {opp.differentiation && (
              <p className="mt-3 text-sm text-slate-600">
                <strong>{t("differentiation")}</strong> {opp.differentiation}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {opp.risks && opp.risks.length > 0 && (
        <Card className="mb-5">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-500" /> {t("keyRisks")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {opp.risks.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <AlertTriangle className="h-4 w-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
    </div>
  );
}
