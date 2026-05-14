export type SkillEntryPoint = {
  label: string;
  path: string;
  description: string;
};

export type SkillDetail = {
  slug: string;
  title: string;
  category: string;
  blurb: string;
  lead: string;
  overview: string;
  bestFor: string[];
  workflow: string[];
  outputs: string[];
  guardrails: string[];
  entryPoints: SkillEntryPoint[];
};

export type SkillListItem = Pick<
  SkillDetail,
  "slug" | "title" | "category" | "blurb"
>;

export type SkillNeighbor = Pick<SkillDetail, "slug" | "title" | "blurb">;

export type SkillNeighbors = {
  previous?: SkillNeighbor;
  next?: SkillNeighbor;
};
