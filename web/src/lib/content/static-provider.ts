import { SKILLS } from "@/lib/skills-data";
import { defaultLocale, type Locale } from "@/lib/i18n/config";
import { getSkillTranslation } from "@/lib/i18n/skill-translations";
import type {
  SkillDetail,
  SkillListItem,
  SkillNeighbor,
  SkillNeighbors,
} from "./types";

function localizeSkill(skill: SkillDetail, locale: Locale): SkillDetail {
  const translation = getSkillTranslation(skill.slug, locale);

  if (!translation) return skill;

  return {
    ...skill,
    ...translation,
    entryPoints: translation.entryPoints
      ? skill.entryPoints.map((entry, index) => ({
          ...entry,
          ...translation.entryPoints?.[index],
        }))
      : skill.entryPoints,
  };
}

function toSkillListItem(skill: SkillDetail): SkillListItem {
  return {
    slug: skill.slug,
    title: skill.title,
    category: skill.category,
    blurb: skill.blurb,
  };
}

function toSkillNeighbor(skill: SkillDetail): SkillNeighbor {
  return {
    slug: skill.slug,
    title: skill.title,
    blurb: skill.blurb,
  };
}

export async function listSkills(
  locale: Locale = defaultLocale
): Promise<SkillDetail[]> {
  return SKILLS.map((skill) => localizeSkill(skill, locale));
}

export async function listSkillListItems(
  locale: Locale = defaultLocale
): Promise<SkillListItem[]> {
  return (await listSkills(locale)).map(toSkillListItem);
}

export async function listSkillSlugs(): Promise<string[]> {
  return SKILLS.map((skill) => skill.slug);
}

export async function getSkillBySlug(
  slug: string,
  locale: Locale = defaultLocale
): Promise<SkillDetail | undefined> {
  const skill = SKILLS.find((candidate) => candidate.slug === slug);
  return skill ? localizeSkill(skill, locale) : undefined;
}

export async function getSkillNeighbors(
  slug: string,
  locale: Locale = defaultLocale
): Promise<SkillNeighbors> {
  const index = SKILLS.findIndex((skill) => skill.slug === slug);
  const skills = await listSkills(locale);

  return {
    previous: index > 0 ? toSkillNeighbor(skills[index - 1]) : undefined,
    next:
      index >= 0 && index < SKILLS.length - 1
        ? toSkillNeighbor(skills[index + 1])
        : undefined,
  };
}
