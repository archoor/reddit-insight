"use client";

import { useState } from "react";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { type Subreddit, dataApi } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import { Plus, Settings, Trash2, MessageSquare, FileText, BarChart3 } from "lucide-react";

const SORT_OPTIONS = ["hot", "new", "top", "rising"];
const TIME_OPTIONS = ["", "hour", "day", "week", "month", "year", "all"];

function SortSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <select
      className="h-9 rounded-md border border-slate-200 bg-white px-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-300"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {SORT_OPTIONS.map((s) => (
        <option key={s} value={s}>
          {s}
        </option>
      ))}
    </select>
  );
}

function TimeSelect({
  value,
  onChange,
  disabled,
  timeAnyLabel,
  disabledTitle,
}: {
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
  timeAnyLabel: string;
  disabledTitle: string;
}) {
  return (
    <select
      className="h-9 rounded-md border border-slate-200 bg-white px-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:opacity-40 disabled:cursor-not-allowed"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      title={disabled ? disabledTitle : undefined}
    >
      {TIME_OPTIONS.map((x) => (
        <option key={x || "any"} value={x}>
          {x === "" ? timeAnyLabel : x}
        </option>
      ))}
    </select>
  );
}

function NumInput({
  label,
  value,
  onChange,
  min = 1,
  max = 10000,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
      <input
        type="number"
        min={min}
        max={max}
        className="h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-300"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || min)}
      />
    </div>
  );
}

interface EditModalProps {
  sub: Subreddit;
  onClose: () => void;
  onSaved: (updated: Subreddit) => void;
  onDeleted: (id: number) => void;
  onToast: (msg: string, type?: "success" | "error") => void;
}

