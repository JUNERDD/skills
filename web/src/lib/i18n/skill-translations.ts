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
      blurb: "用清晰的所有权边界协调复杂 subagent 工作。",
      lead: "一个 parent-agent 工作流，用于判断何时委派、分配 worker 范围、综合结果并验证最终产出。",
      overview:
        "用于非平凡多步骤任务，其中后台 subagents 可能有帮助，但 parent agent 必须负责问题框定、共享契约、委派决策、worker 所有权边界、综合、验证和用户沟通。它提供决策检查清单，帮助判断何时直接处理、选择 explorer 或 worker 形态、定义不重叠范围、保护原子迁移，并把 worker 输出转化为经过审查的证据。",
      bestFor: [
        "判断复杂仓库任务应由 parent 直接处理还是委派。",
        "在大型仓库、monorepo 或 dirty worktree 中分配明确的 worker 所有权边界。",
        "让共享契约、package exports、排序和破坏性迁移边界保持在 parent-agent 所有权下。",
        "协调独立的探索、实现、审查或验证切片。",
        "在不重复工作的情况下综合 worker 输出，并保持 parent 对最终结果负责。",
      ],
      workflow: [
        "阅读适用仓库规则，并在分配所有权前检查 dirty worktree。",
        "映射成功标准、受影响系统、可能 owner 文件、共享契约和验证命令。",
        "保持共享文件和契约由 parent 拥有，除非一个 worker 被明确指定为唯一 owner。",
        "基于独立性、范围清晰度和综合成本选择零个、一个或少量 workers。",
        "给每个 worker 明确目标、允许范围、禁止动作、验证期望和输出契约。",
        "审查 worker 证据，解决冲突或缺口，只整合被采纳的工作，并运行最窄可信验证。",
      ],
      outputs: [
        "一份委派决策，说明哪些留给 parent，哪些如有必要分配给 workers。",
        "带有所有权边界、约束、验证和预期输出的 worker prompts。",
        "已采纳结果、阻塞点、命令证据、剩余风险和最终验证的综合。",
      ],
      guardrails: [
        "不要委派琐碎请求或 parent 下一步必须亲自处理的阻塞工作。",
        "不要给 sibling workers 分配会重叠写入的共享文件、schema、生成物或全局配置。",
        "没有审查改动文件、产物、命令输出或其他具体证据前，不要把 worker 输出当作事实。",
      ],
      entryPoints: [
        { description: "委派决策、worker prompt 契约、综合和验证规则。", label: "工作流" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    debug: {
      category: "运行时调试",
      blurb: "用证据优先的日志工作流调试运行时问题。",
      lead: "一个要求证明的调试系统，用于运行时 bug、回归、偶发行为和不清楚的失败。",
      overview:
        "当只读代码不够时使用此 skill。它要求先提出假设、加日志、复现、记录 root-cause，再在修复后验证并清理。内置 collector 可把浏览器或应用日志捕获为 NDJSON，并暴露同源 dashboard 供实时检查；最终清理会移除 collector 产物和 root-cause 文档，除非要求保留证据。",
      bestFor: [
        "前端问题需要浏览器日志直接到达活动 collector。",
        "运行时失败很容易猜但很难从静态代码证明。",
        "需要带时间戳证据和前后对比的偶发行为。",
      ],
      workflow: [
        "在加 instrumentation 前陈述精确假设。",
        "连接现有日志会话或启动内置 collector。",
        "为每个假设添加最小临时 instrumentation。",
        "复现问题，检查记录的日志文件，并将假设标记为确认、否定或不确定。",
        "只应用已证明的修复，然后在移除 instrumentation 前收集新的修复后日志。",
      ],
      outputs: [
        "一个随调查演进的 root-cause 文档；成功最终清理时删除，除非用户要求保留。",
        "临时 instrumentation，以及 collector、日志和 root-cause 文档清理。",
        "有新运行时日志支撑的已验证修复。",
      ],
      guardrails: [
        "不要在没有运行时证明的情况下交付猜测性修复。",
        "除非证明直接 collector 投递被阻塞，否则不要创建 app-local proxy APIs 来转发浏览器日志。",
        "中间清日志时保留 root-cause 文档，最终成功清理时再删除，除非用户要求保留证据。",
      ],
      entryPoints: [
        { description: "证据优先调试序列和清理要求。", label: "工作流" },
        { description: "Collector bootstrap、日志格式和调试说明。", label: "运行时参考" },
        { description: "演进式证据文档结构。", label: "Root-cause 参考" },
        { description: "本地 NDJSON collector 和 dashboard 实现。", label: "Collector" },
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
      lead: "一个 coverage-led 审计，用于发现破坏或退化的用户路径、默认值变化、陈旧数据和可见行为变化。",
      overview:
        "当一个变更集需要用户可见行为门禁时使用此 skill。它审查声明范围，把有意可见变化与回归分开，并写出报告，将每个触及 surface 标记为 reviewed、intentional、not covered 或 not relevant。",
      bestFor: [
        "检查重构或功能工作是否破坏了用户可见流程。",
        "审计 loading、error、permission、retry、ordering、export、email 或 CLI-output 变化。",
        "产出 severity 与最强未解决 finding 对齐的审查 artifact。",
      ],
      workflow: [
        "设定或推断审查范围，并在可用时阅读需求。",
        "在判断行为前映射触及的用户可见 surfaces。",
        "把当前行为与基线、意图和用户期望对比。",
        "写出所有不同 findings，而不是只写前几个。",
        "在 coverage ledger 中记录有意可见变化和未覆盖 surfaces。",
      ],
      outputs: [
        "一份 Markdown regression-review report。",
        "与 findings 和 coverage 对齐的 gate recommendation。",
        "完整 findings index 和 coverage ledger。",
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
        "在收到 regression-review 报告或相关 PR feedback 后使用此 skill。它会在编辑前用当前代码验证每个 finding、有意可见变化和 coverage gap，然后修复已证明的回归，并用证据挑战过时或有意的 findings。",
      bestFor: [
        "用当前 diff 和基线重新检查 regression gate。",
        "只修复已证明的用户可见回归。",
        "把真实回归与有意产品变化分开。",
      ],
      workflow: [
        "阅读报告并列出每个 finding、有意变化和未覆盖 surface。",
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
