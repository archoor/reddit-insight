import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AdminDashboard } from "@/components/admin/dashboard";

type PageProps = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "meta" });
  return {
    title: t("admin.title"),
    robots: { index: false, follow: false },
  };
}

export default function AdminPage() {
  return <AdminDashboard />;
}
