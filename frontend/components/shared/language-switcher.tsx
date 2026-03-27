"use client";

import { useEffect, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { ChevronDown, Globe } from "lucide-react";
import { usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { cn } from "@/lib/utils";

/** Short label on the trigger; full native names stay in the menu. */
const LOCALE_SHORT: Record<string, string> = {
  en: "EN",
  es: "ES",
  "pt-BR": "PT",
  fr: "FR",
  de: "DE",
  ja: "JA",
  ko: "KO",
  ar: "AR",
  "zh-Hans": "简",
  "zh-Hant": "繁",
};

export function LanguageSwitcher() {
  const t = useTranslations("locale");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative shrink-0" ref={rootRef}>
      <button
        type="button"
        className={cn(
          "flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm text-slate-700",
          "border border-slate-200/90 bg-white shadow-sm",
          "hover:border-slate-300 hover:bg-slate-50/80",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/40"
        )}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={t("label")}
        onClick={() => setOpen((o) => !o)}
      >
        <Globe className="h-4 w-4 shrink-0 text-slate-500" strokeWidth={1.75} aria-hidden />
        <span className="font-medium tabular-nums tracking-tight text-slate-800">
          {LOCALE_SHORT[locale] ?? locale}
        </span>
        <ChevronDown
          className={cn("h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform", open && "rotate-180")}
          strokeWidth={2}
          aria-hidden
        />
      </button>

      {open && (
        <ul
          className="absolute right-0 top-[calc(100%+4px)] z-50 max-h-72 min-w-[11rem] overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-md"
          role="listbox"
          aria-label={t("label")}
        >
          {routing.locales.map((loc) => (
            <li key={loc} role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={loc === locale}
                className={cn(
                  "flex w-full items-center px-3 py-2 text-left text-sm transition-colors",
                  loc === locale
                    ? "bg-slate-100 font-medium text-slate-900"
                    : "text-slate-600 hover:bg-slate-50"
                )}
                onClick={() => {
                  setOpen(false);
                  router.replace(pathname, { locale: loc });
                }}
              >
                {t(loc)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