function EditSubredditModal({ sub, onClose, onSaved, onDeleted, onToast }: EditModalProps) {
  const t = useTranslations("admin.channels");
  const ta = useTranslations("admin");
  const [form, setForm] = useState({
    display_name: sub.display_name,
    sort_by: sub.sort_by,
    time_filter: sub.time_filter ?? "",
    post_limit: sub.post_limit,
    fetch_comments: sub.fetch_comments,
    comment_min_score: sub.comment_min_score,
    comment_min_count: sub.comment_min_count,
    comment_max_per_post: sub.comment_max_per_post,
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const set = <K extends keyof typeof form>(key: K, val: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [key]: val }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await dataApi.updateSubreddit(sub.id, {
        ...form,
        time_filter: form.sort_by === "top" && form.time_filter ? form.time_filter : null,
      });
      onSaved(updated);
      onToast(ta("toast.channelSaved"));
      onClose();
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(t("confirmDelete", { name: sub.name }))) return;
    setDeleting(true);
    try {
      await dataApi.deleteSubreddit(sub.id);
      onDeleted(sub.id);
      onToast(ta("toast.channelDeleted"));
      onClose();
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Modal open title={t("modalTitle", { name: sub.name })} onClose={onClose}>
      <div className="space-y-5">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">{t("displayName")}</label>
          <input
            className="h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            value={form.display_name}
            onChange={(e) => set("display_name", e.target.value)}
          />
        </div>

        <div className="rounded-lg bg-slate-50 p-4 space-y-3">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <FileText className="h-3.5 w-3.5" /> {t("postCollection")}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">{t("sortLabel")}</label>
              <SortSelect value={form.sort_by} onChange={(v) => set("sort_by", v)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {t("timeLabel")}{" "}
                {form.sort_by !== "top" && <span className="text-slate-400">{t("timeHintTop")}</span>}
              </label>
              <TimeSelect
                value={form.time_filter}
                onChange={(v) => set("time_filter", v)}
                disabled={form.sort_by !== "top"}
                timeAnyLabel={t("timeAny")}
                disabledTitle={t("timeDisabledHint")}
              />
            </div>
          </div>
          <NumInput
            label={t("postsPerRun")}
            value={form.post_limit}
            onChange={(v) => set("post_limit", Math.min(100, Math.max(1, v)))}
            min={1}
            max={100}
          />
        </div>

        <div className="rounded-lg bg-slate-50 p-4 space-y-3">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <MessageSquare className="h-3.5 w-3.5" /> {t("commentCollection")}
          </p>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={form.fetch_comments}
              onChange={(e) => set("fetch_comments", e.target.checked)}
              className="rounded border-slate-300"
            />
            <span className="text-slate-700 font-medium">{t("fetchComments")}</span>
          </label>
          {form.fetch_comments && (
            <div className="grid grid-cols-3 gap-3">
              <NumInput
                label={t("minPostScore")}
                value={form.comment_min_score}
                onChange={(v) => set("comment_min_score", v)}
                min={0}
              />
              <NumInput
                label={t("minCommentCount")}
                value={form.comment_min_count}
                onChange={(v) => set("comment_min_count", v)}
                min={0}
              />
              <NumInput
                label={t("maxPerPost")}
                value={form.comment_max_per_post}
                onChange={(v) => set("comment_max_per_post", v)}
                min={1}
                max={1000}
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-1">
          <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleting}>
            <Trash2 className="h-3.5 w-3.5" />
            {deleting ? t("deleting") : t("deleteChannel")}
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onClose}>
              {t("cancel")}
            </Button>
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving ? t("saving") : t("save")}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

interface Props {
  subreddits: Subreddit[];
  onRefresh: () => void;
  onToast: (msg: string, type?: "success" | "error") => void;
}

export function ChannelsTab({ subreddits, onRefresh, onToast }: Props) {
  const t = useTranslations("admin.channels");
  const ta = useTranslations("admin");
  const format = useFormatter();
  const now = useNow();
  const [editingSub, setEditingSub] = useState<Subreddit | null>(null);
  const [localSubs, setLocalSubs] = useState<Subreddit[]>(subreddits);
  const [newName, setNewName] = useState("");
  const [adding, setAdding] = useState(false);

  if (subreddits !== localSubs && subreddits.length !== localSubs.length) {
    setLocalSubs(subreddits);
  }

  const handleAdd = async () => {
    const name = newName.trim().replace(/^r\//, "");
    if (!name) return;
    setAdding(true);
    try {
      const created = await dataApi.createSubreddit({ name, display_name: name });
      setLocalSubs((prev) => [...prev, created]);
      setNewName("");
      onToast(ta("toast.channelAdded", { name }));
      onRefresh();
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    } finally {
      setAdding(false);
    }
  };

  const handleToggle = async (sub: Subreddit) => {
    try {
      const updated = await dataApi.toggleSubreddit(sub.id);
      setLocalSubs((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    } catch (e) {
      onToast(`${(e as Error).message}`, "error");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          className="h-10 flex-1 max-w-xs rounded-md border border-slate-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          placeholder={t("placeholder")}
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
        />
        <Button onClick={handleAdd} disabled={adding || !newName.trim()}>
          <Plus className="h-4 w-4" />
          {adding ? t("adding") : t("add")}
        </Button>
      </div>

      {localSubs.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 py-16 text-center text-slate-400">
          <BarChart3 className="mx-auto mb-3 h-10 w-10 opacity-40" />
          <p className="text-sm">{t("empty")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {localSubs.map((sub) => (
            <Card
              key={sub.id}
              className={`transition-shadow hover:shadow-sm ${!sub.is_active ? "opacity-60" : ""}`}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-slate-900">r/{sub.name}</span>
                      {sub.display_name && sub.display_name !== sub.name && (
                        <span className="text-sm text-slate-500">({sub.display_name})</span>
                      )}
                      <Badge variant={sub.is_active ? "success" : "outline"}>
                        {sub.is_active ? t("active") : t("inactive")}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                      <span>
                        <span className="font-medium text-slate-600">{t("posts")}</span>
                        sort={sub.sort_by}
                        {sub.sort_by === "top" && sub.time_filter ? ` · time=${sub.time_filter}` : ""}
                        {" · "}limit={sub.post_limit}
                      </span>
                      <span>
                        <span className="font-medium text-slate-600">{t("comments")}</span>
                        {sub.fetch_comments
                          ? `min_score=${sub.comment_min_score} · min_count=${sub.comment_min_count} · max=${sub.comment_max_per_post}`
                          : t("commentsOff")}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400">
                      {t("created")} {format.dateTime(new Date(sub.created_at), { dateStyle: "medium" })}
                      {" · "}
                      {t("updated")} {format.relativeTime(new Date(sub.updated_at), now)}
                    </p>
                  </div>

                  <div className="flex shrink-0 gap-1.5">
                    <Button size="sm" variant="ghost" onClick={() => handleToggle(sub)} className="text-xs">
                      {sub.is_active ? t("disable") : t("enable")}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setEditingSub(sub)}>
                      <Settings className="h-3.5 w-3.5" />
                      {t("edit")}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {editingSub && (
        <EditSubredditModal
          sub={editingSub}
          onClose={() => setEditingSub(null)}
          onSaved={(updated) => {
            setLocalSubs((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
            setEditingSub(null);
          }}
          onDeleted={(id) => {
            setLocalSubs((prev) => prev.filter((s) => s.id !== id));
            setEditingSub(null);
            onRefresh();
          }}
          onToast={onToast}
        />
      )}
    </div>
  );
}
