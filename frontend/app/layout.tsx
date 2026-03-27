import type { ReactNode } from "react";

/** Root passthrough; `<html>` / `<body>` live in `app/[locale]/layout.tsx` (next-intl). */
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
