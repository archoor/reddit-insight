import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getFormatter, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import type { Post, PostAnalysis } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreRing } from "@/components/shared/score-ring";
import { ArrowLeft, ExternalLink, MessageSquare, TrendingUp, Zap } from "lucide-react";
import { absoluteUrl } from "@/lib/locale-path";

interface PageProps {
  params: Promise<{ locale: string; name: string; slug: string }>;
}

const DATA_SERVICE_URL = process.env.DATA_SERVICE_URL || "http://localhost:8001";
const INSIGHT_SERVICE_URL = process.env.INSIGHT_SERVICE_URL || "http://localhost:8002";

async function getPostBySlug(slug: string): Promise<Post | null> {
  try {
    const res = await fetch(`${DATA_SERVICE_URL}/api/posts?search=${encodeURIComponent(slug)}&page_size=5`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.items.find((p: Post) => p.slug === slug) || data.items[0] || null;
  } catch {
    return null;
  }
}

async function getAnalysis(postId: number): Promise<PostAnalysis | null> {
  try {
    const res = await fetch(`${INSIGHT_SERVICE_URL}/api/analysis/${postId}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug, locale } = await params;
  const t = await getTranslations({ locale, namespace: "insight" });
  const post = await getPostBySlug(slug);
  if (!post) return { title: t("notFoundTitle") };

  return {
    title: post.title,
    description: `Business analysis of Reddit discussion: "${post.title}" from r/${post.subreddit_name}`,
    openGraph: {
      title: post.title,
      description: `AI-analyzed Reddit post: pain points, willingness to pay, and business opportunity score.`,
      type: "article",
    },
  };
}

export default async function InsightDetailPage({ params }: PageProps) {
  const { name, slug, locale } = await params;
  const post = await getPostBySlug(slug);
  if (!post) notFound();

  const analysis = await getAnalysis(post.id);
  const t = await getTranslations("insight");
  const ts = await getTranslations("scoreRing");
  const format = await getFormatter();

  type StrRecord = Record<
    string,
    string | number | boolean | string[] | null | undefined | Array<Record<string, string | number | boolean | null | undefined>>
  >;

  /** API 可能返回扩展字段，与 `PostAnalysis` 类型未完全同步 */
  type AnalysisExtended = PostAnalysis & {
    opportunity_score?: number;
    summary?: string;
    opportunity_assessment?: StrRecord;
  };
  const ax = analysis as AnalysisExtended | null;
  const painPoints = (ax?.pain_points as StrRecord | undefined) ?? {};
  const wtp = (ax?.willingness_to_pay as StrRecord | undefined) ?? {};
  const tech = (ax?.tech_feasibility as StrRecord | undefined) ?? {};
  const competition = (ax?.competition as StrRecord | undefined) ?? {};
  const opsRisk = (ax?.operational_risks as StrRecord | undefined) ?? {};
  const assessment = (ax?.opportunity_assessment as StrRecord | undefined) ?? {};

  const insightPath = `/insights/subreddit/${name}/${slug}`;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "AnalysisNewsArticle",
    headline: post.title,
    description: ax?.summary || `Analysis of Reddit discussion: ${post.title}`,
    url: absoluteUrl(locale, insightPath),
    author: { "@type": "Organization", name: "Reddit Insight" },
    datePublished: post.reddit_created_at || post.collected_at,
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": absoluteUrl(locale, insightPath),
    },
  };

  const dateLabel =
    post.reddit_created_at != null
      ? format.dateTime(new Date(post.reddit_created_at), { dateStyle: "medium" })
      : null;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
      <Link
        href="/opportunities"
        className="mb-6 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("back")}
      </Link>

      <div className="mb-8">
        <div className="flex flex-wrap gap-2 mb-3">
          <Badge variant="info">r/{post.subreddit_name}</Badge>
          <Badge variant={post.analysis_status === "done" ? "success" : "warning"}>{post.analysis_status}</Badge>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mb-3 leading-tight">{post.title}</h1>
        <div className="flex flex-wrap items-center gap-4 text-sm text-slate-500">
          <span className="flex items-center gap-1">
            <TrendingUp className="h-4 w-4" /> {post.score} {t("pts")}
          </span>
          <span className="flex items-center gap-1">
            <MessageSquare className="h-4 w-4" /> {post.num_comments} {t("comments")}
          </span>
          {dateLabel && <span>{dateLabel}</span>}
          {post.url && (
            <a
              href={post.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-blue-600 hover:text-blue-800"
            >
              <ExternalLink className="h-3 w-3" /> {t("viewReddit")}
            </a>
          )}
        </div>
        {post.selftext && (
          <div className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-700 line-clamp-4 border">
            {post.selftext}
          </div>
        )}
      </div>

      {!ax ? (
        <Card className="py-12 text-center">
          <CardContent>
            <Zap className="h-10 w-10 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500 mb-2">{t("noAnalysisTitle")}</p>
            <p className="text-sm text-slate-400">{t("noAnalysisHint")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-5">
          <Card className="bg-slate-900 text-white">
            <CardContent className="p-6 flex items-center gap-6">
              <ScoreRing
                score={ax.opportunity_score ?? ax.max_opportunity_score}
                size="lg"
                label={ts("opportunity")}
              />
              <div>
                {assessment?.title && <h2 className="text-lg font-bold mb-2">{String(assessment.title)}</h2>}
                {ax.summary && <p className="text-slate-300 text-sm">{ax.summary}</p>}
                {assessment?.recommendation && (
                  <Badge
                    className="mt-3"
                    variant={
                      assessment.recommendation === "Build"
                        ? "success"
                        : assessment.recommendation === "Validate"
                          ? "warning"
                          : "destructive"
                    }
                  >
                    {t("recommendation")} {String(assessment.recommendation)}
                  </Badge>
                )}
                <p className="text-xs text-slate-500 mt-3">
                  {t("analyzedComments", {
                    sampled: ax.comments_sampled,
                    total: ax.comments_total,
                    model: ax.model_used,
                  })}
                </p>
              </div>
            </CardContent>
          </Card>

          {painPoints && (
            <AnalysisSection
              title={t("painPoints")}
              icon="🔥"
              content={
                <div className="space-y-4">
                  {painPoints.top_pain_point && (
                    <div className="rounded-lg bg-red-50 border border-red-100 p-3 text-sm font-medium text-red-800">
                      {painPoints.top_pain_point as string}
                    </div>
                  )}
                  {(painPoints.items as Array<Record<string, unknown>>)?.map((pp, i) => (
                    <div key={i} className="border-l-2 border-red-300 pl-4">
                      <p className="font-medium text-sm">{String(pp.description ?? "")}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        {t("intensityLine", {
                          intensity: Number(pp.intensity ?? 0),
                          mentions: Number(pp.frequency_mentions ?? 0),
                        })}
                      </p>
                      {(pp.evidence_quotes as string[] | undefined)?.slice(0, 2).map((q, qi) => (
                        <blockquote
                          key={qi}
                          className="text-xs italic text-slate-600 mt-1 bg-slate-50 px-2 py-1 rounded"
                        >
                          &quot;{q}&quot;
                        </blockquote>
                      ))}
                    </div>
                  ))}
                </div>
              }
            />
          )}

          {wtp && (
            <AnalysisSection
              title={t("willingnessToPay")}
              icon="💰"
              content={
                <div className="space-y-3">
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-green-600">{wtp.score as number}/10</p>
                      <p className="text-xs text-slate-500">{t("wtpScore")}</p>
                    </div>
                    {wtp.price_sensitivity && (
                      <Badge
                        variant={
                          wtp.price_sensitivity === "low"
                            ? "success"
                            : wtp.price_sensitivity === "medium"
                              ? "warning"
                              : "destructive"
                        }
                      >
                        {t("priceSensitivity", { level: String(wtp.price_sensitivity) })}
                      </Badge>
                    )}
                    {wtp.suggested_price_range && (
                      <span className="text-sm font-medium text-green-700">
                        {String(wtp.suggested_price_range)}
                      </span>
                    )}
                  </div>
                  {(wtp.signals as Array<Record<string, unknown>>)?.map((s, i) => (
                    <div key={i} className="text-sm bg-green-50 rounded-lg p-3">
                      <p className="font-medium text-green-800">{String(s.type ?? "")}</p>
                      {!!s.quote && (
                        <p className="text-green-700 italic text-xs mt-1">&quot;{String(s.quote)}&quot;</p>
                      )}
                    </div>
                  ))}
                </div>
              }
            />
          )}

          {tech && (
            <AnalysisSection
              title={t("techFeasibility")}
              icon="⚙️"
              content={
                <div className="space-y-3">
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-blue-600">{tech.feasibility_score as number}/10</p>
                      <p className="text-xs text-slate-500">{t("feasibility")}</p>
                    </div>
                    <div>
                      <Badge>
                        {String(tech.complexity ?? "")} {t("complexitySuffix")}
                      </Badge>
                      {tech.estimated_dev_time && (
                        <p className="text-xs text-slate-500 mt-1">~{String(tech.estimated_dev_time)}</p>
                      )}
                    </div>
                  </div>
                  {(tech.tech_stack_suggested as string[] | undefined)?.length ? (
                    <div>
                      <p className="text-xs text-slate-500 mb-2">{t("suggestedStack")}</p>
                      <div className="flex flex-wrap gap-1">
                        {(tech.tech_stack_suggested as string[]).map((stk, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {stk}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {(tech.key_challenges as string[] | undefined)?.map((c, i) => (
                    <p key={i} className="text-sm text-slate-600">
                      ⚡ {c}
                    </p>
                  ))}
                </div>
              }
            />
          )}

          {competition && (
            <AnalysisSection
              title={t("marketCompetition")}
              icon="🏆"
              content={
                <div className="space-y-3">
                  {competition.market_gap && (
                    <div className="rounded-lg bg-purple-50 border border-purple-100 p-3 text-sm text-purple-800">
                      {String(competition.market_gap)}
                    </div>
                  )}
                  {(competition.competitors_mentioned as Array<Record<string, unknown>>)?.map((c, i) => (
                    <div key={i} className="border rounded-lg p-3">
                      <p className="font-medium text-sm">{String(c.name ?? "")}</p>
                      {!!c.weakness && (
                        <p className="text-xs text-slate-600 mt-1">
                          {t("weakness")} {String(c.weakness)}
                        </p>
                      )}
                      {!!c.quote && (
                        <p className="text-xs italic text-slate-500 mt-1">&quot;{String(c.quote)}&quot;</p>
                      )}
                    </div>
                  ))}
                  {(competition.differentiation_opportunities as string[] | undefined)?.map((d, i) => (
                    <p key={i} className="text-sm text-slate-600">
                      ✨ {d}
                    </p>
                  ))}
                </div>
              }
            />
          )}

          {opsRisk && (
            <AnalysisSection
              title={t("sustainabilityTitle")}
              icon="🔄"
              content={
                <div className="space-y-2">
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-purple-600">{opsRisk.sustainability_score as number}/10</p>
                      <p className="text-xs text-slate-500">{t("sustainability")}</p>
                    </div>
                    <Badge variant={opsRisk.recurring_need ? "success" : "secondary"}>
                      {opsRisk.recurring_need ? t("recurringNeed") : t("oneTimeNeed")}
                    </Badge>
                  </div>
                  {(opsRisk.churn_risks as string[] | undefined)?.map((r, i) => (
                    <p key={i} className="text-sm text-slate-600">
                      ⚠️ {r}
                    </p>
                  ))}
                  {opsRisk.moat_potential && (
                    <p className="text-sm text-purple-700 bg-purple-50 p-2 rounded">
                      🛡️ {t("moat")} {String(opsRisk.moat_potential)}
                    </p>
                  )}
                </div>
              }
            />
          )}
        </div>
      )}

      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
    </div>
  );
}

function AnalysisSection({
  title,
  icon,
  content,
}: {
  title: string;
  icon: string;
  content: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <span>{icon}</span> {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{content}</CardContent>
    </Card>
  );
}
