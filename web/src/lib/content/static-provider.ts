import { SKILLS } from "@/lib/skills-data";
import type {
  SkillDetail,
  SkillListItem,
  SkillNeighbor,
  SkillNeighbors,
} from "./types";

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

export async function listSkills(): Promise<SkillDetail[]> {
  return SKILLS;
}

export async function listSkillListItems(): Promise<SkillListItem[]> {
  return SKILLS.map(toSkillListItem);
}

export async function listSkillSlugs(): Promise<string[]> {
  return SKILLS.map((skill) => skill.slug);
}

export async function getSkillBySlug(
  slug: string
): Promise<SkillDetail | undefined> {
  return SKILLS.find((skill) => skill.slug === slug);
}

export async function getSkillNeighbors(slug: string): Promise<SkillNeighbors> {
  const index = SKILLS.findIndex((skill) => skill.slug === slug);

  return {
    previous: index > 0 ? toSkillNeighbor(SKILLS[index - 1]) : undefined,
    next:
      index >= 0 && index < SKILLS.length - 1
        ? toSkillNeighbor(SKILLS[index + 1])
        : undefined,
  };
}
