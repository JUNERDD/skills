import { routing, type Locale } from "@/i18n/routing";

export type { Locale };

export const locales = routing.locales;

export const defaultLocale = routing.defaultLocale;

export const localeLabels: Record<Locale, Record<Locale, string>> = {
  en: {
    en: "English",
    "zh-CN": "Chinese",
  },
  "zh-CN": {
    en: "英文",
    "zh-CN": "中文",
  },
};

export const localeShortLabels: Record<Locale, Record<Locale, string>> = {
  en: {
    en: "EN",
    "zh-CN": "ZH",
  },
  "zh-CN": {
    en: "EN",
    "zh-CN": "中",
  },
};

export const openGraphLocales: Record<Locale, string> = {
  en: "en_US",
  "zh-CN": "zh_CN",
};

export function isLocale(value: string | undefined): value is Locale {
  return routing.locales.includes(value as Locale);
}

export function getPathLocale(pathname: string): Locale | undefined {
  const segment = pathname.split("/")[1];
  return isLocale(segment) ? segment : undefined;
}

function withLeadingSlash(pathname: string) {
  return pathname.startsWith("/") ? pathname : `/${pathname}`;
}

export function stripLocaleFromPath(pathname: string) {
  const normalized = withLeadingSlash(pathname);
  const segments = normalized.split("/");

  if (!isLocale(segments[1])) {
    return normalized === "" ? "/" : normalized;
  }

  const stripped = `/${segments.slice(2).join("/")}`;
  return stripped === "/" || stripped === "" ? "/" : stripped.replace(/\/+$/, "");
}

export function localizePath(pathname: string, locale: Locale) {
  const stripped = stripLocaleFromPath(pathname);
  if (locale === defaultLocale) {
    return stripped;
  }

  return stripped === "/" ? `/${locale}` : `/${locale}${stripped}`;
}

export function getLanguageAlternates(pathname: string) {
  return {
    ...Object.fromEntries(
      locales.map((locale) => [locale, localizePath(pathname, locale)]),
    ),
    "x-default": stripLocaleFromPath(pathname),
  };
}

export function getAbsoluteLanguageAlternates(origin: string, pathname: string) {
  return Object.fromEntries(
    Object.entries(getLanguageAlternates(pathname)).map(([locale, path]) => [
      locale,
      `${origin}${path === "/" ? "" : path}`,
    ]),
  );
}
