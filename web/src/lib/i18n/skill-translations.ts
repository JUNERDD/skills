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
        "当代码库需要激进但有纪律的简化时使用此 skill。它会建立行为保持 oracle，审计可删除代码，并穷尽测试删除和简化候选项。仅审计的请求止于建议；实施沿用已批准范围，只为尚未决定的架构问题准备具体选项。该 skill 仅支持显式调用：用户必须使用 `$exhaustive-code-slimmer` 调用；仅凭提示词匹配不会自动激活。",
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
        "当安全瘦身涉及尚未决定的设计或范围时，给出具体架构选项。",
      ],
      guardrails: [
        "不要把压缩、混淆、纯空白删除或注释删除算作代码瘦身。",
        "没有证据时不要删除公共 API、迁移、兼容 shim、安全检查、运维日志或配置。",
        "架构变更须处于已批准范围内；已有授权贯穿候选评估和验证，不重复审批。",
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
        "当团队在代码、库、服务、模板、文档、平台流程或架构决策上重复造轮子时使用此 skill。它结合已有资产检索、重复类型分类、build-vs-reuse 评分、迁移规划和 catalog 脚本。审计与规划只交付证据和建议；整合、资产目录和持续治理按用户要求的交付范围开展。",
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
        "推荐干预方式；仅在交付范围包含这些工作时，补充共享资产、目录指引和持续指标。",
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
    "composable-components": {
      category: "组件架构",
      blurb: "构建公共 Part 真正可配置的 React 复合组件 API。",
      lead: "一套自包含的组件创作契约，用于构建公共接缝诚实的无障碍 primitive 与产品 composer。",
      overview:
        "在创建或重构 React compound component、数据驱动 Part、多态宿主元素或其私有文件布局时使用此 skill。它明确规定调用方数量不影响契约质量：即使当前只有一个生产调用方，公共 Part 仍必须可达，原生 props 与 ref 必须透明，事件与样式必须可组合，状态所有权必须清晰，而组件拥有重复数据时必须提供真实的渲染边界。",
      bestFor: [
        "设计带受控状态、语义 Part、asChild、焦点、键盘和 ARIA 契约的 Radix 风格 primitive。",
        "构建视觉 Part 不依赖具体 store 或同步实现的产品 compound component。",
        "让集合 Item、空状态、Trigger 与 Content 区域无需复制内部行为即可替换。",
        "用职责明确的下划线目录组织组件本地私有文件。",
      ],
      workflow: [
        "先判断 primitive 与 product 行为，再决定重复数据迭代归消费者还是组件所有。",
        "根据状态、数据、语义、内容、样式、交互和集成职责确定公共接缝，而不是根据当前调用方数量。",
        "定义会在缺失 owner 时抛错的 Context 边界，以及合适的受控或 Provider 驱动状态契约。",
        "让每个公共宿主 Part 透明传递 props 与 ref，明确组合事件和样式，并暴露稳定状态属性。",
        "移除 child type 发现、静默丢弃 children，以及让导出 Part 无法触达的固定嵌套默认实现。",
        "应用私有目录分类，并在完成前验证至少一种有意义的替代排列或渲染器。",
      ],
      outputs: [
        "一个所声明 Part 均可直接使用或通过显式边界替换的 compound namespace。",
        "类型化的状态、Item 渲染、宿主 props、无障碍和元素替换契约。",
        "最小私有目录布局，以及所声明组合接缝确实可用的证据。",
      ],
      guardrails: [
        "不要因为只有一个生产调用方就降低 API 质量，也不要为了显得可复用而臆造配置。",
        "不要导出会被便利 facade 永久替换为内部副本的装饰性 Part。",
        "不要把 child.type 身份扫描、只取第一个匹配项或静默丢弃 children 当作组合协议。",
        "不要让样式 hooks 取代语义 HTML、键盘行为、焦点管理或 ARIA。",
        "保持 skill 自包含；它的组合决策不能要求预先安装其他 skills。",
      ],
      entryPoints: [
        { description: "分类、核心决策、创作清单和完成门槛。", label: "工作流" },
        {
          description: "与调用方数量无关的质量、Part 可达性、数据渲染、状态、宿主 props 和无障碍规则。",
          label: "组合契约",
        },
        { description: "私有下划线目录职责、命名、树形结构、导入和紧凑布局指导。", label: "目录布局" },
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
    "github-context7-research": {
      category: "依赖库研究",
      blurb: "用源码与变更历史验证第三方库文档。",
      lead:
        "一个版本感知的证据工作流，用只读 GitHub 源码、测试和变更历史核对 Context7 公共文档。",
      overview:
        "当编码决策依赖外部库、SDK 或框架的精确 API 或行为时，使用这个可隐式自动调用的 skill。它会解析库与目标版本，通过 Context7 建立受支持的公共契约，把 GitHub 证据映射到同一发布版本，并区分文档用法、实现细节、测试以及 Issue 或 PR 的历史上下文。",
      bestFor: [
        "针对当前版本或项目锁定版本实现外部依赖接入。",
        "诊断公共文档未充分解释的运行时行为。",
        "检查 API 变化、回归、Bug workaround 和发布历史。",
        "用公共文档、精确 ref 源码和聚焦测试验证建议。",
      ],
      workflow: [
        "从用户输入或消费项目中识别包、规范仓库、具体问题和目标版本。",
        "解析 Context7 library ID，并只查询该版本与问题所需的公共文档。",
        "把包版本映射到不可变的 GitHub tag 或 commit，而不是静默使用默认分支。",
        "检查公共导出、类型、实现、测试和示例，只在需要时补充 release、commit、Issue 或 PR。",
        "核对两组证据，并把受支持用法与观察到的内部实现、历史上下文和 workaround 分开报告。",
      ],
      outputs: [
        "基于受支持公共契约的直接实现或诊断建议。",
        "用于验证的 Context7 library ID 与版本，以及 GitHub 仓库 ref 或 commit。",
        "对证据一致、冲突、版本映射未决、证据缺口和推断的明确说明。",
      ],
      guardrails: [
        "GitHub MCP 只用于只读研究；隐式调用永远不授权仓库写操作。",
        "不要把版本化文档与无关分支或发布版本的源码静默比较。",
        "不要把私有、生成、弃用、兼容层、测试专用或 feature-flagged 内部 API 推荐为公共 API。",
        "不要向 Context7 发送凭证、私有源码、专有标识符或个人数据。",
      ],
      entryPoints: [
        { description: "版本匹配、证据路由、核对、报告和只读 guardrails。", label: "工作流" },
        { description: "GitHub 与 Context7 MCP 依赖及隐式调用策略。", label: "运行时元数据" },
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
        "当无关事项、重构、行为变化、生成文件或可分离 hunk 混在一起时使用此 skill。它规划逻辑批次，一次 stage 一个批次，并调用 `git-commit` 生成消息。用户授权可以覆盖单个批次或整轮提交；仅在尚未授权时，对准备好的批次请求确认，并遵守用户要求的逐批确认。",
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
        "调用 `git-commit` 并展示 staged 摘要和消息；已有授权覆盖该批次时继续提交，否则请求确认。",
      ],
      outputs: [
        "一组聚焦 commits 的建议顺序。",
        "一次一个 staged 批次，并配套 Conventional Commit 草稿。",
        "在用户明确授权的批次或提交序列内创建本地 commits。",
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
      blurb: "通过层级化任务与决策所有权协调多步骤工作。",
      lead:
        "一个层级协调器：分配任务、决策和写入所有权，保护 worker 上下文，路由冲突并验证集成结果。",
      overview:
        "用于需要协调并行或依赖工作流的非平凡多步骤任务。显式调用后，root parent 构建任务与决策图，为每个重大决策域和写入边界分配唯一 owner，仅为可独立分解的子树任命有界 subplanner，在层级或上下文交接需要共享记忆时使用有所有权且单写者的临时实体文档，以事件驱动方式调度就绪工作、路由冲突，并保留最终集成与清理所有权。该 skill 仅支持显式调用：用户必须使用 `$multitask-coordinator` 调用；仅凭提示词匹配不会自动激活。",
      bestFor: [
        "通过显式任务与决策图协调并行和依赖工作流。",
        "把独占决策域委派给容量与范围受限的递归 subplanner。",
        "需要时通过有所有权且单写者的临时实体文档共享已接受决策和 handoff。",
        "在大型仓库或迁移中防止决策脑裂、过期契约和重叠写入。",
        "在已验收结果解锁依赖工作时保持健康 worker 不被打断。",
        "审计层级编排中的所有权漂移、失控递归、争用或验证缺口。",
      ],
      workflow: [
        "框定根规格，并在派发 writer 前读取适用规则和 dirty state。",
        "构建带依赖、owner、稳定输入、范围、证据和验收标准的任务与决策图。",
        "仅在层级、上下文交接或重复发现确有需要时创建一个有所有权的临时共享记忆根目录。",
        "让当前 planner 保留小型或紧耦合工作；仅为独占且可分解的子树任命 subplanner。",
        "冻结已消费的决策和契约，再在所有权、隔离和集成容量内派发有用的就绪工作。",
        "增量检查终态证据，按类型路由冲突，并在验收后立即解锁依赖项。",
        "在 root parent 所有权下验证集成结果、决策一致性和剩余风险。",
      ],
      outputs: [
        "一份带明确层级、依赖、决策 owner 和写入边界的任务与决策图。",
        "一个可选的 marker-owned 临时记忆根目录，包含精确路径且每份文档只有一个 writer。",
        "带委派权限、稳定输入、范围、证据和验证要求的 subplanner 与 worker 合同。",
        "对已验收工作、冲突路由、过期输入、阻塞点、剩余风险和最终验证的证据化综合。",
      ],
      guardrails: [
        "在仓库规则、dirty state、决策所有权和写入所有权明确前，不要派发 writer。",
        "不要为同一重大决策域或共享写入边界分配多个 owner。",
        "不要让普通 worker 继续委派；只有明确任命的 subplanner 才能获得后代容量和范围。",
        "不要扫描、广泛注入、并发编辑或不安全删除临时共享记忆文档。",
        "不要取消、重启、改派健康 worker，或向其发送未经请求的 follow-up。",
        "没有审查改动文件、产物、命令输出或其他具体证据前，不要把 worker 输出当作事实。",
      ],
      entryPoints: [
        { description: "层级任务与决策所有权、冲突路由、健康 worker 连续性、综合和验证规则。", label: "工作流" },
        { description: "磁盘协调记忆的位置、所有权、内容、保留和安全清理规则。", label: "临时共享记忆" },
        { description: "层级调度、决策一致性和编排有效性的指标与场景。", label: "调度审计" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "plan-mode": {
      category: "规划",
      blurb: "创建带代码引用和待办事项的可编辑实施计划。",
      lead:
        "一个规划工作流，用可编辑 Markdown 计划记录代码引用、待办事项及规划或实施范围。",
      overview:
        "当用户要求规划、保存计划文件，或以架构和方案权衡分析为交付物时使用此 skill。它创建可编辑 Markdown 计划，研究具体代码引用，解决关键问题，并维护可执行待办。只要求规划时停在实施之前；已经要求规划并实施时沿用已有授权继续。任务复杂或涉及多文件本身不会触发新的批准流程。用户要求访谈，或存在适合追问的关键未决选择时，再使用 `grill-me`。",
      bestFor: [
        "在编辑前规划多文件实现、架构、路由、数据流或权衡较多的工作。",
        "维护包含文件引用、代码引用和复选框待办的 Markdown 计划。",
        "使用 `grill-me` 开展用户要求的访谈或澄清关键未决选择。",
        "为 dirty worktree、迁移、设置、部署、生成代码或其他高影响面保持严格边界。",
        "在已有授权范围内实施全部或选定待办，或交付仅规划的结果。",
      ],
      workflow: [
        "判断请求仅限规划还是已授权实施，然后创建或复用 Markdown 计划并提供路径。",
        "研究必要信息，把具体文件、代码引用、约束和未决问题写入计划。",
        "仅在未决选择会实质改变计划时提问，并在收到回答后更新文件。",
        "维护可编辑的复选框待办，以便之后选择和实施。",
        "结合证据检验假设；用户要求访谈或存在关键未决选择时再使用 `grill-me`。",
        "校验并概述计划，按请求交付规划结果，或直接实施已授权待办并完成相关检查及仓库必需门禁。",
      ],
      outputs: [
        "包含代码引用、可编辑待办及准确授权状态的 Markdown 计划。",
        "需要访谈时生成的 `grill-me` 记录和规划结果文件路径。",
        "当歧义会改变计划时，提出聚焦澄清问题。",
        "计划到实施的交接，或完成已授权实施并进行相称验证。",
      ],
      guardrails: [
        "仅规划阶段只允许写计划及 `grill-me` 记录或结果，不编辑实现、安装包、启动服务或修改 Git 状态。",
        "不要把未解决的产品、数据、安全或架构假设藏在最终计划里。",
        "实施前重读计划并确认授权覆盖全部还是选定待办；已有授权覆盖的工作无需再次请求批准。",
      ],
      entryPoints: [
        { description: "规划边界、工作流、澄清规则和交接要求。", label: "工作流" },
        { description: "创建并校验 Markdown 计划文件。", label: "计划文件助手" },
        { description: "生命周期、模式边界、研究策略、图示和常见失败模式。", label: "架构参考" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    debug: {
      category: "运行时调试与修复",
      blurb: "用丢失与序列缺口可审计的证据证明、修复并验证运行时 bug。",
      lead:
        "一个 coverage-first 调试与修复系统，提供可机器校验的原生断点与探针计划、丢失与序列缺口可审计的运行时证据、持续演进的调查账本，以及独立的修复后验证。",
      overview:
        "当只读代码不足以证明问题，且运行时 bug 需要从失败契约一路跟进到已验证修复时使用此 skill。它构建有代码依据的因果图，为每个 material hypothesis 同时记录确认与否定证据，并校验包含 attached/unavailable/unsafe 调试器策略、initial/deferred 断点批次、结构化探针以及 terminal 或 observation-checkpoint 完成模式的 coverage plan。原生调试器已连接且暂停安全时，agent 会在执行前一次性安装全部安全、非冗余的首批断点，而不是只下一个或两个断点逐步推进；暂停不安全或调试器不可用时，仍会保留完整候选集并为每个延后断点记录结构化原因，同时改用经过校验的非暂停探针。collector 位置同步与 expected-probe 分析会复用同一计划。每个活动探针都采用固定的 all-occurrences/every-execution 契约：每个被接受的 occurrence 恰好形成一个独立序列化事件和一条持久化 NDJSON；多事件 envelope 只改变网络封装，不改变事件数。用户通过普通消息明确表示复现完成后，agent 会立即接管采集收尾与冻结，无需额外点击或手动 Stop/Freeze。若无法确认 checkpoint、producer 解绑或日志交付，则将已保存记录标为采集不完整，继续分析其中可用的证据，并保持记录冻结。运行时事件交付保持语言无关：优先复用项目或宿主已有 logger，其次使用目标语言的原生 HTTP 客户端；仅在不使用 collector 生命周期控制且具备安全写入所有权时，才直接追加 NDJSON。skill 不再向目标项目注入预设的 JavaScript transport。collector 只暴露 `POST /ingest`，接受单条事件或精确的 `{\"events\":[...]}` envelope，并提供收集、Freeze、Resume、Clear 和 Stop；重试、去重、envelope 身份、generation 与应用生命周期策略都留给目标项目。新建的本地图形环境会话仍会自动打开并确认 dashboard，实时列表、筛选、详情、IDE 源码打开、location sync 与配置交互全部保留。`FROZEN` 时新 ingest 会被拒绝且不会写入，但所有 dashboard 继续刷新，Clear 仍可用且不会恢复记录，所有标签页、刷新与后续分析轮次都会看到同一状态。相关 NDJSON 会先按 run 与实际需要的应用 correlation 字段摘要，再读取必要的原始事件。除非用户明确要求仅诊断，否则 debug、troubleshoot、fix、repair 或 resolve 请求会继续完成证据充分的修复、独立验证、账本收尾与清理。",
      bestFor: [
        "昂贵、偶发、时序敏感、破坏性、环境特定或只能由用户完成的复现。",
        "很容易猜测、但难以跨因果边界证明的运行时失败。",
        "需要在恢复执行前一次性安装广泛首批断点的原生调试器调查。",
        "在加入广泛临时 instrumentation 前需要确定性覆盖门禁的调查。",
        "需要父 flow、operation、request、attempt 和顺序证据的并发或分布式流程。",
        "按条件需要完整页面生命周期应用 fetch 捕获的浏览器调查。",
        "业务流有意保持打开的 SSE、WebSocket、subscription、long-poll 或 ReadableStream 故障。",
        "不能停在根因报告或未验证建议的端到端 bug 修复请求。",
      ],
      workflow: [
        "无需重复审批地确定范围：除非用户明确限制为仅诊断，否则 debug/fix 请求包含修复与验证；随后选择复现执行者，定义失败契约及 terminal 或有界观察条件，并检查相关执行路径。",
        "构建因果边界图，枚举有代码依据的 material hypothesis，并为每项定义确认与否定证据。",
        "创建并校验 coverage plan，确保调试器策略、首批与延后断点、边界、假设、探针、固定的 all-occurrences/every-execution 基数契约、结构化的 payload-only 边界、隐私检查和残余歧义一致；结构上拒绝任意层级的未知键，并通过强制语义审查拒绝过少的断点批次或试图覆盖 occurrence 策略的说明文本。",
        "原生调试器已连接且暂停安全时，在第一次 run/continue 前安装全部安全、非冗余的 initial 断点；若工具一次只能设置一个位置，则连续设置完再恢复执行。暂停后若暴露新的因果区间，也先一次性补齐该区间的断点再继续；暂停不安全时改用非暂停探针。",
        "从调查账本记录的精确 ready file 恢复日志会话；健康会话跨轮次与 run ID 复用同一 collector、dashboard、IDE 选择和 location 状态，不扫描工作区也不重复打开 UI。新建的本地图形环境会话仍自动尝试打开并确认 dashboard，明确无界面、CI、容器内或远程会话才显式关闭。",
        "对共享 causal cuts 与 invariants 插桩，选择项目 logger 或目标运行时原生 adapter；使用目标项目的模块系统逐一解析每条临时 helper 引用（slash 分隔的文件相对引用可选用路径助手），再通过原生解析、编译、collector、expected-probe 与事件基数门禁；上一轮冻结分析和下一轮准备完成后运行 `resume-recording`，要求 collector 为 live，并在每次请求用户复现前复制规范化的 `dashboard-status` 状态与 URL 行。",
        "收集一次 terminal 运行或有界观察窗口。结合上下文识别用户的完成消息后，agent 立即使用可用控制解绑 producer、完成日志写入并冻结 collector，再核对持久化记录。若无法确认 checkpoint、清理或交付，则记录采集不完整并分析已保存的证据，无需用户再执行结束动作；仅在分析发现影响因果证明或验证的证据缺口后，才请求新一轮复现。",
        "证明从起点到症状的传播链；若仍不足，只为最小未决因果区间补探针，并全程更新同一份调查账本。",
        "仅诊断时先保存证据并清理临时 instrumentation；否则把诊断视为中间结果，立即修复已证明的机制、独立验证并清理 owned artifacts。",
      ],
      outputs: [
        "一份包含调试器决策、广泛首批/延后断点批次与结构化探针，并由位置同步和 expected-probe 分析共同使用的机器可读 coverage plan。",
        "一条带引用的根因起点到症状证据链，或明确的最小未决因果区间。",
        "对于持续流，提供已持久化的有界源序列前缀 checkpoint 与源序列缺口报告，在不声称业务流结束的情况下闭合证据窗口。",
        "每个修复范围内、用户复现、多轮或需持久记录的调查都使用一份持续演进的账本。",
        "面向用户复现、证据分析和修复验证的交接采用易扫读的 Markdown，并以空行分隔标题与列表。",
        "修复范围内的任务会产出因果充分的代码变更，并由独立验证运行与确定性清理支撑。",
      ],
      guardrails: [
        "没有根因起点、传播和最终症状三段证据时，不要声称已证明根因。",
        "若仍有已知且安全、非冗余的首批位置，不要只设置一两个原生断点就恢复执行；应安装完整批次或逐项记录明确的延后理由。",
        "不要把仅暂停的断点当作 all-occurrence 结构化探针，也不要仅凭断点未命中就证明路径不存在。",
        "不要把原生调试器控制台 logpoint 当作完整证据；承担证据作用的 logpoint 必须同时是经过校验、并通过选定 runtime adapter 写入的结构化探针。",
        "临时 correlation header 可能改变 CORS、缓存、路由、签名、授权或产品行为时，不要添加它。",
        "不要把 dashboard 可见性当作证据，也不要让打开失败阻塞证据采集或复现。",
        "用户明确表示复现完成后，不要仅为结束采集要求额外点击、失焦、导航、DevTools 命令或 Dashboard Stop/Freeze。checkpoint instrumentation 应绑定到自然边界；应结合上下文理解消息，而非匹配固定词语。用户消息结束复现等待，运行时证据独立决定采集是否完整。",
        "不要把 collector 全局 `FROZEN` 当作健康故障、产品流程完成或持久化证明。优先解绑 producer 并完成日志写入后 Freeze；无法确认时仍由 agent 冻结已有记录，明确标注采集缺口。在分析与修复期间保持冻结，清理上一轮残留 producer，仅在下一轮准备完成且即将记录时 Resume。",
        "仅诊断任务不要实施修复，也不要保留仍让因果机制继续生效的较小 workaround。",
        "不要对任何活动探针 occurrence 做采样、节流、debounce、first-N、change-gate、once-per-key、聚合、合并、覆盖、去重或丢弃。",
        "不要要求目标项目导入预设的语言专用 transport，不要 fire-and-forget collector 写入，也不要假定 collector 会去重而自动重试结果不明确的请求。",
        "不要凭猜测生成相对 helper 引用，也不要在不同嵌套深度的 importer 之间复制同一引用；应先创建目标文件，并要求目标项目的原生 resolver 或 compiler 接受每条临时跨文件边。",
        "没有权威、持久的 producer-side logger 时，不要声称跨 reload、navigation、进程丢失、内存耗尽或存储耗尽不存在事件丢失；只能声明已确认的连续前缀，并明确生命周期丢失边界。",
        "不要在摘要前读取无界原始日志，也不要在成功清理后遗留临时 instrumentation 或 owned artifacts。",
      ],
      entryPoints: [
        { description: "Coverage-first 调试修复序列、完成边界、账本与清理要求。", label: "工作流" },
        { description: "因果图、material hypotheses、广泛首批断点批次、coverage plan 与复现门禁。", label: "覆盖规划" },
        { description: "Collector 启动、会话操作、结构化日志与清理。", label: "运行时参考" },
        { description: "浏览器原生 adapter 选择、长生命周期流 checkpoint、fetch 捕获与生命周期规则。", label: "浏览器参考" },
        { description: "增量证据与排除账本的结构。", label: "Root-cause 参考" },
        { description: "校验严格的调试器策略、断点批次、结构化探针与共享覆盖门禁，并在复现前失败关闭。", label: "覆盖校验器" },
        { description: "在 importer 与目标文件均已存在后，计算并校验 slash 分隔的文件相对 debug helper 引用；package、namespace 与 alias 仍由项目原生解析。", label: "文件相对 helper 解析器" },
        { description: "启动、确认、恢复和停止本地 collector 与仪表盘会话。", label: "会话助手" },
        { description: "在阅读原始体积前摘要 NDJSON 证据与事件连续性。", label: "日志摘要器" },
        { description: "本地 NDJSON collector 和 dashboard 实现。", label: "Collector" },
        { description: "会话、coverage-plan 同步、correlation 摘要、dashboard 与生命周期回归测试。", label: "生命周期测试" },
        { description: "调试器策略、断点批次、schema、映射、sentinel 与门禁校验回归测试。", label: "Coverage-plan 测试" },
        { description: "Message、event 名称、probe ID、空白与空状态摘要回归测试。", label: "Dashboard 摘要测试" },
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
    bugbot: {
      category: "代码审查",
      blurb: "持久化引入 Bug 报告，并识别报告修复意图。",
      lead:
        "一个两阶段本地 diff 审查器，提供持久 Markdown 报告与低摩擦、报告范围内的修复。",
      overview:
        "对本地 branch 或未提交改动执行窄范围 Bugbot 工作流时使用此 skill。检测会盘点 tracked 与 untracked 文件，递归追踪 diff 派生候选项直到有界固定点，并把每个已验证的生产 Bug 写入唯一 Markdown 报告；该报告是检测阶段唯一允许的写入。修复意图来自完整对话，也包括首次请求中的评审并修复授权。报告落盘后继续已授权修复，无需再次批准；只要求评审时停在报告。修复意图明确且没有更窄范围时，选择最新无歧义报告中的全部未解决 findings；具体语义指代可以选择子集。运行相关及必需检查，不静默处理不同的新 findings，也不改变 Git 发布状态。",
      bestFor: [
        "针对仓库默认分支或指定 base 审查当前 branch work。",
        "针对 HEAD 审查 staged、unstaged 与 untracked 本地改动。",
        "生成不限 finding 数量的持久报告，再根据上下文识别的意图修复全部或选定 findings。",
      ],
      workflow: [
        "解析仓库、比较模式、baseline、tracked diff 与 untracked 文件清单。",
        "从每个 changed hunk 与 untracked 文件建立候选前沿。",
        "只沿与改动有因果关系的控制流、依赖、契约、状态和失败路径追踪候选项。",
        "持续加入新暴露的 diff 相关风险直到固定点，再按根因验证和去重。",
        "把每个已验证 finding 写入带稳定报告内 ID、证据、coverage 与 recommendation 的唯一 Markdown 报告。",
        "报告落盘后沿用首次请求或后续对话中的修复授权，重新验证选定 findings，完成针对性及必需检查，避免无依据重复验证。",
      ],
      outputs: [
        "一份持久 Markdown 报告，包含每个引入生产 Bug 的 finding card 与完整索引。",
        "完整审查无 Bug 时的明确 clean report，或列出精确 coverage gaps 的 incomplete report。",
        "修复后的 Markdown 摘要，包含验证结果与仍未确认的问题。",
      ],
      guardrails: [
        "检测期间只写报告 artifact；不要编辑被审查源码或 Git 状态。",
        "只为 Bugbot 请求启动新检测；隐式路由用于报告跟进，而不是普通 code review。",
        "从当前及之前的用户指令识别修复意图，保留只评审的范围；只有意图、报告或 finding 范围仍存在关键歧义时才询问。",
        "不要限制 findings 数量，也不要在最高严重度或最容易的问题后停止。",
        "不要把递归前沿扩展到与被审查改动没有因果关系的路径。",
        "不要 stage、commit、push、deploy，或在没有单独请求时修复不同的新 findings。",
      ],
      entryPoints: [
        { description: "阶段路由、上下文修复意图识别、递归检测和报告持久化。", label: "工作流" },
        { description: "标准 Markdown 报告、finding cards、coverage ledger、证据与自检。", label: "报告模板" },
        { description: "确认解析、有范围修复、验证与停止规则。", label: "修复工作流" },
        { description: "此 skill 的可选 agent 运行时元数据与自动调用策略。", label: "运行时元数据" },
      ],
    },
    "code-review": {
      category: "代码审查",
      blurb: "执行以产品依据为准、具备有界报告血缘的深度审查。",
      lead:
        "一个冻结范围的深度审查工作流：要求权威 expected-behavior 依据、稳定问题指纹，并把实现后复审限制为终止 generation。",
      overview:
        "当用户请求 `/code-review`、PR/diff/branch/staged review 或 merge 前安全检查时使用此 skill。它先由协调者评估编排，仅在独立分析或并行覆盖有实质收益时委派，并冻结初审范围，追踪可传播风险，在把产品选择判为 defect 前要求权威产品或契约证据，并为问题生成确定性的语义指纹。receiving 最多可生成一次仅覆盖实现 delta 与受影响执行链的 generation-1 复审；该报告是终点，不能自动再启动 receiving。该 skill 仅支持显式调用：用户必须使用 `$code-review` 调用；仅凭提示词匹配不会自动激活。",
      bestFor: [
        "审查 PR、branch diff、staged changes、working tree、聚焦文件或 pasted code。",
        "判断并行 specialist subagents 何时能实质提升审查价值。",
        "在 merge 前发现正确性 bug、release-blocking regression、安全问题、契约风险和缺失测试。",
        "区分已验证 defect、未确认产品意图与已裁决产品决策。",
        "产出包含 coverage、语义问题血缘和有界 receiving handoff 的可复用 artifact。",
      ],
      workflow: [
        "先确定 review chain generation、冻结范围，并记录 baseline、target、需求与最小 diff inventory。",
        "由协调者或有明确价值的只读 assessor 评估范围与风险，再执行单 reviewer 或 specialist 计划。",
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
        "review 阶段保持只读；用户也已授权 fixes 时，先完成报告再继续修复。",
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
        "在收到 `code-review` 报告或等价 PR feedback 后使用此 skill。分配 disposition 前，它先从真实触发与入口出发，经过 guards、控制/数据/状态传播、持久化与外部效应、失败语义，一直追踪到终端影响。它跨 generation 继承匹配的 Intentional、Disproved、Stale 和 Duplicate 裁决；链路或产品权威证据不完整时禁止修复；由协调者或有明确价值的委派执行状态相容的已确认动作；仅在确认仍适用后复用已有证据；把相邻的新发现作为 provisional residual 返回；初审链最多运行一次终止 post-review，且不自动消费其 findings。该 skill 仅支持显式调用：用户必须使用 `$receiving-code-review` 调用；仅凭提示词匹配不会自动激活。",
      bestFor: [
        "在改代码前，针对完整端到端执行链重新验证每个 `F#`、`T#` 和未覆盖的 `A#`。",
        "用证据正式挑战错误、夸大或过时的 review 主张。",
        "按工作范围选择实现负责人，修复已确认的正确性、安全、契约或测试问题。",
        "除非代码、契约或实质证据变化，否则保护权威产品意图不被重新打开。",
        "在未请求发布时保留 staged 工作，并让新修复保持 unstaged。",
      ],
      workflow: [
        "阅读完整 source review，或把非结构化反馈规范化为稳定 item IDs。",
        "捕获血缘与 Git 状态，建立当前 EC# 端到端执行链，并评估委派是否有实质价值。",
        "针对完整执行链和 expected-behavior 权威性验证每项，并分配相容的 verdict、action 与 implementation state。",
        "由协调者或有明确价值的 coding 委派实现已确认修复，并给出明确所有权与 no-staging 约束。",
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
        "按风险与执行收益选择委派；协调者直接实现同样需要条目所有权和当前验证证据。",
        "除非当前请求明确要求，否则不要 stage、commit 或改变 Git index。",
        "在每个 source item 都有 disposition、每个已实现 item 都有针对性验证前，不要声称已解决。",
        "不要静默丢弃或自动实现 verifier 发现的独立问题；应把它们作为 provisional residual candidates 返回。",
        "不要自动修复 blocked chain 或未确认产品选择，也不要从终止 post-review 自动开启下一轮 receiving。",
      ],
      entryPoints: [
        { description: "重新审查、挑战、实现所有权和 Git index 保留规则。", label: "工作流" },
        { description: "评估协议与 specialist 重新审查指导。", label: "重新审查编排" },
        { description: "标准 receiving-code-review resolution report 形状。", label: "Disposition 模板" },
        { description: "校验执行链、血缘继承、状态相容和单次 review 预算。", label: "Disposition 校验器" },
        { description: "覆盖执行链优先 disposition 与有界后续的回归测试。", label: "校验器测试" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "thermo-review": {
      category: "代码审查",
      blurb: "输出严格的结构质量评审报告。",
      lead: "聚焦职责拆分、文件膨胀、抽象边界和复杂度增长的结构质量门禁。",
      overview:
        "用此 skill 进行严格的可维护性评审。它输出 Markdown 报告，以 350 行作为分析内聚性、依赖和职责归属的触发信号，并持续检查结构候选项，直到覆盖完整或明确记录缺口。仅评审时止于报告；已授权的修复在保留报告后继续。该 skill 仅支持显式调用：用户必须使用 `$thermo-review` 调用；仅凭提示词匹配不会自动激活。",
      bestFor: [
        "评估改动是否让实现更加纠缠、膨胀、间接或难以扩展。",
        "发现遗漏的简化机会、内聚职责拆分、职责归属调整和类型边界改进。",
        "产出包含问题、递归覆盖、行数证据和剩余盲点的持久报告。",
      ],
      workflow: [
        "设定评审范围和基线；未指定时优先暂存改动，再考虑工作区。",
        "整理差异和行数；对超过 350 行的候选文件分析职责、依赖边界和规范所有者。",
        "从文件增长、分支、辅助函数、抽象、类型、所有权、编排、测试和重复代码中建立候选集合。",
        "结合局部流程、调用点、契约、测试和已有规范实现，向内外追踪每个候选项。",
        "继续纳入新发现的简化候选项，直到没有新增项或明确记录未覆盖部分。",
        "保留包含问题、拆分缺口、覆盖和证据的报告，再按用户要求结束评审或继续修复。",
      ],
      outputs: [
        "一份 Markdown 结构质量评审报告。",
        "包含建议、完成状态、严重度统计和主要结构风险的简洁总结。",
        "递归覆盖记录、行数记录、候选检查日志和质量门禁建议。",
      ],
      guardrails: [
        "评审阶段保持只读；报告完成后的修复遵循已有用户授权。",
        "不要把测试通过当作结构合理的证明。",
        "不要静默豁免超过 350 行的结构候选项；说明职责边界或记录覆盖缺口。",
        "不要用密集排版、任意搬移或其他只降低行数的手段解决阈值问题。",
        "主要问题是正确性、安全、隐私、数据丢失或合并风险时，使用 `code-review`。",
      ],
      entryPoints: [
        { description: "结构评审、覆盖和交接规则。", label: "工作流" },
        { description: "结构问题、递归覆盖和行数证据模板。", label: "报告模板" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "receiving-thermo-review": {
      category: "代码审查后续",
      blurb: "验证并处理严格的结构评审反馈。",
      lead: "用当前证据处理结构反馈，避免盲目重构和行为回归的响应流程。",
      overview:
        "用此 skill 处理 thermo 报告或结构反馈。它逐项处理问题、拆分、覆盖和行数证据，检查行为一致性，并验证职责内聚性后再处理阈值问题。过期项单独核对，独立且已授权的修复可以继续；原始报告和无关 Git 状态会保留。有必要时只对受影响改动复审。该 skill 仅支持显式调用：用户必须使用 `$receiving-thermo-review` 调用；仅凭提示词匹配不会自动激活。",
      bestFor: [
        "结合当前差异、行数、调用点和职责归属验证结构问题。",
        "通过职责和依赖分析处理 350 行问题，以及拆分、递归覆盖和候选检查事项。",
        "在指定范围内实施简化，同时验证输入、保护条件、输出和扩展点的行为一致性。",
      ],
      workflow: [
        "阅读可用报告、用户期望、已批准范围、基线和当前代码。",
        "根据问题、拆分缺口、递归覆盖、行数、候选检查和盲点建立处理记录。",
        "逐项核对过期或不一致的证据，只阻塞依赖它的编辑，并保留未解决的覆盖缺口。",
        "为阈值问题分析职责和依赖，在已批准边界内选择内聚的解决方案。",
        "给出简洁的行为一致性与验证计划，然后继续已授权工作。",
        "优先处理确认的阻塞项，同时解决独立事项，记录有证据的豁免和后续处理决定。",
        "重算受影响行数，执行针对性验证和必需检查，报告剩余问题，不递归启动评审循环。",
      ],
      outputs: [
        "覆盖所接收 thermo 报告事项的完整处理记录。",
        "范围明确的结构修复，或有证据的质疑、豁免和后续处理决定。",
        "受影响部分最新的行数、覆盖和行为一致性状态。",
      ],
      guardrails: [
        "不要盲目执行结构评审反馈。",
        "没有批准范围时，不启动广泛的架构重构。",
        "不要把行数降低、密集排版或搬入杂项模块当作阈值问题已解决。",
        "不要用结构清理掩盖潜在的用户可见回归。",
        "保留已有暂存内容；Git 操作遵循用户针对本任务的具体授权。",
        "所有问题、拆分缺口、阈值事项和开放覆盖项都有处理结果后，才能声明门禁已解决。",
      ],
      entryPoints: [
        { description: "结构反馈处理、行为一致性和验证规则。", label: "工作流" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "hack-review": {
      category: "代码审查",
      blurb: "审查实现是否依赖脆弱的 hack-like 捷径。",
      lead: "一个 coverage-led 审计，用于发现结构性捷径、所有权泄漏、被掩盖的根因和脆弱边界处理。",
      overview:
        "当变更需要实现质量门禁时使用此 skill。它审查声明范围，枚举不同 hack 风险，保护合理例外，并记录所有权覆盖。未指定范围时优先检查暂存改动，否则比较工作区与 HEAD。仅评审时止于报告；已授权的修复在保留报告后继续。该 skill 仅支持显式调用：用户必须使用 `$hack-review` 调用；仅凭提示词匹配不会自动激活。",
      bestFor: [
        "发现会隐藏破坏性不变量的 impossible-state fallback。",
        "标记没有解决根因的 symptom-masking patch。",
        "捕捉重复抽象、硬编码特例和边界绕过。",
      ],
      workflow: [
        "先设定审查范围；未指定时优先检查暂存改动，否则说明采用工作区与 HEAD 对比。",
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
        "用此 skill 处理 hack-review 报告或等价反馈。它验证当前所有权，逐项处理问题、有意例外和覆盖缺口，单独核对过期项，并继续已授权的独立修复。必要的外部输入保护、原始反馈和无关工作会保留；有必要时只对受影响改动复审，避免递归循环。该 skill 仅支持显式调用：用户必须使用 `$receiving-hack-review` 调用；仅凭提示词匹配不会自动激活。",
      bestFor: [
        "验证每个 hack-risk finding 在当前 diff 中是否仍成立。",
        "修复所有权问题，同时不机械删除必要 guard。",
        "关闭或延续 `Not covered` 所有权边界。",
      ],
      workflow: [
        "阅读报告和用户期望，保留原始反馈，并枚举问题、例外和覆盖缺口。",
        "逐项验证当前所有权和意图，核对过期反馈，不阻塞独立且已确认的工作。",
        "建立 disposition ledger：fix、disprove、narrow、confirm 或 carry forward。",
        "实施已授权修复并针对性验证，保留真实外部输入保护和范围明确的例外。",
        "报告每项处理结果和未解决的门禁问题；仅在有必要时复审，不递归启动接收流程。",
      ],
      outputs: [
        "覆盖整份报告的 disposition ledger。",
        "针对已确认条目的有证据代码修改。",
        "disproven、narrowed、intentional 和 carried-forward 条目的总结。",
      ],
      guardrails: [
        "不要机械执行报告。",
        "保留已有暂存内容；Git 操作遵循用户针对本任务的具体授权。",
        "用证据或更窄的修复处理技术风险；仅在缺少用户决策或新增范围授权时询问。",
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
        "当变更需要用户可见行为门禁时使用此 skill。它区分有意变化和回归，记录问题与覆盖情况，并在图能澄清路径时使用局部行为图。简单路径可直接追踪并对比输出。仅评审时止于报告；已授权的修复在保留报告后继续。该 skill 仅支持显式调用：用户必须使用 `$regression-review` 调用；仅凭提示词匹配不会自动激活。",
      bestFor: [
        "检查重构或功能工作是否破坏了用户可见流程。",
        "审计 loading、error、permission、retry、ordering、export、email 或 CLI-output 变化。",
        "追踪发生变化的 input、guard、transform 和 output，而不是构建全仓调用图。",
        "产出 severity 与最强未解决 finding 对齐的审查 artifact。",
      ],
      workflow: [
        "设定或推断审查范围，并在可用时阅读需求。",
        "在判断行为前映射触及的用户可见 surfaces。",
        "用直接证据追踪行为变化；当分支、副作用或所有权变化需要图示时，构建局部行为图。",
        "把当前行为与基线、意图和用户期望对比。",
        "写出所有不同 findings，而不是只写前几个。",
        "在 coverage ledger 中记录有意可见变化和未覆盖 surfaces。",
      ],
      outputs: [
        "一份 Markdown regression-review report。",
        "与 findings 和 coverage 对齐的 gate recommendation。",
        "完整问题索引和覆盖记录，以及有助于解释路径的行为图差异。",
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
        "用此 skill 处理回归报告或相关反馈。它根据当前行为和产品要求验证问题、图示证据、有意变化和覆盖情况，逐项核对过期反馈，并继续已授权的修复。已确认的产品行为和原始反馈会保留；有必要时只对受影响改动复审，避免递归循环。该 skill 仅支持显式调用：用户必须使用 `$receiving-regression-review` 调用；仅凭提示词匹配不会自动激活。",
      bestFor: [
        "用当前 diff 和基线重新检查 regression gate。",
        "把 behavior graph deltas 与 findings 和 coverage rows 对齐。",
        "只修复已证明的用户可见回归。",
        "把真实回归与有意产品变化分开。",
      ],
      workflow: [
        "阅读报告和用户期望，保留原始反馈，并列出问题、有意变化和未覆盖部分。",
        "把 behavior graph deltas 与当前代码路径和 coverage ledger 对齐。",
        "逐项验证当前路径和产品意图，核对过期反馈，不阻塞独立修复。",
        "编辑前建立 disposition ledger。",
        "在已有授权范围内修复确认的回归，运行针对性验证和仓库要求的检查。",
        "报告每项处理结果和未解决的门禁问题；返回必要复审的剩余发现，不递归启动接收流程。",
      ],
      outputs: [
        "完整 disposition ledger。",
        "针对已确认用户可见回归的有范围修复。",
        "challenged、narrowed、intentional 和 carried-forward 条目的证据。",
      ],
      guardrails: [
        "不要盲目应用 review feedback。",
        "保留已有暂存内容；Git 操作遵循用户针对本任务的具体授权。",
        "解决聚焦 regression finding 时，不要扩大用户可见行为。",
      ],
      entryPoints: [
        { description: "Disposition ledger 和 regression-response 要求。", label: "工作流" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
    "artifact-template-soft-focus-color-haze": {
      category: "图像生成",
      blurb: "用全新构图创作克制的抽象柔焦色雾图像。",
      lead: "一个感知输出模式的图像生成模板，用于创作细颗粒柔色场与暧昧失焦主体。",
      overview:
        "使用此 skill 以 Soft-Focus Color Haze 的视觉语言创作新图像，而不复制两份保留参考图中的主体或布局。它会为纯背景与主体引导请求选用独立参考，以宽阔低频色彩体积构图，并保持安静留白、哑光颗粒与清晰冷暖分离。",
      bestFor: [
        "生成色彩动势克制、留有安静低细节区域的全出血抽象背景。",
        "将提供的图像或指定主体转化为半抽象、柔焦的色彩存在。",
        "生成在位置、裁切、流向与留白方向上都有明显差异的变体。",
        "在不依赖锐利轮廓、硬阴影或写实材质细节的情况下保持主体与色场分离。",
      ],
      workflow: [
        "从 skill 包中解析标准背景参考与专用主体风格参考。",
        "将每个输出分类为纯背景或主体引导，并保持两种模式互不污染。",
        "只选一份与模式匹配的风格参考，将其作为视觉语言证据，而不是编辑目标。",
        "主体引导输出必须先依据用户指定或明确随机构图卡锁定位置。",
        "从宽阔柔焦色彩体积开始生成，再检查抽象度、色彩分离、位置、颗粒以及对参考布局的独立性。",
      ],
      outputs: [
        "一张使用 Soft-Focus Color Haze 视觉语言全新构图的全出血图像。",
        "不暗示焦点物体或可识别图案的纯背景图像。",
        "除非明确要求可读性，否则语义种子保持暧昧的主体引导图像。",
        "当请求多个输出时，生成构图明显不同的变体。",
      ],
      guardrails: [
        "不要复制保留参考图的主体、几何、精确色值、裁切或空间排列。",
        "除非用户明确要求比较或融合，不要同时传入两份模板参考。",
        "不要先构建写实物体再模糊；从一开始就应用失焦色彩平面构建图像。",
        "不要让主体融入背景、在缩略图尺寸立即变得写实，或偏离锁定位置。",
      ],
      entryPoints: [
        { description: "模式路由、风格语法、构图卡、对比门禁与视觉 QA 规则。", label: "工作流" },
        { description: "标准背景参考与预览图路径。", label: "模板元数据" },
        { description: "纯背景生成的风格参考。", label: "背景参考" },
        { description: "主体引导生成的风格参考。", label: "主体参考" },
        { description: "此 skill 的可选 agent 运行时元数据。", label: "运行时元数据" },
      ],
    },
  },
};

export function getSkillTranslation(slug: string, locale: Locale) {
  return skillTranslations[locale]?.[slug];
}
