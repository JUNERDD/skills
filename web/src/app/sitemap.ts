import type { MetadataRoute } from "next";
import { SKILLS } from "@/lib/skills-data";
import { getSiteOrigin } from "@/lib/site-url";

export default function sitemap(): MetadataRoute.Sitemap {
  const origin = getSiteOrigin();
  const lastModified = new Date();

  return [
    {
      url: origin,
      lastModified,
      changeFrequency: "weekly",
      priority: 1,
    },
    ...SKILLS.map((skill) => ({
      url: `${origin}/skills/${skill.slug}`,
      lastModified,
      changeFrequency: "monthly" as const,
      priority: 0.82,
    })),
  ];
}
