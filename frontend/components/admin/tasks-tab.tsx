"use client";

import { useState, useEffect, useRef } from "react";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { type CollectTask, dataApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatNumber } from "@/lib/utils";
import {
  Play,
  Trash2,
  Plus,
  Globe,
  Pin,
  Clock,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Power,
  PowerOff,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  pending: { color: "bg-yellow-100 text-yellow-800", icon: <Clock className="h-3 w-3" /> },
  running: { color: "bg-blue-100 text-blue-800", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
  completed: { color: "bg-green-100 text-green-800", icon: <CheckCircle2 className="h-3 w-3" /> },
  failed: { color: "bg-red-100 text-red-800", icon: <AlertCircle className="h-3 w-3" /> },
};

const SORT_OPTIONS = ["hot", "new", "top", "rising"];
const TIME_OPTIONS = ["", "hour", "day", "week", "month", "year", "all"];

function FormRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
      {children}
    </div>
  );
}

function inputCls() {
  return "h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-300";
}

function selectCls(disabled = false) {
  return `${inputCls()} ${disabled ? "opacity-40 cursor-not-allowed" : ""}`;
}

interface NewTaskForm {
  taskType: "single" | "global";
  subreddit_name: string;
  sort_by: string;
  time_filter: string;
  post_limit: number;
  fetch_comments: boolean;
  comment_min_score: string;
  comment_min_count: string;
  max_comments_per_post: string;
  cron_expression: string;
}

const defaultForm: NewTaskForm = {
  taskType: "single",
  subreddit_name: "",
  sort_by: "hot",
  time_filter: "",
  post_limit: 25,
  fetch_comments: true,
  comment_min_score: "",
  comment_min_count: "",
  max_comments_per_post: "",
  cron_expression: "",
};

interface CreateFormProps {
  onCreated: (task: CollectTask) => void;
  onToast: (msg: string, type?: "success" | "error") => void;
}

