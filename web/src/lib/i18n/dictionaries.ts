import "server-only";
import type { Locale } from "@/i18n/routing";

export type SiteDictionary = {
  metadata: {
    description: string;
    keywords: string[];
    ogDescription: string;
    siteJsonLdDescription: string;
    srOnlyBrand: string;
    titleDefault: string;
    titleTemplate: string;
  };
  nav: {
    github: string;
    home: string;
    languageSwitcher: string;
  };
  hero: {
    copiedInstall: string;
    copyInstall: string;
    eyebrow: string;
    repository: string;
    tagline: string;
  };
  support: {
    afterCollectionVersion: string;
    afterInstallPath: string;
    afterRootVersion: string;
    beforeCollectionVersion: string;
    beforeInstallPath: string;
    heading: string;
  };
  skillsList: {
    description: string;
    openGuide: string;
    title: string;
  };
  finalCta: {
    copied: string;
    copy: string;
    description: string;
    figureLabel: string;
    footerMeta: string;
    heading: string;
    promptLabel: string;
  };
  copyButton: {
    errorDescription: string;
    errorTitle: string;
    failedLabel: string;
    successTitle: string;
  };
  toaster: {
    close: string;
  };
  skillDetail: {
    contents: string;
    copiedInstallCommand: string;
    copyInstallCommand: string;
    copyInstallCommandFailed: string;
    entryPoints: string;
    guardrails: string;
    install: string;
    installCommandCopied: string;
    metadataNotFoundTitle: string;
    metadataTitleSuffix: string;
    navBestFor: string;
    navEntryPoints: string;
    navGuardrails: string;
    navOutputs: string;
    navOverview: string;
    navWorkflow: string;
    next: string;
    outputs: string;
    overview: string;
    previous: string;
    relatedSkills: string;
    useCase: string;
    workflow: string;
  };
};

