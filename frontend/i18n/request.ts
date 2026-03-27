import deepmerge from "deepmerge";
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";
import en from "../messages/en.json";

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;
  if (!locale || !(routing.locales as readonly string[]).includes(locale)) {
    locale = routing.defaultLocale;
  }

  let messages: typeof en = en;
  if (locale !== "en") {
    try {
      const mod = await import(`../messages/${locale}.json`);
      messages = deepmerge(en, mod.default) as typeof en;
    } catch {
      messages = en;
    }
  }

  return { locale, messages };
});
