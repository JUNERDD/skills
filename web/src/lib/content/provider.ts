import * as staticProvider from "./static-provider";

export type {
  SkillDetail,
  SkillEntryPoint,
  SkillListItem,
  SkillNeighbor,
  SkillNeighbors,
} from "./types";
export {
  AGENT_INSTALL_INSTRUCTION,
  COLLECTION_VERSION,
  INSTALL_DOC_RAW,
  REPO_URL,
  getSkillInstallCommand,
  getSkillSourceUrl,
} from "./urls";

export const contentProvider = "static";

export const listSkills = staticProvider.listSkills;
export const listSkillListItems = staticProvider.listSkillListItems;
export const listSkillSlugs = staticProvider.listSkillSlugs;
export const getSkillBySlug = staticProvider.getSkillBySlug;
export const getSkillNeighbors = staticProvider.getSkillNeighbors;
