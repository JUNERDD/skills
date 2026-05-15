import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  defaultLocale: "en",
  localeDetection: false,
  locales: ["en", "zh-CN"],
  localePrefix: "as-needed",
});

export type Locale = (typeof routing.locales)[number];
