import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["en", "es", "pt-BR", "fr", "de", "ja", "ko", "ar", "zh-Hans", "zh-Hant"],
  defaultLocale: "en",
  localePrefix: "as-needed",
});

export type AppLocale = (typeof routing.locales)[number];
