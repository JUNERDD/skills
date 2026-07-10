import type { Locale } from "@/i18n/routing";
import type { SkillDetail, SkillEntryPoint } from "@/lib/content/types";

type SkillTranslation = Partial<Omit<SkillDetail, "entryPoints" | "slug">> & {
  entryPoints?: Partial<Pick<SkillEntryPoint, "description" | "label">>[];
};

const skillTranslations: Partial<Record<Locale, Record<string, SkillTranslation>>> = {
  "zh-CN": {
    "comment-strategist": {
      category: "代码文档",
      blurb: "添加高价值代码注释，同时避免注释噪音。",
      lead: "一个注释编辑工作流，让代码更容易理解，而不是把语法翻译成散文。",
      overview:
        "当文件需要围绕意图、约束、数据含义、公共契约或非显然控制流留下持久注释时使用此 skill。它会先读取本地注释风格，必要时移除薄弱或重复的注释，只添加能帮助后续读者推理代码的注释。",
      bestFor: [
        "为导出的函数、接口、类、类型和配置对象补充文档。",
        "用经得起实现变化的说明替换过时或只复述语法的注释。",
        "澄清字段、选项、状态变体，以及属于契约一部分的分支含义。",
      ],
      workflow: [
        "编辑前先阅读顶层定义，让注释匹配文件真实的所有权边界。",
        "识别附近注释的语言、语气、密度和格式约定。",
        "按读者价值排序候选注释，并选择最小但有用的粒度。",
        "在添加新注释前改写或移除低价值注释，保持一致的文档声音。",
        "复读最终文件，确认每条注释在小的实现细节变化后仍然成立。",
      ],
      outputs: [
        "默认只提交针对注释的补丁，除非用户明确要求更广的代码修改。",
        "解释分支为何存在、字段意味着什么，或哪里容易误用的注释。",
        "包含所请求验证结果的简洁完成说明。",
      ],
      guardrails: [
        "不要添加只是复述语法的叙述。",
        "除非当前请求明确要求，不要 stage、commit 或推进 Git 状态。",
        "匹配仓库现有注释风格，而不是强行引入新的文档体系。",
      ],
      entryPoints: [
        { description: "注释选择、粒度和清理规则。", label: "工作流" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "exhaustive-code-slimmer": {
      category: "代码清理",
      blurb: "用 DX 感知的架构门禁最大化安全删码。",
      lead: "一个删除优先的工作流，用于减少需维护代码，同时保持外部可观察行为不变。",
      overview:
        "当代码库需要激进但有纪律的简化时使用此 skill。它会建立行为保持 oracle，审计可删除代码，测试删除和简化候选项，并在架构级重构前暂停等待明确批准，让瘦身提升可维护性，而不是制造稠密或高风险代码。",
      bestFor: [
        "寻找可删除文件、分支、导出、依赖、包装层和重复逻辑。",
        "用 build、typecheck、test、lint、smoke 或 contract oracle 验证删减候选项。",
        "诊断阻碍安全删除的架构问题，并在重构前提出 DX 导向的选项。",
      ],
      workflow: [
        "记录基线文件、LOC、字节数、依赖、大文件、重复块以及生成或 vendor 目录。",
        "在仓库可用时运行审计和架构 DX 扫描。",
        "删除代码前设计当前可用的最强行为保持 oracle。",
        "跨每一层枚举删除、简化、依赖、配置、测试和架构候选项。",
        "搜索精确或分区后的候选集合，直到当前前沿没有未测试候选项。",
      ],
      outputs: [
        "前后指标、已接受候选项、被拒绝的高风险候选项和瘦身比例。",
        "最终代码缩减结果的 oracle 命令和剩余盲点。",
        "当安全瘦身需要结构清理时，给出需批准的架构选项。",
      ],
      guardrails: [
        "不要把压缩、混淆、纯空白删除或注释删除算作代码瘦身。",
        "没有证据时不要删除公共 API、迁移、兼容 shim、安全检查、运维日志或配置。",
        "在用户明确批准某个选项或范围前，不要执行架构级重构。",
      ],
      entryPoints: [
        { description: "穷尽式瘦身工作流、oracle 规则和批准门禁。", label: "工作流" },
        { description: "仓库清单、指标和候选项枚举助手。", label: "代码瘦身审计" },
        { description: "基于 oracle 命令的精确和分区候选搜索。", label: "穷尽式收缩" },
        { description: "删除和简化候选项目录。", label: "转换目录" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "reduce-reinvention": {
      category: "复用策略",
      blurb: "发现重复劳动，并引导复用优先的整合。",
      lead:
        "一个复用优先工作流，用于发现已有资产、判断是否采纳或整合，并记录有证据的差异化选择。",
      overview:
        "当团队在代码、库、服务、模板、文档、平台流程或架构决策上重复造轮子时使用此 skill。它结合先搜索再构建、重复类型分类、build-vs-reuse 评分、迁移规划和轻量 catalog 脚本，让复用决策基于证据，而不是抽象口号。",
      bestFor: [
        "审计重复实现、重叠服务、重复模板或废弃 fork。",
        "判断应该采纳、适配、包装、抽取、整合、下线，还是记录合理分歧。",
        "创建可复用资产 catalog、ADR/RFC 记录、迁移计划、golden path 和治理说明。",
      ],
      workflow: [
        "框定被重复的能力、受影响 owner、目标结果、约束和所需深度。",
        "在提出新工作前搜索本地代码、文档、manifest、设计系统、服务 catalog、ADR、ticket 和团队约定。",
        "按完全复制、近似克隆、共享业务规则、重叠服务、模板重复、废弃 fork 或合理分歧分类候选项。",
        "从适配度、所有权、维护、安全、兼容性、迁移成本和未来演进角度评分复用价值。",
        "推荐干预方式，并通过示例、owner、生命周期、反馈渠道和指标让复用路径清晰可见。",
      ],
      outputs: [
        "包含路径、符号、包或服务名、文档、搜索词、owner、consumer 和置信度的证据。",
        "带成本、风险、迁移工作量、安全或 license 顾虑以及兼容性说明的建议。",
        "下一步行动、owner、验收标准，以及证明重复劳动减少的指标。",
      ],
      guardrails: [
        "不要只因为代码长得像就消除重复；先验证领域知识、变更节奏和未来演进。",
        "没有负责 owner、示例、版本/弃用策略和支持预期时，不要创建共享库、平台服务或 golden path。",
        "不要只依赖自动 clone detection；结合脚本输出、代码审查、领域上下文、所有权数据和使用证据。",
      ],
      entryPoints: [
        { description: "复用优先审计工作流、建议和 guardrails。", label: "工作流" },
        { description: "让复用可发现、可维护的端到端模型。", label: "复用 playbook" },
        { description: "重复造轮子审计的搜索策略和证据收集提示。", label: "审计清单" },
        { description: "Build-vs-reuse 评分和建议规则。", label: "决策矩阵" },
        { description: "可填写的审计、ADR/RFC、catalog、迁移和例外模板。", label: "模板" },
        { description: "扫描仓库中的重复代码和重复造轮子信号。", label: "重复造轮子审计" },
        { description: "生成轻量可复用资产清单。", label: "复用 catalog" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "find-local-skill": {
      category: "Agent 工作流",
      blurb: "先拆解请求，再寻找相关本地 skills。",
      lead:
        "一个 skill 选择工作流，用于先拆解请求、盘点本地 skills、选择适用项，再进入正常分析。",
      overview:
        "当 agent 需要在规划、路由或实现请求前检查可用本地 skills 时使用此 skill。它会把请求拆成交付物、工作流阶段、工具、领域和隐含前置条件，再结合会话内 skill 元数据和本地扫描器，覆盖普通项目 skills 文件夹、Cursor、Claude Code、OpenCode、Codex、共享 Agent Skills roots 和插件 skill 缓存，只加载真正影响任务做法的 skill 内容。",
      bestFor: [
        "在需求分析、规划或实现前寻找相关本地 skills。",
        "把模糊或多阶段请求通过显式 skill 选择来路由，而不是依赖记忆。",
        "发现由交付物、工具或工作流阶段隐含出来的前置 skills。",
        "审计普通项目 skills 文件夹、Cursor、Claude Code、OpenCode、Codex 和共享 Agent Skills roots 的可用 skill 覆盖。",
        "区分 `product-design:index` 这类带命名空间的插件 skills。",
      ],
      workflow: [
        "把请求拆成显式动作、交付物、工件、工具、工作流阶段和隐含前置条件。",
        "在读取额外 skill 内容前，先盘点会话上下文中已有的 skills。",
        "文件系统可用时运行本地扫描器，覆盖支持的用户、项目和插件 roots。",
        "在 broad inventory 之后，针对单个 facet 或紧密同义词组做聚焦补充搜索。",
        "用 skill 名、带命名空间的插件名、描述、显式提及、工具、文件类型、产品、领域、工作流线索和拆解出的前置条件做匹配。",
        "只选择会实质改变工作方式的 skills。",
        "按依赖顺序应用选中的 skill 工作流，再继续用户要求的分析或实现。",
      ],
      outputs: [
        "一段简短 skill 选择摘要，为每个选中 skill 给出一个理由。",
        "使用所选工作流产出的分析、计划、实现指导或实际工作成果。",
        "没有找到合适本地 skill 时的明确说明。",
      ],
      guardrails: [
        "拆解、盘点和选择完成前，不要开始解法分析。",
        "不要加载无关 skill 内容。",
        "第一次 broad inventory 前，不要用 query 缩小范围。",
        "不要把不相关的拆解 facet 塞进一个长 scanner query，因为 scanner 会要求所有词都匹配。",
        "当命名空间插件条目和泛用名称都可能匹配时，优先选择命名空间插件条目。",
      ],
      entryPoints: [
        { description: "Skill 盘点、选择和分析顺序规则。", label: "工作流" },
        { description: "扫描常见本地 skill roots 的文件系统工具。", label: "本地 skill 扫描器" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "git-commit": {
      category: "Git 工作流",
      blurb: "根据 staged diff 起草 Conventional Commit 消息。",
      lead: "一个窄范围 commit 消息助手，只查看 index 并返回准确的 Conventional Commit 草稿。",
      overview:
        "当 staged changes 已准备好但 commit 文案需要更精确时使用此 skill。它检查 staged status、staged stats 和 staged diff，再根据即将提交的真实行为推断正确的 Conventional Commit 类型和消息，不会修改仓库。",
      bestFor: [
        "从当前 staged 批次生成清晰的 subject 和 body。",
        "检查 staged 工作是否混杂到不适合一个诚实的 commit。",
        "让 commit 文案扎根于即将提交的内容，而不是分支名或意图。",
      ],
      workflow: [
        "检查 `git status --short`、`git diff --cached --stat` 和 `git diff --cached`。",
        "如果没有 staged 内容则停止，而不是退回去看 unstaged work。",
        "根据 staged 行为推断 commit 类型，而不是只看分支名或意图。",
        "起草 Conventional Commit subject 和 body，准确命名用户可见或结构性变化。",
        "只返回消息文本，不运行 `git commit`。",
      ],
      outputs: [
        "一份 Conventional Commit 消息建议。",
        "当 staged 批次混杂或有误导性时给出警告。",
        "不修改仓库。",
      ],
      guardrails: [
        "只检查 staged changes。",
        "不要 stage 文件、读取 unstaged diff 或创建 commit。",
        "不要发明 staged diff 中看不见的产品上下文。",
      ],
      entryPoints: [
        { description: "只检查 staged 内容并起草 Conventional Commit 的规则。", label: "工作流" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    mr: {
      category: "Git 工作流",
      blurb: "使用并维护 Git MR/PR 辅助 CLI。",
      lead: "一个 Git 合并请求工作流，用于安全运行 mr CLI，覆盖分支策略、默认 detached 模式、请求提供方、配置、冲突恢复、自动更新提示和工具维护。",
      overview:
        "当需要通过 `mr`、`mrm`、`mrt` 或 `mrp` 创建、预览、配置、排查、安装、更新、卸载或维护 Git 合并请求或拉取请求时使用此 skill。它让 agent 遵循 CLI 真实的请求提供方行为、非阻塞更新提示和 inline/detached 冲突恢复路径，而不是自造手写 git 恢复步骤。",
      bestFor: [
        "从当前分支创建或预览到 master、test、prerelease 或任意目标分支的 Git 合并请求或拉取请求。",
        "检查本地是否缺少 mr，并在用户确认后安装。",
        "在 merge、rebase、merge-target、direct PR 和 detached 无感模式之间做选择。",
        "配置 CNB、GitHub、GitLab 或自定义请求命令。",
        "理解自动更新提示，以及禁用提示的环境变量。",
        "处理停住的 merge 或 rebase 状态，并保留 CLI 拥有的 resume 路径。",
        "维护 CLI 背后的 TypeScript/Pastel/Ink/Zod 实现。",
      ],
      workflow: [
        "执行会修改 MR 分支的命令前，先用 `git status --short --branch` 检查仓库状态。",
        "解析目标别名；对含糊的 MR 请求，先澄清 source、target，以及保留还是删除重建 MR 分支。",
        "当策略、无感模式或仓库状态不清楚时，先用 `--dry-run`。",
        "一次只运行一种策略，并尊重 `MR_STRATEGY`、`mr.strategy`、`MR_DETACHED` 和 `mr.detached` 的配置优先级。",
        "把交互式更新提示当作信息性 stderr，不当成工作流输出或命令失败。",
        "发生冲突时，把解决动作交给用户；只有在冲突已 staged 后，才重跑匹配的 `mr` resume 命令。",
        "编辑 CLI 项目时，先确认实现仓库身份，不假设本机路径，并让 README 行为说明、命令示例、图示和自动更新提示说明与实现保持一致。",
      ],
      outputs: [
        "`mr`、`mrm`、`mrt` 和 `mrp` 工作流的安全命令选择。",
        "自动更新提示的解释和禁用指导。",
        "与当前 CLI 实现一致的冲突 handoff 和 resume 指令。",
        "针对 mr 项目的有范围维护建议和验证命令。",
      ],
      guardrails: [
        "不要组合多个策略 flag，也不要把 `--rm-mr` 和 `--pr` 一起用。",
        "不要用手写 git commit、手动 push 或 shortcut `--pr` 流程替代 CLI 冲突恢复。",
        "除非用户明确要求该具体操作，否则不要修改已停住的 merge/rebase 状态。",
      ],
      entryPoints: [
        { description: "MR 命令选择、策略规则和冲突恢复 guardrails。", label: "工作流" },
        { description: "详细命令面、无感模式、配置、安装和维护说明。", label: "CLI 参考" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "split-commits": {
      category: "Git 工作流",
      blurb: "把混杂 working tree 拆成聚焦的本地 commits。",
      lead: "一个有纪律的 staging 工作流，把宽泛本地修改拆成短而可审查的 commit 序列。",
      overview:
        "当无关事项、重构、行为变化、生成文件或可分离 hunk 混在一起时使用此 skill。它规划逻辑批次，一次 stage 一个批次，调用 `git-commit` 生成消息，并在每次 `git commit` 前要求明确确认。",
      bestFor: [
        "分离同一个 working tree 中的无关事项。",
        "把重构和行为变化分开。",
        "构建更容易审查、回滚和解释的本地 commits。",
      ],
      workflow: [
        "检查当前 Git 状态，包括 staged 和 unstaged 工作。",
        "判断修改是否需要拆分，并写出简短 commit 计划。",
        "改变 staged 文件前尊重现有 index 内容。",
        "一次只 stage 一个逻辑批次，并只包含属于该批次的文件和 hunk。",
        "为 staged 批次调用 `git-commit`，并在运行每个 commit 前请求确认。",
      ],
      outputs: [
        "一组聚焦 commits 的建议顺序。",
        "一次一个 staged 批次，并配套 Conventional Commit 草稿。",
        "只有在明确批准后才创建本地 commits。",
      ],
      guardrails: [
        "不要把 push 包含在拆分工作流里。",
        "不要为了方便把无关修改压进一个 commit。",
        "重塑 index 时不要覆盖用户已有修改。",
      ],
      entryPoints: [
        { description: "Commit 规划、staging、批准和排序规则。", label: "工作流" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "multitask-coordinator": {
      category: "Agent 协作",
      blurb: "用委派优先的并行调度协调多步骤工作。",
      lead:
        "一个 parent-agent 调度器：构建依赖图、最大化有用并行、不打断健康 worker、综合证据并验证集成结果。",
      overview:
        "用于可从并行探索、实现、审查或验证中受益的非平凡多步骤任务。触发后，parent 框定目标、构建任务依赖图，在工具与隔离容量允许下派发最大有用的就绪非重叠 worker 集合，以事件驱动方式继续调度且不打断健康 worker，并保留共享契约、集成、验证和用户沟通的所有权。只有真正琐碎或不可委派的工作才由 parent 直接处理。",
      bestFor: [
        "在探索、实现、审查和验证之间最大化有用并行。",
        "构建依赖图并填满每个安全的就绪 worker 槽位，而不是默认串行化。",
        "在大型仓库、monorepo、dirty worktree 或隔离 worktree/branch 中分配不重叠的写入所有权。",
        "在 parent 集成结果并解锁依赖项时，保持健康 worker 不被打断。",
        "审计多 agent 编排中的隐藏串行化、空闲容量或不必要打断。",
      ],
      workflow: [
        "框定目标、验收标准、约束和验证边界。",
        "阅读适用仓库规则，并在分配所有权前检查 dirty worktree。",
        "构建带依赖、读写范围、预期证据和完成标准的任务图。",
        "派发最大有用的就绪非重叠 worker 集合；随 worker 完成继续事件驱动调度。",
        "不打断健康 worker；parent 在契约、集成和仅 parent 决策上推进协调路径。",
        "综合证据、解决冲突、验证集成结果，并报告剩余风险。",
      ],
      outputs: [
        "一份依赖感知的调度说明，写明哪些留给 parent、哪些被委派。",
        "带有所有权边界、约束、验证和预期输出的 worker prompts。",
        "已采纳结果、阻塞点、命令证据、剩余风险和最终验证的综合。",
      ],
      guardrails: [
        "不要仅为了减少 worker 数量而让安全有用的槽位空闲。",
        "不要取消、重启、改派健康 worker，或向其发送未经请求的 follow-up。",
        "不要给 sibling workers 分配重叠写入，除非隔离 branch 或 worktree 让计划中的合并边界明确。",
        "没有审查改动文件、产物、命令输出或其他具体证据前，不要把 worker 输出当作事实。",
      ],
      entryPoints: [
        { description: "委派优先调度、所有权、健康 worker 连续性、综合和验证规则。", label: "工作流" },
        { description: "并行调度有效性的指标与诊断。", label: "调度审计" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "plan-mode": {
      category: "规划",
      blurb: "在编辑前规划复杂或高风险工作。",
      lead:
        "一个无修改规划工作流，用于收集证据、消除歧义，并产出需要批准的实施计划。",
      overview:
        "当任务复杂、模糊、高风险或范围较广，过早编辑会造成返工或偏离用户意图时使用此 skill。它让 agent 留在只读探索中，提出聚焦的澄清问题，明确可能涉及的文件和验证路径，并在执行前等待明确批准。",
      bestFor: [
        "在编辑前规划多文件实现、架构、路由、数据流或权衡较多的工作。",
        "为 dirty worktree、迁移、设置、部署、生成代码或其他高影响面保持严格边界。",
        "创建包含受影响区域、顺序步骤、验证、非目标和关键风险的具体计划。",
      ],
      workflow: [
        "重述目标，并定义无修改规划边界。",
        "只用只读的文件、代码、文档、诊断或 subagent 探索来研究必要信息。",
        "当缺失决策会实质改变实现时，尽早提问。",
        "给出简洁计划，包含范围、文件或模块、实施顺序、验证、非目标和风险。",
        "在编辑、stage、启动写入型工具或改变系统前等待批准。",
      ],
      outputs: [
        "针对当前任务的具体批准门控计划。",
        "当歧义会改变计划时，提出聚焦澄清问题。",
        "批准后清晰交接到执行，并包含承诺的验证步骤。",
      ],
      guardrails: [
        "规划时不要编辑文件、创建文件、stage commits、安装包、启动服务或运行写入型脚本。",
        "不要把未解决的产品、数据、安全或架构假设藏在最终计划里。",
        "不要把用户批准研究误当成批准实现无关清理。",
      ],
      entryPoints: [
        { description: "规划边界、工作流、澄清规则和交接要求。", label: "工作流" },
        { description: "生命周期、模式边界、研究策略、图示和常见失败模式。", label: "架构参考" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    debug: {
      category: "运行时调试",
      blurb: "用完整的页面生命周期 fetch 证据证明运行时根因。",
      lead:
        "一个要求证据的调试系统，提供回调感知的仪表盘启动、明确的启动状态、页内确认式浏览器传输，以及不按事件数量截断的应用 fetch 捕获。",
      overview:
        "当只读代码不够时使用此 skill。它构建宽但去重的因果假设集，在本地 collector 就绪后打开仪表盘，并通过页内确认式内存队列收集相关 NDJSON 证据。针对 fetch 调查，它记录当前页面生命周期内实际发出的每个应用 fetch，不做采样或任意数量截断，按字节分帧并向 `/ingest/batch` 发送确认式批次。随后先摘要大日志，再通过增量 root-cause 账本证明因果链，修复已证明的根因，并仅在因果充分后把改动约束在最窄的完整范围内，独立验证并移除临时 instrumentation。",
      bestFor: [
        "昂贵、偶发或难以重复的复现，需要一次高覆盖探针通过。",
        "前端问题需要浏览器日志直接到达活动 collector。",
        "高频浏览器请求流，需要审计单个页面生命周期内实际发出的每个应用 fetch。",
        "运行时失败很容易猜但很难从静态代码证明。",
        "需要保留已否定路径，避免后续轮次在没有新证据时重复调查。",
      ],
      workflow: [
        "定义失败契约，并沿边界、分支、状态、异步、缓存和外部调用构建因果图。",
        "枚举并去重假设；在 one-shot 模式下覆盖每个合理子系统，不设任意探针上限。",
        "用 `scripts/debug_session.py` 启动或连接日志会话；让本地启动尝试打开仪表盘并明确报告状态，纯 headless 环境才使用 `--no-open-dashboard`。",
        "针对浏览器 fetch 流，复制 `assets/browser-debug-transport.mjs`，在内存中为每个事件保留一份序列化副本，并发送不按数量截断的字节分帧确认式批次。",
        "通过覆盖门禁，收集一次干净复现，并在阅读原始体积前摘要 NDJSON 日志。",
        "将假设标记为确认、否定、不确定或未到达，然后追加 root-cause 调查账本。",
        "修复有证据证明的根因；仅在因果充分后最小化范围，用独立运行验证，然后移除 instrumentation 并停止 collector。",
      ],
      outputs: [
        "一份增量 root-cause 文档，保留每轮调查；成功最终清理时删除，除非用户要求保留。",
        "临时 instrumentation，以及 collector、日志和 root-cause 文档清理。",
        "有新运行时日志支撑的已验证根因修复。",
      ],
      guardrails: [
        "不要在没有运行时证明的情况下交付猜测性修复，也不要为了更小改动而选择仍保留已证明因果机制的症状级 workaround。",
        "除非证明直接 collector 投递被阻塞，否则不要创建 app-local proxy APIs 来转发浏览器日志。",
        "需要完整覆盖时，不要对实际应用 fetch 生命周期事件做采样、截断或按数量限制。",
        "不要声称页内浏览器队列能跨导航、刷新、进程终止或内存耗尽继续存在。",
        "不要把 collector 的 `/ingest`、`/ingest/batch` 或仪表盘流量记录为应用 fetch。",
        "除非有新的运行时证据解释原因，否则不要重试已否定或被取代的 root-cause 路径。",
        "当 NDJSON 证据文件可用时，不要分析 collector stdout；先做摘要。",
        "中间清日志时保留 root-cause 文档，最终成功清理时再删除，除非用户要求保留证据。",
      ],
      entryPoints: [
        { description: "证据优先调试序列、one-shot 模式和清理要求。", label: "工作流" },
        { description: "昂贵或偶发复现的高覆盖探针规划。", label: "One-shot 参考" },
        { description: "Collector bootstrap、日志格式和调试说明。", label: "运行时参考" },
        { description: "增量证据与排除账本结构。", label: "Root-cause 参考" },
        { description: "启动、确认、恢复和停止本地 collector 与仪表盘会话。", label: "会话助手" },
        { description: "用于字节分帧确认式 fetch 捕获的页内内存队列。", label: "浏览器传输" },
        { description: "在阅读原始体积前摘要 NDJSON 证据。", label: "日志摘要器" },
        { description: "本地 NDJSON collector 和 dashboard 实现。", label: "Collector" },
        { description: "分离会话、自动仪表盘和生命周期回归测试。", label: "生命周期测试" },
        { description: "内存队列、完整 fetch、分批、超时和重试回归测试。", label: "浏览器传输测试" },
      ],
    },
    "grill-me": {
      category: "计划压力测试",
      blurb: "一次一个高杠杆问题，压力测试计划或设计。",
      lead: "一个结构化追问工作流，用于明确假设、权衡、风险和范围边界。",
      overview:
        "当计划、设计、rollout 或技术方向需要在实现前接受压力测试时使用此 skill。它一次问一个问题，保持 Markdown Q&A log 同步，并在决策足够具体、可交给另一位工程师执行时产出可规划结果。",
      bestFor: [
        "把模糊计划转化为明确的成功标准、非目标和阶段边界。",
        "发现隐藏失败模式、不可逆决策和 stakeholder 成本。",
        "从实时问答会话中产出可规划记录。",
      ],
      workflow: [
        "为当前会话开始或恢复本地 grilling log。",
        "询问最高杠杆的未解决问题，而不是收集浅层偏好。",
        "在相关时覆盖目标、范围、stakeholders、替代方案、风险、验证、rollout 和 rollback。",
        "随着计划变清晰，同步维护对话记录。",
        "最终生成 planning-ready outcome Markdown，并移除 active session 指针。",
      ],
      outputs: [
        "一份实时 Q&A transcript。",
        "一份最终的 planning-ready outcome document。",
        "明确的假设、权衡、风险和开放决策。",
      ],
      guardrails: [
        "一次只问一个问题。",
        "不要把模糊回答当作最终规划输入。",
        "完成后不要留下 active session pointer。",
      ],
      entryPoints: [
        { description: "提问标准、覆盖地图和最终化流程。", label: "工作流" },
        { description: "本地 transcript 和 outcome 文件支持。", label: "会话脚本" },
        { description: "已记录追问行为和会话生命周期说明。", label: "参考" },
      ],
    },
    "code-review": {
      category: "代码审查",
      blurb: "执行以产品依据为准、具备有界报告血缘的深度审查。",
      lead:
        "一个冻结范围的深度审查工作流：要求权威 expected-behavior 依据、稳定问题指纹，并把实现后复审限制为终止 generation。",
      overview:
        "当用户请求 `/code-review`、PR/diff/branch/staged review 或 merge 前安全检查时使用此 skill。它先做只读编排评估并冻结初审范围，追踪可传播风险，在把产品选择判为 defect 前要求权威产品或契约证据，并为问题生成确定性的语义指纹。receiving 最多可生成一次仅覆盖实现 delta 与受影响执行链的 generation-1 复审；该报告是终点，不能自动再启动 receiving。",
      bestFor: [
        "审查 PR、branch diff、staged changes、working tree、聚焦文件或 pasted code。",
        "判断并行 specialist subagents 何时能实质提升审查价值。",
        "在 merge 前发现正确性 bug、release-blocking regression、安全问题、契约风险和缺失测试。",
        "区分已验证 defect、未确认产品意图与已裁决产品决策。",
        "产出包含 coverage、语义问题血缘和有界 receiving handoff 的可复用 artifact。",
      ],
      workflow: [
        "先确定 review chain generation、冻结范围，并记录 baseline、target、需求与最小 diff inventory。",
        "启动只读 orchestration-assessment subagent，并执行其单 reviewer 或 specialist 计划。",
        "当风险可能传播时，沿控制流、数据、安全、持久化、集成和测试路径追踪到 diff 之外。",
        "先建立 expected behavior 依据，再独立验证、去重并为 candidate 分配稳定 ID、issue key 和 fingerprint。",
        "按模板写出标准 `code-review` Markdown 报告，并用 `scripts/validate_review_report.py` 校验。",
      ],
      outputs: [
        "一份经验证的标准 `code-review` Markdown 报告。",
        "一段简短 terminal summary，包含 recommendation、完成状态、严重度计数和编排模式。",
        "完整 findings index、test gaps、coverage ledger、问题血缘和有界 receiving handoff。",
      ],
      guardrails: [
        "除非用户明确要求 fixes，否则不要在 review 期间改代码。",
        "不要 stage、commit、push 或改变 Git 状态。",
        "不要把审查深度等同于 agent 数量；仅在范围与风险证明有必要时启动 specialists。",
        "未经协调者独立综合，不要把 subagent 结论直接写入报告。",
        "不要把未确认的产品选择判为 defect；应转为影响批准的 Question。",
        "不要自动消费 generation-1 post-review；把剩余 findings 返回给用户或产品 owner。",
        "当用户要求专门的 regression 或 hack gate 时，改用 `regression-review` 或 `hack-review`。",
      ],
      entryPoints: [
        { description: "编排、深度审查契约、报告写作规则和 guardrails。", label: "工作流" },
        { description: "评估协议与 specialist 分区指导。", label: "Subagent 编排" },
        { description: "标准 code-review 章节和 coverage ledger 形状。", label: "报告模板" },
        { description: "校验血缘、产品依据、问题指纹和终止 generation。", label: "报告校验器" },
        { description: "覆盖报告血缘与产品意图门禁的回归测试。", label: "校验器测试" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "receiving-code-review": {
      category: "代码审查后续",
      blurb: "端到端追踪 findings，并在不递归滚动 review 的前提下完成处置。",
      lead:
        "一个执行链优先的响应工作流：继承既有产品裁决、强制 disposition 状态相容，并限制实现后复审次数。",
      overview:
        "在收到 `code-review` 报告或等价 PR feedback 后使用此 skill。分配 disposition 前，它先从真实触发与入口出发，经过 guards、控制/数据/状态传播、持久化与外部效应、失败语义，一直追踪到终端影响。它跨 generation 继承匹配的 Intentional、Disproved、Stale 和 Duplicate 裁决；链路或产品权威证据不完整时禁止修复；只委派状态相容的已确认动作；把相邻的新发现作为 provisional residual 返回；初审链最多运行一次终止 post-review，且不自动消费其 findings。",
      bestFor: [
        "在改代码前，针对完整端到端执行链重新验证每个 `F#`、`T#` 和未覆盖的 `A#`。",
        "用证据正式挑战错误、夸大或过时的 review 主张。",
        "通过 coding subagent 修复已确认的正确性、安全、契约或测试问题。",
        "除非代码、契约或实质证据变化，否则保护权威产品意图不被重新打开。",
        "在未请求发布时保留 staged 工作，并让新修复保持 unstaged。",
      ],
      workflow: [
        "阅读完整 source review，或把非结构化反馈规范化为稳定 item IDs。",
        "捕获血缘与 Git 状态，先重建并冻结可复用的 EC# 端到端执行链，再启动 re-review 编排。",
        "针对完整执行链和 expected-behavior 权威性验证每项，并分配相容的 verdict、action 与 implementation state。",
        "把已确认的修复或测试工作委派给 coding subagent，并给出明确所有权与 no-staging 约束。",
        "generation-0 source 最多使用一次实现 delta post-review，将其作为终点链接，并在不自动 receiving 的情况下返回剩余 findings。",
      ],
      outputs: [
        "一份经验证的 `receiving-code-review` disposition ledger 与 resolution report。",
        "针对有争议 source claims 的正式 challenge cards。",
        "可审计的 EC# 执行链与语义血缘 ledger。",
        "针对已确认 review findings 的有范围 unstaged 修复，以及验证证据。",
      ],
      guardrails: [
        "不要盲目应用 review feedback。",
        "在 intake、条目枚举及 complete/blocked EC# 重建完成前不要改代码。",
        "当 coding subagent 可用时，不要只在协调者里实现已确认的代码或测试改动。",
        "除非当前请求明确要求，否则不要 stage、commit 或改变 Git index。",
        "在每个 source item 都有 disposition、每个已实现 item 都有针对性验证前，不要声称已解决。",
        "不要静默丢弃或自动实现 verifier 发现的独立问题；应把它们作为 provisional residual candidates 返回。",
        "不要自动修复 blocked chain 或未确认产品选择，也不要从终止 post-review 自动开启下一轮 receiving。",
      ],
      entryPoints: [
        { description: "重新审查、挑战、coding 委派和 Git index 保留规则。", label: "工作流" },
        { description: "评估协议与 specialist 重新审查指导。", label: "重新审查编排" },
        { description: "标准 receiving-code-review resolution report 形状。", label: "Disposition 模板" },
        { description: "校验执行链、血缘继承、状态相容和单次 review 预算。", label: "Disposition 校验器" },
        { description: "覆盖执行链优先 disposition 与有界后续的回归测试。", label: "校验器测试" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "hack-review": {
      category: "代码审查",
      blurb: "审查实现是否依赖脆弱的 hack-like 捷径。",
      lead: "一个 coverage-led 审计，用于发现结构性捷径、所有权泄漏、被掩盖的根因和脆弱边界处理。",
      overview:
        "当一个变更需要实现质量门禁，而不是普通代码审查时使用此 skill。它审查声明范围，枚举发现的每个不同 hack-risk，记录有意例外，并显示哪些所有权边界已覆盖或仍未知。",
      bestFor: [
        "发现会隐藏破坏性不变量的 impossible-state fallback。",
        "标记没有解决根因的 symptom-masking patch。",
        "捕捉重复抽象、硬编码特例和边界绕过。",
      ],
      workflow: [
        "先设定审查范围，并拒绝静默扩大范围。",
        "阅读相关 diff、需求和触及的所有权边界。",
        "识别 hack-risk 模式，并归并为不同 findings。",
        "写出 Markdown report，包含 recommendation、findings、有意例外和 coverage ledger。",
        "让 gate 与最高严重度未解决 finding 和 coverage 状态保持一致。",
      ],
      outputs: [
        "一份 coverage-led Markdown hack-risk report。",
        "一段简短 terminal summary。",
        "完整 findings、intentional exceptions 和 uncovered boundaries 索引。",
      ],
      guardrails: [
        "不要静默抽样大范围。",
        "不要把 recommendation 降到低于最强未解决 finding。",
        "当主要问题是用户可见行为时，改用 `regression-review`。",
      ],
      entryPoints: [
        { description: "范围、findings、gate 和报告写作规则。", label: "工作流" },
        { description: "标准报告章节和 coverage ledger 形状。", label: "报告模板" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "receiving-hack-review": {
      category: "代码审查后续",
      blurb: "消费 hack-review 报告，并在改代码前验证每个 finding。",
      lead: "一个响应工作流，把 hack-risk review findings 转化为有证据的修复、挑战或延续决策。",
      overview:
        "在收到 hack-review 报告或等价 PR feedback 后使用此 skill。它会在改代码前为每个 finding、有意例外和 coverage gap 建立 disposition ledger，然后只修复仍成立的问题，并为被挑战或缩窄的条目保留证据。",
      bestFor: [
        "验证每个 hack-risk finding 在当前 diff 中是否仍成立。",
        "修复所有权问题，同时不机械删除必要 guard。",
        "关闭或延续 `Not covered` 所有权边界。",
      ],
      workflow: [
        "阅读 review report，枚举每个 finding、exception 和 coverage gap。",
        "在规划编辑前对当前代码验证每个条目。",
        "建立 disposition ledger：fix、disprove、narrow、confirm 或 carry forward。",
        "应用有范围的修复，并命名受影响所有权边界和回归风险。",
        "报告每个条目的最终 disposition，不 stage，除非明确要求。",
      ],
      outputs: [
        "覆盖整份报告的 disposition ledger。",
        "针对已确认条目的有证据代码修改。",
        "disproven、narrowed、intentional 和 carried-forward 条目的总结。",
      ],
      guardrails: [
        "不要机械执行报告。",
        "除非当前请求明确要求 staging 或 committing，否则不要 stage changes。",
        "如果修复会扩大行为或削弱所有权边界，先缩窄或询问。",
      ],
      entryPoints: [
        { description: "Disposition ledger 和证据优先响应规则。", label: "工作流" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "regression-review": {
      category: "代码审查",
      blurb: "审查代码变更是否引入用户可见行为回归。",
      lead: "一个 coverage-led 审计，用于发现破坏或退化的用户路径、默认值变化、陈旧数据和行为路径变化。",
      overview:
        "当一个变更集需要用户可见行为门禁时使用此 skill。它审查声明范围，把有意可见变化与回归分开，在能澄清受影响路径时构建 scoped behavior-graph deltas，并写出报告，将每个触及 surface 标记为 reviewed、intentional、not covered 或 not relevant。",
      bestFor: [
        "检查重构或功能工作是否破坏了用户可见流程。",
        "审计 loading、error、permission、retry、ordering、export、email 或 CLI-output 变化。",
        "追踪发生变化的 input、guard、transform 和 output，而不是构建全仓调用图。",
        "产出 severity 与最强未解决 finding 对齐的审查 artifact。",
      ],
      workflow: [
        "设定或推断审查范围，并在可用时阅读需求。",
        "在判断行为前映射触及的用户可见 surfaces。",
        "为可建图的用户可见或未知影响 surface 构建 scoped behavior graph baseline。",
        "把当前行为与基线、意图和用户期望对比。",
        "写出所有不同 findings，而不是只写前几个。",
        "在 coverage ledger 中记录有意可见变化和未覆盖 surfaces。",
      ],
      outputs: [
        "一份 Markdown regression-review report。",
        "与 findings 和 coverage 对齐的 gate recommendation。",
        "完整 findings index、behavior graph deltas 和 coverage ledger。",
      ],
      guardrails: [
        "不要静默抽样大范围。",
        "除非实现问题改变了可见行为，否则不要把实现丑陋当作 regression。",
        "当主要担忧是脆弱实现结构时，改用 `hack-review`。",
      ],
      entryPoints: [
        { description: "范围、用户可见 findings、coverage 和 gate 规则。", label: "工作流" },
        { description: "标准报告章节和 coverage ledger 形状。", label: "报告模板" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "receiving-regression-review": {
      category: "代码审查后续",
      blurb: "消费 regression-review 报告，并在改代码前验证每个 finding。",
      lead: "一个响应工作流，用当前证据和有范围修复解决 regression-review findings。",
      overview:
        "在收到 regression-review 报告或相关 PR feedback 后使用此 skill。它会在编辑前用当前代码验证每个 finding、behavior graph delta、有意可见变化和 coverage gap，然后修复已证明的回归，并用证据挑战过时或有意的 findings。",
      bestFor: [
        "用当前 diff 和基线重新检查 regression gate。",
        "把 behavior graph deltas 与 findings 和 coverage rows 对齐。",
        "只修复已证明的用户可见回归。",
        "把真实回归与有意产品变化分开。",
      ],
      workflow: [
        "阅读报告并列出每个 finding、有意变化和未覆盖 surface。",
        "把 behavior graph deltas 与当前代码路径和 coverage ledger 对齐。",
        "用当前代码、基线和可见行为验证每个条目。",
        "编辑前建立 disposition ledger。",
        "用窄范围修改修复已确认回归。",
        "报告每个条目的 disposition，并保持 Git staging 不变，除非被要求。",
      ],
      outputs: [
        "完整 disposition ledger。",
        "针对已确认用户可见回归的有范围修复。",
        "challenged、narrowed、intentional 和 carried-forward 条目的证据。",
      ],
      guardrails: [
        "不要盲目应用 review feedback。",
        "除非当前请求明确要求，否则不要 stage changes。",
        "解决聚焦 regression finding 时，不要扩大用户可见行为。",
      ],
      entryPoints: [
        { description: "Disposition ledger 和 regression-response 要求。", label: "工作流" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
  },
};

export function getSkillTranslation(slug: string, locale: Locale) {
  return skillTranslations[locale]?.[slug];
}
