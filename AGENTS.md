# Agent Instructions

These instructions apply to the whole repository. More specific `AGENTS.md`
files, such as `web/AGENTS.md`, also apply within their subtrees.

## Repository Model

- This repository is a collection of installable project skills.
- Installable skills live in `skills/<skill-name>/`.
- Each skill owns its `SKILL.md` plus any optional `agents/`, `references/`,
  `scripts/`, or `assets/` directories.
- The companion website lives in `web/` and presents the public catalog,
  install guidance, and skill detail pages.

## Skill, README, And Web Sync

When changing any project skill under `skills/<skill-name>/`, evaluate before
finishing whether the root `README.md` or `web/` needs a matching update.

Update `README.md` or `web/` when a skill change affects public catalog data,
repository documentation, or website copy, including:

- adding, renaming, or removing a skill
- changing a skill title, summary, category, positioning, or recommended use
- changing install commands, entry points, file paths, examples, or referenced
  assets
- changing behavior that the README or website describes

At minimum, check the root `README.md` and `web/src/lib/skills-data.ts` for
skill catalog changes, then inspect the relevant page or component if the
changed skill is surfaced elsewhere. If no README or website change is needed,
mention that both sync checks were performed in the final response.

## Editing Notes

- Keep changes scoped to the requested skill, repository docs, or web surface.
- Do not edit generated dependency or build output directories such as
  `web/node_modules/` or `web/.next/`.
