import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import "../globals.css";
import { Nav } from "@/components/shared/nav";
import { routing } from "@/i18n/routing";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "meta" });
  const title = t("root.title");
  const description = t("root.description");
  return {
    metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"),
    title: { default: title, template: "%s | Reddit Insight" },
    description,
    keywords: ["reddit analysis", "business opportunities", "market research", "startup ideas"],
    openGraph: {
      type: "website",
      siteName: "Reddit Insight",
      title,
      description,
    },
    robots: { index: true, follow: true },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;
  if (!(routing.locales as readonly string[]).includes(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const messages = await getMessages();
  const t = await getTranslations({ locale, namespace: "footer" });
  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <html lang={locale} dir={dir} suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen bg-slate-50`}
      >
        <NextIntlClientProvider messages={messages}>
          <Nav />
          <main>{children}</main>
          <footer className="border-t bg-white py-8 mt-16">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center text-sm text-slate-500">
              <p>{t("tagline")}</p>
            </div>
          </footer>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
