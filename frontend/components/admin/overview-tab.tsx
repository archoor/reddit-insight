"use client";

import { useTranslations } from "next-intl";
import { type StatsOverview } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/utils";
import { Database, MessageSquare, BarChart3, ListChecks, Zap, ArrowRight } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  queued: "bg-blue-100 text-blue-800",
  analyzing: "bg-indigo-100 text-indigo-800",
  done: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  skipped: "bg-slate-100 text-slate-600",
};

interface Props {
  stats: StatsOverview;
  onBatchAnalysis: () => void;
  onGoToPosts: () => void;
}

export function OverviewTab({ stats, onBatchAnalysis, onGoToPosts }: Props) {
  const t = useTranslations("admin.overview");

  const metricCards = [
    { label: t("totalPosts"), value: formatNumber(stats.total_posts), icon: Database, bg: "bg-blue-50", icon_c: "text-blue-500" },
    { label: t("comments"), value: formatNumber(stats.total_comments), icon: MessageSquare, bg: "bg-violet-50", icon_c: "text-violet-500" },
    { label: t("channels"), value: stats.total_subreddits, icon: BarChart3, bg: "bg-emerald-50", icon_c: "text-emerald-500" },
    { label: t("tasks"), value: stats.total_tasks, icon: ListChecks, bg: "bg-amber-50", icon_c: "text-amber-500" },
  ];

  const totalStatusCount = Object.values(stats.analysis_status_distribution).reduce((a, b) => a + b, 0) || 1;
  const maxSubCount = Math.max(...stats.posts_by_subreddit.map((r) => r.count), 1);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {metricCards.map((card) => (
          <Card key={card.label} className="overflow-hidden">
            <CardContent className={`p-4 flex items-center gap-3 ${card.bg}`}>
              <div className={`rounded-lg bg-white/70 p-2.5 ${card.icon_c}`}>
                <card.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{card.value}</p>
                <p className="text-xs text-slate-500">{card.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-700">{t("analysisStatus")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {Object.entries(stats.analysis_status_distribution).map(([status, count]) => (
              <div key={status} className="flex items-center gap-3">
                <span
                  className={`inline-flex min-w-[72px] justify-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[status] ?? "bg-slate-100 text-slate-600"}`}
                >
                  {status}
                </span>
                <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-slate-400 transition-all"
                    style={{ width: `${(count / totalStatusCount) * 100}%` }}
                  />
                </div>
                <span className="w-8 text-right text-sm font-medium text-slate-700">{count}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-700">{t("postsByChannel")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {stats.posts_by_subreddit.length === 0 ? (
              <p className="text-sm text-slate-400 py-4 text-center">{t("noData")}</p>
            ) : (
              stats.posts_by_subreddit.map((row) => (
                <div key={row.subreddit} className="flex items-center gap-3">
                  <span className="w-24 truncate text-sm font-medium text-slate-700">r/{row.subreddit}</span>
                  <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-indigo-400 transition-all"
                      style={{ width: `${(row.count / maxSubCount) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-medium text-slate-700">{row.count}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-slate-700">{t("shortcuts")}</CardTitle>
        </CardHeader>
        <CardContent>
          <Button onClick={onBatchAnalysis} className="gap-2">
            <Zap className="h-4 w-4" />
            {t("batchAnalyze")}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold text-slate-700">{t("recentPosts")}</CardTitle>
            <button
              type="button"
              onClick={onGoToPosts}
              className="flex items-center gap-1 text-xs text-indigo-600 hover:underline"
            >
              {t("viewAll")} <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        </CardHeader>
        <CardContent>
          {stats.recent_posts.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-4">{t("noData")}</p>
          ) : (
            <div className="divide-y">
              {(stats.recent_posts as Record<string, unknown>[]).map((p) => (
                <div key={p.id as string} className="flex items-center justify-between py-3 gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate text-slate-800">{p.title as string}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      r/{p.subreddit_name as string} · {formatNumber(p.score as number)} pts
                    </p>
                  </div>
                  <span
                    className={`shrink-0 inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[p.analysis_status as string] ?? "bg-slate-100 text-slate-600"}`}
                  >
                    {p.analysis_status as string}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
