"use client";

import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { BarChart3, Lightbulb, Settings, TrendingUp } from "lucide-react";
import { LanguageSwitcher } from "@/components/shared/language-switcher";

export function Nav() {
  const pathname = usePathname();
  const t = useTranslations("nav");

  const navItems = [
    { href: "/", label: t("home"), icon: TrendingUp },
    { href: "/opportunities", label: t("opportunities"), icon: Lightbulb },
    { href: "/admin", label: t("admin"), icon: Settings, admin: true },
  ];

  return (
    <header className="sticky top-0 z-50 border-b bg-white/80 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2 font-bold text-xl shrink-0 min-w-0">
            <BarChart3 className="h-6 w-6 text-blue-600 shrink-0" />
            <span className="truncate">{t("brand")}</span>
          </Link>
          <div className="flex items-center gap-2 sm:gap-4 min-w-0">
            <nav className="flex items-center gap-1 overflow-x-auto">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors whitespace-nowrap",
                    pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              ))}
            </nav>
            <LanguageSwitcher />
          </div>
        </div>
      </div>
    </header>
  );
}
