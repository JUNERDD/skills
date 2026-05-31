// Managed by scripts/sync-version.mjs from the repository-level VERSION file.
export const COLLECTION_VERSION = "0.2.0";

export const REPO_URL = "https://github.com/JUNERDD/skills";
export const INSTALL_DOC_RAW =
  "https://raw.githubusercontent.com/JUNERDD/skills/refs/heads/main/docs/INSTALL.md";
export const AGENT_INSTALL_INSTRUCTION = `Fetch and follow instructions from ${INSTALL_DOC_RAW}`;

export function getSkillSourceUrl(slug: string) {
  return `${REPO_URL}/tree/main/skills/${slug}`;
}

export function getSkillInstallCommand(slug: string) {
  return `npx skills@latest add JUNERDD/skills --skill ${slug}`;
}