const dictionaries: Record<Locale, SiteDictionary> = {
  en: {
    metadata: {
      description:
        "Reusable AI agent skills published from a single repository - install independently or as a curated collection.",
      keywords: [
        "AI agents",
        "agent skills",
        "Cursor",
        "Claude",
        "reusable prompts",
        "developer tools",
        "JUNERDD",
      ],
      ogDescription: "Reusable AI agent skills published from a single repository.",
      siteJsonLdDescription:
        "Reusable AI agent skills published from a single repository - install independently or as a curated collection.",
      srOnlyBrand: "JUNERDD Skills - reusable AI agent skills",
      titleDefault: "JUNERDD Skills · Reusable agent skills",
      titleTemplate: "%s · JUNERDD Skills",
    },
    nav: {
      github: "GitHub",
      home: "JUNERDD home",
      languageSwitcher: "Switch language",
    },
    hero: {
      copiedInstall: "Copied prompt",
      copyInstall: "Copy install prompt",
      eyebrow: "Agent skill collection",
      repository: "View repository",
      tagline: "Reusable AI agent skills packaged as installable workflows.",
    },
    support: {
      afterCollectionVersion: " today) while tooling can pin their own runtime revisions when necessary.",
      afterInstallPath: ", each bundled with prompts and docs. Root ",
      afterRootVersion: " tracks the curated collection (",
      beforeCollectionVersion: "v",
      beforeInstallPath: "Installables live under ",
      heading: "What ships",
    },
    skillsList: {
      description:
        "Every local installable gets a field manual. Open a guide for the workflow, boundaries, outputs, and source entry points.",
      openGuide: "Open guide",
      title: "Skills at a glance",
    },
    finalCta: {
      copied: "Copied",
      copy: "Copy",
      description:
        "If you want an agent to install this repository for you without copying files, tell it:",
      figureLabel: "Agent installation instruction",
      footerMeta: "skills · collection",
      heading: "Wire it into your agents",
      promptLabel: "Prompt",
    },
    copyButton: {
      errorDescription: "The browser rejected the clipboard write.",
      errorTitle: "Copy failed",
      failedLabel: "Copy failed",
      successTitle: "Agent install prompt copied",
    },
    toaster: {
      close: "Dismiss notification",
    },
    skillDetail: {
      contents: "Contents",
      copiedInstallCommand: "Copied",
      copyInstallCommand: "Copy",
      copyInstallCommandFailed: "Copy failed",
      entryPoints: "Files worth opening",
      guardrails: "Important boundaries",
      install: "Install",
      installCommandCopied: "Install command copied",
      metadataNotFoundTitle: "Skill not found",
      metadataTitleSuffix: "guide",
      navBestFor: "Best for",
      navEntryPoints: "Entry points",
      navGuardrails: "Guardrails",
      navOutputs: "Outputs",
      navOverview: "Overview",
      navWorkflow: "Workflow",
      next: "Next skill",
      outputs: "What you get back",
      overview: "What this skill does",
      previous: "Previous skill",
      relatedSkills: "Related skills",
      useCase: "When to use it",
      workflow: "How it works",
    },
  },
  "zh-CN": {
    metadata: {
      description:
        "从同一个仓库发布的可复用 AI agent skills，可单独安装，也可作为精选集合使用。",
      keywords: [
        "AI agents",
        "agent skills",
        "Cursor",
        "Claude",
        "可复用 prompts",
        "开发者工具",
        "JUNERDD",
      ],
      ogDescription: "从同一个仓库发布的可复用 AI agent skills。",
      siteJsonLdDescription:
        "从同一个仓库发布的可复用 AI agent skills，可单独安装，也可作为精选集合使用。",
      srOnlyBrand: "JUNERDD Skills - 可复用 AI agent skills",
      titleDefault: "JUNERDD Skills · 可复用 agent skills",
      titleTemplate: "%s · JUNERDD Skills",
    },
    nav: {
      github: "GitHub",
      home: "JUNERDD 首页",
      languageSwitcher: "切换语言",
    },
    hero: {
      copiedInstall: "已复制 prompt",
      copyInstall: "复制安装 prompt",
      eyebrow: "Agent skill 集合",
      repository: "查看仓库",
      tagline: "把可复用 AI agent skills 打包成可安装的工作流。",
    },
    support: {
      afterCollectionVersion: " 当前版本），工具需要时也可以固定自己的运行时版本。",
      afterInstallPath: "，每个 skill 都带有 prompts 和文档。根目录 ",
      afterRootVersion: " 记录精选集合版本（",
      beforeCollectionVersion: "v",
      beforeInstallPath: "可安装 skill 位于 ",
      heading: "交付内容",
    },
    skillsList: {
      description:
        "每个本地可安装 skill 都有一份操作手册。打开 guide 可以查看工作流、边界、输出和源码入口。",
      openGuide: "打开 guide",
      title: "Skills 一览",
    },
    finalCta: {
      copied: "已复制",
      copy: "复制",
      description: "如果希望 agent 自动安装这个仓库而不是手动复制文件，可以告诉它：",
      figureLabel: "Agent 安装指令",
      footerMeta: "skills · collection",
      heading: "接入你的 agents",
      promptLabel: "Prompt",
    },
    copyButton: {
      errorDescription: "浏览器拒绝了剪贴板写入。",
      errorTitle: "复制失败",
      failedLabel: "复制失败",
      successTitle: "Agent 安装 prompt 已复制",
    },
    toaster: {
      close: "关闭通知",
    },
    skillDetail: {
      contents: "目录",
      copiedInstallCommand: "已复制",
      copyInstallCommand: "复制",
      copyInstallCommandFailed: "复制失败",
      entryPoints: "值得打开的文件",
      guardrails: "重要边界",
      install: "安装",
      installCommandCopied: "安装命令已复制",
      metadataNotFoundTitle: "Skill 未找到",
      metadataTitleSuffix: "指南",
      navBestFor: "适用场景",
      navEntryPoints: "入口文件",
      navGuardrails: "边界",
      navOutputs: "输出",
      navOverview: "概览",
      navWorkflow: "工作流",
      next: "下一个 skill",
      outputs: "你会得到什么",
      overview: "这个 skill 做什么",
      previous: "上一个 skill",
      relatedSkills: "相关 skills",
      useCase: "什么时候使用",
      workflow: "如何工作",
    },
  },
};

export async function getDictionary(locale: Locale) {
  return dictionaries[locale];
}
