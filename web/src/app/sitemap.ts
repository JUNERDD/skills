import type { MetadataRoute } from "next";
import { listSkillSlugs } from "@/lib/content/provider";
import {
  getAbsoluteLanguageAlternates,
  localizePath,
  locales,
} from "@/lib/i18n/config";
import { getSiteOrigin } from "@/lib/site-url";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = getSiteOrigin();
  const lastModified = new Date();
  const slugs = await listSkillSlugs();
  const skillPaths = slugs.map((slug) => `/skills/${slug}`);
  const paths = ["/", ...skillPaths];

  return paths.flatMap((pathname) =>
    locales.map((locale) => ({
      url: `${origin}${localizePath(pathname, locale)}`,
      lastModified,
      changeFrequency: pathname === "/" ? ("weekly" as const) : ("monthly" as const),
      priority: pathname === "/" ? 1 : 0.82,
      alternates: {
        languages: getAbsoluteLanguageAlternates(origin, pathname),
      },
    })),
  );
}
