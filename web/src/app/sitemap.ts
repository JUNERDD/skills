import type { MetadataRoute } from "next";
import { listSkillSlugs } from "@/lib/content/provider";
import { getSiteOrigin } from "@/lib/site-url";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = getSiteOrigin();
  const lastModified = new Date();
  const slugs = await listSkillSlugs();

  return [
    {
      url: origin,
      lastModified,
      changeFrequency: "weekly",
      priority: 1,
    },
    ...slugs.map((slug) => ({
      url: `${origin}/skills/${slug}`,
      lastModified,
      changeFrequency: "monthly" as const,
      priority: 0.82,
    })),
  ];
}
