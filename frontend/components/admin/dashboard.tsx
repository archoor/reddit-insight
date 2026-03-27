"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { dataApi, insightApi, type CollectTask, type StatsOverview, type Subreddit } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { RefreshCw, Database, Radio, ListChecks, FileText } from "lucide-react";

import { OverviewTab } from "./overview-tab";
import { ChannelsTab } from "./channels-tab";
import { TasksTab } from "./tasks-tab";
import { PostsTab } from "./posts-tab";

interface ToastState {
  msg: string;
  type: "success" | "error";
}

function Toast({ toast, onDismiss }: { toast: ToastState; onDismiss: () => void }) {
  return (
    <div
      onClick={onDismiss}
      className={`
        fixed bottom-6 right-6 z-50 cursor-pointer flex items-center gap-2 rounded-xl
        px-4 py-3 text-sm font-medium shadow-lg transition-all
        ${toast.type === "error" ? "bg-red-600 text-white" : "bg-slate-900 text-white"}
      `}
    >
      {toast.msg}
      <span className="ml-1 text-white/60 text-xs">×</span>
    </div>
  );
}

type TabKey = "overview" | "channels" | "tasks" | "posts";

export function AdminDashboard() {
  const t = useTranslations("admin");
  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [tasks, setTasks] = useState<CollectTask[]>([]);
  const [subreddits, setSubreddits] = useState<Subreddit[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [toast, setToast] = useState<ToastState | null>(null);

  const tabs: { key: TabKey; label: string; icon: React.ElementType }[] = [
    { key: "overview", label: t("tabs.overview"), icon: Database },
    { key: "channels", label: t("tabs.channels"), icon: Radio },
    { key: "tasks", label: t("tabs.tasks"), icon: ListChecks },
    { key: "posts", label: t("tabs.posts"), icon: FileText },
  ];

  const showToast = useCallback((msg: string, type: "success" | "error" = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  }, []);

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const [s, ta, sr] = await Promise.allSettled([
        dataApi.getStats(),
        dataApi.getTasks(),
        dataApi.getSubreddits(),
      ]);
      if (s.status === "fulfilled") setStats(s.value);
      if (ta.status === "fulfilled") setTasks(ta.value);
      if (sr.status === "fulfilled") setSubreddits(sr.value);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleBatchAnalysis = async () => {
    try {
      const res = await insightApi.triggerBatchAnalysis({ max_posts: 20 });
      showToast(t("toast.batchTriggered", { count: res.triggered }));
    } catch (e) {
      showToast(`${(e as Error).message}`, "error");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center space-y-3">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-500" />
          <p className="text-sm text-slate-500">{t("loading")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t("dashboardTitle")}</h1>
          <p className="text-sm text-slate-500 mt-0.5">{t("dashboardSubtitle")}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => loadData()}
          disabled={refreshing}
          className="shrink-0 gap-1.5"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          {t("refresh")}
        </Button>
      </div>

      <div className="mb-6 flex gap-0.5 overflow-x-auto border-b border-slate-200">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`
              flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
              ${
                activeTab === key
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
              }
            `}
          >
            <Icon className="h-4 w-4" />
            {label}
            {key === "tasks" && tasks.filter((x) => x.status === "running").length > 0 && (
              <span className="ml-0.5 rounded-full bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700 font-semibold">
                {tasks.filter((x) => x.status === "running").length}
              </span>
            )}
          </button>
        ))}
      </div>

      {activeTab === "overview" &&
        (stats ? (
          <OverviewTab
            stats={stats}
            onBatchAnalysis={handleBatchAnalysis}
            onGoToPosts={() => setActiveTab("posts")}
          />
        ) : (
          <div className="rounded-xl border-2 border-dashed border-slate-200 py-20 text-center text-slate-400 space-y-2">
            <p className="text-base font-medium">{t("cannotConnectTitle")}</p>
            <p className="text-sm">
              {t("cannotConnectHint")}{" "}
              <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">http://localhost:8001</code>
            </p>
            <button type="button" onClick={() => loadData()} className="mt-3 text-sm text-indigo-600 hover:underline">
              {t("retry")}
            </button>
          </div>
        ))}

      {activeTab === "channels" && (
        <ChannelsTab subreddits={subreddits} onRefresh={() => loadData(true)} onToast={showToast} />
      )}

      {activeTab === "tasks" && (
        <TasksTab tasks={tasks} onTasksChange={setTasks} onToast={showToast} />
      )}

      {activeTab === "posts" && <PostsTab subreddits={subreddits} onToast={showToast} />}

      {toast && <Toast toast={toast} onDismiss={() => setToast(null)} />}
    </div>
  );
}
