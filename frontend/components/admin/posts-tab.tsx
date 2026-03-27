"use client";

import { useState, useEffect, useCallback } from "react";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { type Post, type Comment, type Subreddit, dataApi, insightApi } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/utils";
import {
  ExternalLink,
  Zap,
  ChevronLeft,
  ChevronRight,
  Search,
  MessageSquare,
  Loader2,
  ChevronDown,
  ChevronUp,
  User,
  TrendingUp,
} from "lucide-react";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  queued: "bg-blue-100 text-blue-800",
  analyzing: "bg-indigo-100 text-indigo-800",
  done: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  skipped: "bg-slate-100 text-slate-600",
};

interface Filters {
  subreddit: string;
  status: string;
  minScore: string;
  search: string;
  page: number;
}

interface Props {
  subreddits: Subreddit[];
  onToast: (msg: string, type?: "success" | "error") => void;
}

function CommentPanel({ post }: { post: Post }) {
  const t = useTranslations("admin.posts");
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const loadComments = useCallback(async () => {
    if (loaded) {
      setOpen((v) => !v);
      return;
    }
    setOpen(true);
    setLoading(true);
    try {
      const data = await dataApi.getPostComments(post.id);
      setComments(data);
      setLoaded(true);
    } catch {
      setComments([]);
    } finally {
      setLoading(false);
    }
  }, [post.id, loaded]);

  if (!post.comments_fetched) return null;

  return (
    <div className="mt-2 border-t border-slate-100 pt-2">
      <button
        type="button"
        onClick={loadComments}
        className="flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
      >
        {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        {open ? t("toggleCommentsOpen") : t("toggleCommentsClosed", { count: post.num_comments })}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {loading ? (
            <div className="flex items-center gap-2 text-xs text-slate-400 py-2">
              <Loader2 className="h-3 w-3 animate-spin" /> {t("loadingComments")}
            </div>
          ) : comments.length === 0 ? (
            <p className="text-xs text-slate-400 py-2">{t("noComments")}</p>
          ) : (
            <>
              <p className="text-xs text-slate-400">{t("storedComments", { count: comments.length })}</p>
              <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
                {comments.map((c) => (
                  <div
                    key={c.id}
                    className={`rounded-lg border p-2.5 text-xs ${
                      c.depth === 0 ? "bg-white border-slate-200" : "bg-slate-50 border-slate-100 ml-4"
                    } ${c.is_sampled ? "border-l-2 border-l-indigo-400" : ""}`}
                  >
                    <div className="flex items-center gap-2 text-slate-400 mb-1">
                      <User className="h-3 w-3" />
                      <span className="font-medium text-slate-600">{c.author || "[deleted]"}</span>
                      <span className="flex items-center gap-0.5">
                        <TrendingUp className="h-2.5 w-2.5" />
                        {c.score}
                      </span>
                      {c.depth > 0 && (
                        <span className="rounded bg-slate-100 px-1 py-0">{t("depth", { depth: c.depth })}</span>
                      )}
                      {c.is_sampled && (
                        <span className="rounded bg-indigo-50 text-indigo-600 px-1 py-0 font-medium">
                          {t("sampled")}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-700 leading-relaxed whitespace-pre-wrap line-clamp-6">{c.body}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function postStatusLabel(t: (key: string) => string, status: string) {
  switch (status) {
    case "pending":
      return t("status.pending");
    case "queued":
      return t("status.queued");
    case "analyzing":
      return t("status.analyzing");
    case "done":
      return t("status.done");
    case "failed":
      return t("status.failed");
    case "skipped":
      return t("status.skipped");
    default:
      return status;
  }
}

export function PostsTab({ subreddits, onToast }: Props) {
  const t = useTranslations("admin.posts");
  const ta = useTranslations("admin");
  const format = useFormatter();
  const now = useNow();
  const [posts, setPosts] = useState<Post[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    subreddit: "",
    status: "",
    minScore: "",
    search: "",
    page: 1,
  });

  const PAGE_SIZE = 20;

  const fetchPosts = useCallback(
    async (f: Filters) => {
      setLoading(true);
      try {
        const params: Record<string, string | number> = {
          page: f.page,
          page_size: PAGE_SIZE,
        };
        if (f.subreddit) params.subreddit = f.subreddit;
        if (f.status) params.analysis_status = f.status;
        if (f.minScore) params.min_score = f.minScore;
        if (f.search) params.search = f.search;

        const res = await dataApi.getPosts(params);
        setPosts(res.items);
        setTotal(res.total);
      } catch (e) {
        onToast(`${ta("toast.postsLoadFailed")}: ${(e as Error).message}`, "error");
      } finally {
        setLoading(false);
      }
    },
    [onToast, ta]
  );

  useEffect(() => {
    fetchPosts(filters);
  }, [filters, fetchPosts]);

  const setFilter = <K extends keyof Filters>(key: K, val: Filters[K]) =>
    setFilters((f) => ({ ...f, [key]: val, page: key === "page" ? (val as number) : 1 }));

  const handleAnalyze = async (postId: number) => {
    try {
      await insightApi.triggerAnalysis(postId);
      onToast(ta("toast.analyzeTriggered"));
      setPosts((prev) => prev.map((p) => (p.id === postId ? { ...p, analysis_status: "queued" } : p)));
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    }
  };

  const handleFetchComments = async (postId: number) => {
    try {
      await dataApi.triggerCommentFetch(postId);
      onToast(ta("toast.commentsTriggered"));
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const inputCls =
    "h-9 rounded-md border border-slate-200 bg-white px-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300";

  const statusKeys = ["pending", "queued", "analyzing", "done", "failed", "skipped"] as const;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <select
          className={inputCls}
          value={filters.subreddit}
          onChange={(e) => setFilter("subreddit", e.target.value)}
        >
          <option value="">{t("allChannels")}</option>
          {subreddits.map((s) => (
            <option key={s.id} value={s.name}>
              r/{s.name}
            </option>
          ))}
        </select>

        <select className={inputCls} value={filters.status} onChange={(e) => setFilter("status", e.target.value)}>
          <option value="">{t("allStatus")}</option>
          {statusKeys.map((s) => (
            <option key={s} value={s}>
              {t(`status.${s}`)}
            </option>
          ))}
        </select>

        <input
          type="number"
          className={`${inputCls} w-24`}
          placeholder={t("minScore")}
          value={filters.minScore}
          onChange={(e) => setFilter("minScore", e.target.value)}
        />

        <div className="flex gap-0">
          <input
            className={`${inputCls} rounded-r-none border-r-0 w-48`}
            placeholder={t("searchPh")}
            value={filters.search}
            onChange={(e) => setFilter("search", e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchPosts(filters)}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchPosts(filters)}
            className="rounded-l-none h-9 px-3 border-slate-200"
          >
            <Search className="h-4 w-4" />
          </Button>
        </div>

        <span className="self-center text-sm text-slate-500 ml-1">
          {loading ? t("loadingCount") : t("totalCount", { count: formatNumber(total) })}
        </span>
      </div>

      {loading && posts.length === 0 ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      ) : posts.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 py-16 text-center text-slate-400">
          <p className="text-sm">{t("empty")}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {posts.map((post) => {
            const cls = STATUS_STYLES[post.analysis_status] ?? "bg-slate-100 text-slate-600";
            const label = postStatusLabel(t, post.analysis_status);
            return (
              <Card key={post.id} className="hover:shadow-sm transition-shadow">
                <CardContent className="p-3">
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0 space-y-1">
                      <p className="text-sm font-medium text-slate-800 leading-snug line-clamp-2">{post.title}</p>
                      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-500">
                        <span className="font-medium text-slate-600">r/{post.subreddit_name}</span>
                        <span>▲ {formatNumber(post.score)}</span>
                        <span className="flex items-center gap-0.5">
                          <MessageSquare className="h-3 w-3" />
                          {post.num_comments}
                        </span>
                        <span>{post.comments_fetched ? t("commentsFetched") : t("commentsNotFetched")}</span>
                        <span>{format.relativeTime(new Date(post.collected_at), now)}</span>
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-1.5">
                      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
                        {label}
                      </span>

                      {(post.analysis_status === "pending" || post.analysis_status === "failed") && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleAnalyze(post.id)}
                          className="h-7 px-2 text-xs gap-1"
                        >
                          <Zap className="h-3 w-3 text-amber-500" />
                          {t("analyze")}
                        </Button>
                      )}

                      {!post.comments_fetched && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleFetchComments(post.id)}
                          className="h-7 px-2 text-xs gap-1"
                          title={t("triggerComments")}
                        >
                          <MessageSquare className="h-3 w-3 text-indigo-400" />
                        </Button>
                      )}

                      {post.url && (
                        <a href={post.url} target="_blank" rel="noopener noreferrer">
                          <Button size="sm" variant="ghost" className="h-7 px-2" title={t("openPost")}>
                            <ExternalLink className="h-3 w-3 text-slate-400" />
                          </Button>
                        </a>
                      )}
                    </div>
                  </div>

                  <CommentPanel post={post} />
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-1">
          <Button
            variant="outline"
            size="sm"
            disabled={filters.page <= 1}
            onClick={() => setFilter("page", filters.page - 1)}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            {t("prev")}
          </Button>
          <span className="text-sm text-slate-500">
            {t("page", { page: filters.page, total: totalPages })}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={filters.page >= totalPages}
            onClick={() => setFilter("page", filters.page + 1)}
            className="gap-1"
          >
            {t("next")}
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