function TaskCreateForm({ onCreated, onToast }: CreateFormProps) {
  const t = useTranslations("admin.tasks");
  const tc = useTranslations("admin.channels");
  const ta = useTranslations("admin");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<NewTaskForm>(defaultForm);
  const [creating, setCreating] = useState(false);

  const set = <K extends keyof NewTaskForm>(key: K, val: NewTaskForm[K]) =>
    setForm((f) => ({ ...f, [key]: val }));

  const handleCreate = async () => {
    if (form.taskType === "single" && !form.subreddit_name.trim()) {
      onToast(ta("toast.fillSubreddit"), "error");
      return;
    }
    setCreating(true);
    try {
      const payload: Partial<CollectTask> = {
        subreddit_name: form.taskType === "global" ? null : form.subreddit_name.trim().replace(/^r\//, ""),
        sort_by: form.sort_by,
        time_filter: form.sort_by === "top" && form.time_filter ? form.time_filter : null,
        post_limit: form.post_limit,
        fetch_comments: form.fetch_comments,
        comment_min_score: form.comment_min_score ? parseInt(form.comment_min_score, 10) : null,
        comment_min_count: form.comment_min_count ? parseInt(form.comment_min_count, 10) : null,
        max_comments_per_post: form.max_comments_per_post ? parseInt(form.max_comments_per_post, 10) : null,
        cron_expression: form.cron_expression.trim() || undefined,
        is_active: true,
      };
      const created = await dataApi.createTask(payload);
      onCreated(created);
      onToast(ta("toast.taskCreated"));
      setForm(defaultForm);
      setOpen(false);
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <button
          type="button"
          className="flex w-full items-center justify-between text-sm font-semibold text-slate-700"
          onClick={() => setOpen((o) => !o)}
        >
          <span className="flex items-center gap-1.5">
            <Plus className="h-4 w-4 text-indigo-500" />
            {t("createTitle")}
          </span>
          {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
        </button>
      </CardHeader>

      {open && (
        <CardContent className="space-y-4 pt-0">
          <div className="flex gap-4">
            {(["single", "global"] as const).map((type) => (
              <label key={type} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="taskType"
                  value={type}
                  checked={form.taskType === type}
                  onChange={() => set("taskType", type)}
                  className="accent-indigo-500"
                />
                <span className="text-sm font-medium text-slate-700">
                  {type === "single" ? t("typeSingle") : t("typeGlobal")}
                </span>
              </label>
            ))}
          </div>

          {form.taskType === "single" && (
            <FormRow label={t("subredditLabel")}>
              <input
                className={inputCls()}
                placeholder={t("subredditPh")}
                value={form.subreddit_name}
                onChange={(e) => set("subreddit_name", e.target.value)}
              />
            </FormRow>
          )}

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <FormRow label={t("sort")}>
              <select className={inputCls()} value={form.sort_by} onChange={(e) => set("sort_by", e.target.value)}>
                {SORT_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </FormRow>
            <FormRow label={form.sort_by !== "top" ? t("timeRangeTop") : t("timeRange")}>
              <select
                className={selectCls(form.sort_by !== "top")}
                value={form.time_filter}
                onChange={(e) => set("time_filter", e.target.value)}
                disabled={form.sort_by !== "top"}
              >
                {TIME_OPTIONS.map((x) => (
                  <option key={x || "any"} value={x}>
                    {x === "" ? t("timeAny") : x}
                  </option>
                ))}
              </select>
            </FormRow>
            <FormRow label={t("postLimit")}>
              <input
                type="number"
                min={1}
                max={100}
                className={inputCls()}
                value={form.post_limit}
                onChange={(e) =>
                  set("post_limit", Math.min(100, Math.max(1, parseInt(e.target.value, 10) || 25)))
                }
              />
            </FormRow>
            <FormRow label={t("fetchComments")}>
              <div className="flex h-9 items-center">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.fetch_comments}
                    onChange={(e) => set("fetch_comments", e.target.checked)}
                    className="rounded border-slate-300 accent-indigo-500"
                  />
                  <span className="text-sm text-slate-700">{t("enabled")}</span>
                </label>
              </div>
            </FormRow>
          </div>

          <div className="rounded-lg bg-slate-50 p-3 space-y-2">
            <p className="text-xs font-semibold text-slate-500 uppercase">{t("commentOverrides")}</p>
            <div className="grid grid-cols-3 gap-3">
              {(
                [
                  { key: "comment_min_score" as const, label: tc("minPostScore") },
                  { key: "comment_min_count" as const, label: tc("minCommentCount") },
                  { key: "max_comments_per_post" as const, label: tc("maxPerPost") },
                ] as const
              ).map(({ key, label }) => (
                <FormRow key={key} label={label}>
                  <input
                    type="number"
                    className={inputCls()}
                    placeholder={t("inherit")}
                    value={form[key]}
                    onChange={(e) => set(key, e.target.value)}
                  />
                </FormRow>
              ))}
            </div>
          </div>

          <FormRow label={t("cron")}>
            <input
              className={inputCls()}
              placeholder={t("cronPh")}
              value={form.cron_expression}
              onChange={(e) => set("cron_expression", e.target.value)}
            />
          </FormRow>

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setForm(defaultForm);
                setOpen(false);
              }}
            >
              {t("cancel")}
            </Button>
            <Button size="sm" onClick={handleCreate} disabled={creating}>
              {creating ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> {t("creating")}
                </>
              ) : (
                t("create")
              )}
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

interface TaskCardProps {
  task: CollectTask;
  onRun: (id: number) => void;
  onToggle: (id: number) => void;
  onDelete: (id: number) => void;
  running: boolean;
}

function TaskCard({ task, onRun, onToggle, onDelete, running }: TaskCardProps) {
  const t = useTranslations("admin.tasks");
  const format = useFormatter();
  const now = useNow();
  const cfg = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.pending;
  const isGlobal = task.subreddit_name === null || task.subreddit_name === undefined;

  const hasCommentOverride =
    (task.comment_min_score !== null && task.comment_min_score !== undefined) ||
    (task.comment_min_count !== null && task.comment_min_count !== undefined) ||
    (task.max_comments_per_post !== null && task.max_comments_per_post !== undefined);

  return (
    <Card className={`transition-shadow hover:shadow-sm ${!task.is_active ? "opacity-60" : ""}`}>
      <CardContent className="p-4 space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap min-w-0">
            {isGlobal ? (
              <Globe className="h-4 w-4 shrink-0 text-indigo-500" />
            ) : (
              <Pin className="h-4 w-4 shrink-0 text-slate-400" />
            )}
            <span className="font-semibold text-slate-900 truncate">
              {isGlobal ? t("globalTask") : `r/${task.subreddit_name}`}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.color}`}
            >
              {cfg.icon}
              {task.status}
            </span>
            {!task.is_active && (
              <Badge variant="outline" className="text-xs">
                {t("paused")}
              </Badge>
            )}
          </div>

          <div className="flex shrink-0 gap-1.5">
            <Button
              size="sm"
              variant="outline"
              onClick={() => onRun(task.id)}
              disabled={running || task.status === "running"}
              className="h-8 px-2.5 text-xs gap-1.5"
            >
              {task.status === "running" ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Play className="h-3 w-3" />
              )}
              {t("run")}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onToggle(task.id)}
              className="h-8 px-2.5 text-xs gap-1.5"
              title={task.is_active ? t("toggleScheduleOn") : t("toggleScheduleOff")}
            >
              {task.is_active ? (
                <PowerOff className="h-3 w-3 text-slate-500" />
              ) : (
                <Power className="h-3 w-3 text-emerald-500" />
              )}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onDelete(task.id)}
              disabled={task.status === "running"}
              className="h-8 px-2.5 text-xs text-red-500 hover:bg-red-50"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
          <span>
            sort={task.sort_by}
            {task.sort_by === "top" && task.time_filter ? ` · time=${task.time_filter}` : ""}
          </span>
          <span>limit={task.post_limit}</span>
          <span>
            comments={task.fetch_comments ? t("fetchOn") : t("fetchOff")}
          </span>
          {hasCommentOverride && (
            <span className="text-indigo-500">
              {t("overridePrefix")}
              {[
                task.comment_min_score != null && `min_score=${task.comment_min_score}`,
                task.comment_min_count != null && `min_count=${task.comment_min_count}`,
                task.max_comments_per_post != null && `max/post=${task.max_comments_per_post}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
          )}
          {task.cron_expression ? (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3 text-amber-500" />
              {task.cron_expression}
            </span>
          ) : (
            <span className="text-slate-400">{t("manualOnly")}</span>
          )}
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
          <span>
            {t("totalPosts")}: {formatNumber(task.posts_collected)}
          </span>
          <span>
            {t("totalComments")}: {formatNumber(task.comments_collected)}
          </span>
          {task.last_run_at && (
            <span>
              {t("lastRun")}: {format.relativeTime(new Date(task.last_run_at), now)}
            </span>
          )}
        </div>

        {task.last_error && (
          <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700 flex items-start gap-2">
            <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <span className="break-all">{task.last_error}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface Props {
  tasks: CollectTask[];
  onTasksChange: (tasks: CollectTask[]) => void;
  onToast: (msg: string, type?: "success" | "error") => void;
}

export function TasksTab({ tasks, onTasksChange, onToast }: Props) {
  const t = useTranslations("admin.tasks");
  const ta = useTranslations("admin");
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const anyRunning = tasks.some((x) => x.status === "running");
    if (anyRunning && !pollingRef.current) {
      pollingRef.current = setInterval(async () => {
        try {
          const updated = await dataApi.getTasks();
          onTasksChange(updated);
          if (!updated.some((x) => x.status === "running")) {
            clearInterval(pollingRef.current!);
            pollingRef.current = null;
          }
        } catch {
          /* ignore */
        }
      }, 3000);
    } else if (!anyRunning && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [tasks, onTasksChange]);

  const handleRun = async (id: number) => {
    try {
      await dataApi.runTask(id);
      onToast(ta("toast.taskRun"));
      const updated = await dataApi.getTasks();
      onTasksChange(updated);
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    }
  };

  const handleToggle = async (id: number) => {
    try {
      const updated = await dataApi.toggleTask(id);
      onTasksChange(tasks.map((x) => (x.id === updated.id ? updated : x)));
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm(t("confirmDelete"))) return;
    try {
      await dataApi.deleteTask(id);
      onTasksChange(tasks.filter((x) => x.id !== id));
      onToast(ta("toast.taskDeleted"));
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    }
  };

  const anyRunning = tasks.some((x) => x.status === "running");

  return (
    <div className="space-y-4">
      <TaskCreateForm onCreated={(task) => onTasksChange([task, ...tasks])} onToast={onToast} />

      {tasks.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 py-16 text-center text-slate-400">
          <p className="text-sm">{t("empty")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onRun={handleRun}
              onToggle={handleToggle}
              onDelete={handleDelete}
              running={anyRunning}
            />
          ))}
        </div>
      )}
    </div>
  );
}
