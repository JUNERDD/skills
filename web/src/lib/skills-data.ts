export const COLLECTION_VERSION = "0.1.1";

export const REPO_URL = "https://github.com/JUNERDD/skills";
export const INSTALL_DOC_RAW =
  "https://raw.githubusercontent.com/JUNERDD/skills/refs/heads/main/docs/INSTALL.md";

export type SkillItem = {
  slug: string;
  title: string;
  blurb: string;
};

/** 与根 README「Skills At A Glance」对齐 */
export const SKILLS: SkillItem[] = [
  {
    slug: "comment-strategist",
    title: "comment-strategist",
    blurb: "Add high-value code comments without comment noise.",
  },
  {
    slug: "git-commit",
    title: "git-commit",
    blurb: "Draft a Conventional Commit message from the staged diff.",
  },
  {
    slug: "split-commits",
    title: "split-commits",
    blurb: "Split a mixed working tree into focused local commits.",
  },
  {
    slug: "debug",
    title: "debug",
    blurb: "Debug runtime issues with an evidence-first logging workflow.",
  },
  {
    slug: "hack-review",
    title: "hack-review",
    blurb: "Review whether an implementation relies on brittle hack-like shortcuts.",
  },
  {
    slug: "receiving-hack-review",
    title: "receiving-hack-review",
    blurb: "Consume a hack-review report and verify each finding before changing code.",
  },
  {
    slug: "regression-review",
    title: "regression-review",
    blurb: "Review code changes for user-visible behavioral regressions.",
  },
  {
    slug: "receiving-regression-review",
    title: "receiving-regression-review",
    blurb: "Consume a regression-review report and verify each finding before changing code.",
  },
];
