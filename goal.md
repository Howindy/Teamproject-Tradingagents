# CS5351 项目目标、交付规范与 Agent 执行约束

依据：`CS5351-2026-2027-project.pdf`（10 页，以下简称 P）和 `cs5351-2026-2027-introduction.pdf`（27 页，以下简称 I）。本文供人工审阅项目范围、交付物和验收证据，同时为执行项目的 agent 提供方向与约束。文中的“必须/不得”表示项目要求或执行约束；“建议/示例”表示尚未批准的参考做法。业务、字段、阈值、代码和命名示例不能直接当作已批准需求，也不代表已经完成的成果。

## 1. 最终到底要做到什么

交付一个包含真实 AI 功能的软件，并证明团队能在可审计的人类监督下，通过 AI coding agent 完成设计、构建、验证和维护的整个软件工程生命周期。（P3）

必须同时具备：

1. **真实 AI 组件**：例如 LLM 功能、检索增强流水线、AI 辅助决策。
2. **确定性安全边界**：至少一处 AI 输出必须经过普通程序的确定性约束，不能由模型自行决定是否合规。
3. **机器可检查的需求**：功能、不变量和质量目标都有 ID、验收标准、优先级和验证办法。
4. **能约束 agent 的架构与权限**：说明谁可建议、谁有最终决定权；允许读写哪些文件；错误时如何降级。
5. **受监督的开发证据**：先计划、人工批准、再生成代码；保留完整会话及人工打断、纠偏、批准、拒绝的理由。
6. **真实运行的验证与 GitHub 门禁**：测试、需求 schema、回归、语义评估、AI 使用日志等检查能阻断不合格变更。
7. **持续演化证据**：需求、架构、代码、测试、运行监控、文档保持同步；有评审、缺陷、债务记录。

I20 以增强 TradingAgents 为参考方向，也允许选择复杂度相近的项目；P3 明确应用自选，VHIS 只是模式参考，不是要扩展的项目。N 人团队应增加 N 个有意义的功能需求和非功能需求（I20 对两类数量的分配不够明确，稳妥做法是各准备 N 个并确认）。允许删减原有功能，但要保留合理的业务与架构完整性。

**示例目标**：股票分析助手生成有来源的分析建议；确定性代码拒绝过期数据、无来源结论和超预算调用；AI 无权直接执行交易。与基线比较延迟、token、成本及质量，证明新增要求产生实际效果。此例仅供理解，不限定选题，也不要求接入真实交易。

## 2. 使用方式与 Agent 执行约束

### 2.1 人工审阅方式

按“目标 → 交付清单 → 文件规范 → 门禁 → 流程 → 验收清单”审阅。审阅时确认范围是否明确、每项要求是否有对应文件和可复核证据、待确认事项是否已经解决。项目采用的业务范围、指标阈值、技术栈和架构决策应落入正式需求与架构文件。

### 2.2 Agent 的阅读与执行顺序

1. 阅读本文件，识别最终目标、交付范围、必须遵守的边界和未决问题。
2. 进入实际项目仓库后，读取适用的 `AGENTS.md`、`Prompt.md` 及其指定的需求、架构、权限和验证文件；本文件不替代这些入口。
3. 先检查现有基线和产物，列出缺口；沿用已有实现与已批准决策，避免重复创建或整体重写。
4. 提交执行计划：关联需求 ID、受影响模块、接口契约、修改路径、测试与验收方式、实施步骤和人工门禁。
5. 计划与测试获得所需人工批准后再生成应用代码；只在获准范围内实施，按阶段验证并报告证据。

### 2.3 必须遵守的执行边界

- 使用 **OpenCode** 作为项目 coding agent；课程采用 `deepseek-v4-flash` 展示和评估，具体运行配置应明确记录。（I5–6）
- 应用代码由受监督的 agent 生成和修改；人工通过明确指令、评审和批准来控制变更，并保存原始会话及干预理由。（I20）
- 不得将本文件中的股票业务、模块名、阈值、配置字段或命令示例自动升级为正式规格；以已批准需求和架构为准。
- 不得绕过确定性安全边界、放宽验收阈值、篡改评估集或修改测试语义以制造通过结果。
- 不得伪造批准、会话、测试结果、运行数据、贡献记录或提交历史；未执行的检查明确标为“未执行”，缺失证据明确标为“待补充”。
- 涉及安全关键代码修改时，必须有对应架构决策和人工批准；不得自行修改 human-only 文件或超出路径权限。
- 发现需求冲突、权限不足或影响当前任务的未决事项时，明确指出影响并请求决定；可继续不依赖该决定的工作，不得擅自扩大范围。
- 每次变更同步相关需求、架构、追踪、测试与 AI-use log；每轮交付说明改动、验证结果、证据位置和剩余问题。

### 2.4 项目提交边界

提交项目目录 ZIP，并单独提交 **10 分钟演示视频，视频不放 ZIP**；不得提交 API key。（I23）项目截止时间以正式通知为准。

## 3. 总交付物清单

| 编号 | 交付内容 | 核心验收点 |
|---|---|---|
| D1 | YAML 需求与 JSON schema | 需求可机器检查，CI 真正验证 |
| D2 | 架构文档 | 决策、边界、不变量、上下文、权限、状态、运行策略可追踪 |
| D3 | 编码治理文件 | agent 知道读什么、改什么、何时停下来、如何验证 |
| D4 | 验证治理与 QA 记录 | 三层验证、每项验收有测试、每项不变量有反例测试、零回归 |
| D5 | 完整原始会话与人工注释 | 覆盖从需求分类到基于测试修订架构的全过程 |
| D6 | 单一 `Report.md` | 团队过程、优化、贡献、每人反思和真实证据 |
| D7 | 真实 GitHub 仓库 | 源码、测试、CI/CD、阻断门禁、分支保护、有效提交历史 |
| D8 | `src/` 与 `test/` | 完整实现，离线测试与 API 测试分离 |
| D9 | 根目录静态 `Prompt.md` | 先执行计划、批准后编码、分阶段人工门禁 |
| I23 补充 | 独立 10 分钟视频 | 新要求实施前后效果、软件工程原创性、追踪与治理 |

## 4. 推荐交付文件树

以下以 P9 和 I24 的目录树为主；标有“可选”的三份文件在 P5 正文中明确 optional。为减少歧义，建议有内容就提交，不能把它们误称为硬性必交。

```text
<team-app>/
├── README.md
├── AGENTS.md
├── architecture-blueprint.md
├── Prompt.md
├── Report.md
├── docs/
│   ├── req/
│   │   ├── requirements.yaml
│   │   └── req-schema.json
│   ├── architecture/
│   │   ├── adr/001-<choice>.md
│   │   ├── invariants.md
│   │   ├── trace-matrix.md
│   │   ├── memory-design.md
│   │   ├── permission-model.md
│   │   ├── runtime-policy-catalog.md
│   │   ├── evaluation-table.md
│   │   ├── evaluation-logbook.md      # 可选
│   │   ├── risk-list.md               # 可选
│   │   └── option-ledger.md           # 可选
│   ├── code-governance/
│   │   ├── structural-constraints.md
│   │   ├── verification-constraints.md
│   │   └── mcp-tool-manifest.md
│   ├── ai-use-log.yaml
│   ├── review-memo.md
│   ├── debt-register.md
│   └── bug-diary.md
├── .opencode/
│   ├── permissions.jsonc
│   └── rules.md
├── .agent/rules.md
├── .github/workflows/ci.yml
├── prompts/
│   ├── prompt_v1.0.yaml
│   └── prompt_v1.1.yaml
├── src/                             # 模块名对应架构元素
├── test/
│   ├── offline/
│   └── live/
└── transcripts/
    ├── <student-id>-<student-name>.md
    └── ...
```

项目实际需要的依赖声明、锁文件、启动配置、固定评估数据集等应随实现补充；上面的树不是禁止其他文件。`goal.md` 是人工审阅与 agent 定向指南，不是课程指定交付物；实际执行入口仍为项目仓库的 `AGENTS.md` 和 `Prompt.md`。

## 5. 每个文件写什么：内容与示例

### 5.1 根目录文件

| 文件 | 应有内容 | 示例片段或结构（均为建议） |
|---|---|---|
| `README.md` | 项目目的、架构概述、文件组织、离线/live/完整测试运行方式、真实 GitHub URL；解释门禁设计 | `Purpose → Architecture → File map → Setup → Run → Offline/Live/Full tests → Blocking gates → Repository URL`；具体命令必须能执行 |
| `AGENTS.md` | agent 单一入口：构建目标、架构阅读顺序、代码基线、可读/可改/冻结区域、模块组织、接口契约、验证要求 | `先读 blueprint、ADR、invariants、permission-model；基于现有 baseline 增量修改；不得修改冻结的评估集；先提交计划` |
| `architecture-blueprint.md` | 主约束文档：范围、架构驱动、系统边界、组件、权威边界、agent 流程、权限、验证、可观测性、变更策略 | `LLMAdvisor 只产出建议；SafetyGuard 作确定性校验；失败返回拒绝结果并记录原因；所有请求带 trace_id` |
| `Prompt.md` | 静态启动指令；AGENTS 后读取；要求执行计划、人工批准、构建、自验证、阶段门禁 | `输出需求→模块→测试追踪、接口、范围与非目标、测试策略、步骤；停止等待人工批准，获批后才编码` |
| `Report.md` | 过程总结、优化、团队名单学号贡献、每人反思、质量证据、协同演化、人工发现的问题 | 见第 8 节报告提纲 |

`Prompt.md` 是开发启动指令；`prompts/*.yaml` 是应用运行时 prompt，二者不要混用。

### 5.2 D1：需求文件

`docs/req/requirements.yaml`：包括机器可读 PRD 和汇总需求，逐项有 ID、type、statement、可机器检查的 fit criterion、MoSCoW 优先级及明确取舍。覆盖功能、不变量、质量、性能、成本、治理、安全；从现有系统分析得到的需求必须链接来源。（P5）

示例（自定义 schema 示例，不是课程规定字段名）：

```yaml
product:
  name: EvidenceStock
  scope: 生成带证据的股票分析建议
  non_goals: [自动交易]
requirements:
  - id: FR-001
    type: functional
    statement: 分析响应包含结论及来源标识
    priority: Must
    tradeoff: 优先保证证据完整，暂缓多语言输出
    fit_criterion:
      metric: responses_with_valid_source_ids_ratio
      threshold: 1.0
      verification: test/offline/test_analysis_contract.py
    sources: [baseline-observation-001]
  - id: INV-001
    type: invariant
    statement: 未通过安全校验的 AI 建议不得返回为可用建议
    priority: Must
    tradeoff: 允许拒绝服务，禁止绕过校验
    fit_criterion:
      metric: unsafe_output_escape_count
      threshold: 0
      verification: test/offline/test_safety_guard.py
  - id: PERF-001
    type: performance
    statement: 固定评估条件下响应延迟满足预算
    priority: Should
    tradeoff: 质量阈值优先于延迟优化
    fit_criterion:
      metric: p95_latency_seconds
      threshold: 30
      verification: fixed_dataset_benchmark
```

性能和成本阈值需由团队基线测量决定；30 秒只是示例。指标应明确数据集、样本量、运行条件、比较方向及如何计算。

`docs/req/req-schema.json`：JSON Schema，校验 YAML 解析后的数据结构，规定必填字段、类型、枚举等。例如 `required: [id, type, statement, priority, fit_criterion]`、`priority.enum: [Must, Should, Could, Wont]`。CI 必须实际调用验证器；ID 唯一性、追踪完整性等也应检查，不能认为字段结构合法就代表语义正确。

### 5.3 D2：架构文件

| 文件 | 必须描述的内容 | 内容示例 |
|---|---|---|
| `adr/001-<choice>.md` | 选定架构、备选、理由、后果、重开条件、设计过程；AI 上下文分层、装配、token 上限、压缩阈值、压缩后约束重注入 | `选择有界分析流水线；比较自由多 agent 辩论；上下文=身份/常驻约束/检索证据/历史/可恢复状态/当前任务；去重→排序→预算→压缩→装配；示例 cap=16000，80% 触发压缩，之后重注入安全规则` |
| `invariants.md` | 不变量、源需求 ID、执行组件、验证方法、违反时具体运行回退 | `INV-001 / SafetyGuard / 恶意输出反例测试 / 拒绝响应、记录事件并禁用该次建议`；“修 bug”不是运行回退 |
| `trace-matrix.md` | 每项需求→执行组件→测试或证据→运行监控 | `PERF-001 → AnalysisService → benchmark.json → latency_p95` |
| `memory-design.md` | 跨会话、中断、版本保留什么；写入/检索策略、所有权、保留期、隐私 | `保存带版本号的任务检查点；只保存脱敏摘要；旧 schema 不兼容时拒绝恢复；30 天清理（示例）` |
| `permission-model.md` | 每个 coding-agent 角色的逐路径读写白名单，默认无读无写 | `Planner 可读 docs，不写 src；Builder 可读已批准规范，仅写指定模块；Verifier 可读实现并运行测试，不改审批证据` |
| `runtime-policy-catalog.md` | 每条降级或失败路径及动作 | `API 超时→限次重试→返回不可用；无来源→拒绝；预算耗尽→停止调用；数据过期→提示刷新` |
| `evaluation-table.md` | 候选架构比较，支持最终选择 | `候选 / 安全边界 / 质量 / 延迟 / token / 可测试性 / 维护代价 / 结论`，填真实测量或明确估算 |
| `evaluation-logbook.md`（可选） | 支持架构判断的累计证据 | `日期、候选版本、数据集、运行条件、原始结果路径、结论、局限` |
| `risk-list.md`（可选） | 可能演化为缺陷的假设及复审触发器 | `数据接口稳定性假设；连续两次契约失败时复审；负责人及缓解措施` |
| `option-ledger.md`（可选） | 被拒方案及重新考虑条件 | `暂不使用多 agent 自由辩论：延迟过大；只有质量提升超阈值且成本受控时重开` |

### 5.4 D3：编码治理文件

| 文件 | 内容要求与示例 |
|---|---|
| `docs/code-governance/structural-constraints.md` | 每个架构元素恰好对应一个模块；扩展基线而非替换；每个模块和函数引用所实现的架构决策与不变量；明确权威边界。例如 `safety_guard.py 对应 SafetyGuard，标注 ADR-001/INV-001，禁止绕过统一校验入口`。不适用项应说明理由。 |
| `docs/code-governance/mcp-tool-manifest.md` | 工具、允许调用的角色、用途、权限与约束。例如 `只读仓库检索→Planner/Reviewer；执行测试→Verifier；部署操作→明确授权角色`。无 MCP 时也说明未启用，不能省略治理说明。 |
| `.opencode/permissions.jsonc` | 项目级机器可读权限、guard 规则与执行机制。例如“默认拒绝、按角色/路径白名单允许、冻结规则文件、限制命令”。实际键名必须符合所用 OpenCode 版本，不能把示意 JSON 当作有效配置。 |
| `.opencode/rules.md` | 常驻行为规则，**human-only**。例如 `未经批准不编码；不得绕过门禁；不得读取密钥；遇到需求矛盾停止并报告`。必须有实际措施限制 agent 修改。 |
| `.agent/rules.md` | 项目 covenant：抽象限制、依赖限制、测试独立性、每功能至少一个负面测试；安全关键代码修改需 ADR 和人工批准；需求变动后一轮 sprint 内更新规则。 |

### 5.5 D4：验证与质量记录

| 文件 | 内容要求与示例 |
|---|---|
| `verification-constraints.md` | 每个 fit criterion 至少一项测试；每个不变量至少一项在其被违反时会失败的测试；测试引用 REQ/INV ID；每轮跑完之前全部测试，零回归；定义结构、回归、行为三层验证。 |
| `docs/review-memo.md` | 每个 PR 一条评审，覆盖规格、架构、代码、测试、运行元数据，全程检查安全和效率；结论只能为 `APPROVE`、`CHANGES REQUIRED`、`REJECT`。示例：`PR #12 / commit / reviewer / spec evidence / architecture evidence / findings / verdict`。 |
| `docs/debt-register.md` | 持续记录 prompt rot、虚构依赖、不可触碰代码、隐藏依赖、agent 膨胀、评估债、护栏债、人类/认知债。示例：`DEBT-003 / guardrail debt / 缺少过期数据反例 / 风险 / owner / 到期 / 关闭证据`。 |
| `docs/bug-diary.md` | 重大 bug 的症状、复现、分类、根因、修复、暴露的不变量缺口。示例：`超时后仍返回旧建议→模拟超时复现→状态污染→清空旧状态→新增 INV 与回归测试`。 |

三层验证（P6）：结构层检查 import、模块边界、权限、架构适应度函数；回归层跑所有旧测试；行为层验证 faithfulness/relevance 等质量阈值以及零安全逃逸。

### 5.6 其他文件与目录

| 文件/目录 | 内容与示例 |
|---|---|
| `docs/ai-use-log.yaml` | 必须保持最新；P 未指定字段 schema。建议每项包含 `id, date, member, agent, model, task, requirements, changed_files, transcript, human_decision, validation, commit`。按真实情况记录，代码或 prompt 改动的 PR 未更新此文件必须阻断。 |
| `.github/workflows/ci.yml` | 真正执行第 6 节的门禁。示例 job 名 `schema, static, test-approval, regression, semantic-eval, ai-use-log` 只是建议；不能仅写名称或无条件成功。安全相关路径要触发额外检查。 |
| `prompts/prompt_v1.0.yaml` | 版本化应用运行时 prompt。示例 `version: '1.0'; purpose: evidence_analysis; template: '依据提供的证据分析，并返回来源 ID'; model_parameters: ...`；明确输出契约。 |
| `prompts/prompt_v1.1.yaml` | 后续真实版本及变更。例如新增证据不足时拒答策略，并关联固定评估集结果。不可凭空伪造版本演化；课程树展示两个版本。 |
| `src/` | 完整应用源码，模块对应架构元素。示例 `retrieval.py, llm_advisor.py, safety_guard.py, analysis_service.py`；技术栈不限于 Python。 |
| `test/offline/` | 无 API 依赖、确定性测试，如 schema、接口、权限、非法输出、预算耗尽、状态恢复及固定 mock。 |
| `test/live/` | 真实模型/API 的集成及行为评估，说明 key 配置、预算、运行命令、环境与阈值。提交密钥占位配置而非真实 key。 |
| `transcripts/<student-id>-<student-name>.md` | 完整原始 session，保留工具调用、输出、失败及重试，再添加清楚标记的人工注释：`[HUMAN INTERVENTION: REJECT] agent 绕过 Guard；理由 INV-001；要求重规划；后续证据...`。不能只交摘要或事后编造对话。 |

## 6. 六项阻断门禁与分支保护

以下是 P10 的硬性要求，必须用失败案例证明能拦截：

| 门禁 | 触发与阻断条件 | 建议实现/证据 |
|---|---|---|
| 测试批准 | 实施开始前，变更的测试必须已经获批；否则代码不能合并 | 保存测试先行的 commit、人工批准者和时间，与实现 commit 关联；只有测试通过不等于先获批 |
| 静态分析 | 每次提交跑 lint、类型和依赖检查；安全路径 PR 另跑契约、安全、API surface、权限检查 | 路径触发检查、失败日志、修复后通过记录 |
| Schema | 需求 YAML 必须符合 JSON schema | 故意删除必填字段，证明 CI 失败 |
| 语义评估 | prompt 或模型变更重放固定评估集；未达质量阈值不能进生产且需报告 | 固定样本、指标与阈值版本化；证明劣化 prompt 被拦截 |
| 回归 | 每项变更跑完所有历史测试；任何回归阻断合并 | 完整 suite 结果及失败 PR |
| AI-use log | 代码或 prompt 变更未同步更新日志时阻断 PR | diff 检测及漏记日志的失败案例 |

分支保护必须要求 CI 通过；安全关键路径变更还必须有人工 review 和相应 ADR。仓库设置与 CI 配合执行，单独提交 `ci.yml` 或文字声明不构成已启用分支保护。可保留脱敏设置截图/导出、PR 和流水线链接作为证据。

## 7. 总项目开展流程

### 阶段 0：确认范围和基线

确认选题复杂度及新增需求范围；若基于 TradingAgents，固定 baseline commit，先跑通并记录质量、时间、token、成本。保存观察来源，不预先假定新版本一定更好。

产出：项目范围、基线版本、初始测量、仓库和会话记录机制。

### 阶段 1：需求工程

分析现有系统，区分功能、质量、安全与不变量；消除歧义；写 YAML、schema、MoSCoW 和取舍；明确每项验收的测量方法。将基线发现链接到来源。

人工检查：需求是否有意义、阈值是否可测、至少一条零容忍不变量是否由确定性程序执行。

### 阶段 2：架构候选与评估

按架构驱动生成候选，评估并写 ADR、blueprint、上下文设计、权限、状态和运行策略；建立需求→组件→测试→监控追踪矩阵。建议通过多轮 ADD（Attribute-Driven Design），根据质量属性及证据逐轮细化，而非只画一张图。（I25）

人工检查：AI 建议权与系统决定权是否明确；失败是否有具体回退；候选选择是否有证据。

### 阶段 3：治理与测试先行

建立 AGENTS、静态 Prompt、权限、规则、工具清单和验证约束；定义接口、验收测试及负面测试；在实施前取得测试批准并保存证据。尽早启用 CI 和分支保护，避免最后补做过程记录。

人工检查：计划和测试确实在实现前批准，agent 权限有实际执行机制。

### 阶段 4：受监督的增量构建

OpenCode 从 AGENTS 进入，读取 Prompt，先出计划（追踪、接口、范围、测试策略、步骤），停止等待人工批准。获批后按小 PR 实施，每个功能包括正向与负向验证；团队通过 agent 执行代码变更；持续保存原始 transcript、AI-use log 和提交历史。

发现越权、需求误解或不正确测试时及时拒绝、重定向并解释原因。

### 阶段 5：三层验证、评审与架构迭代

依次做结构、历史回归、行为评估；运行离线及 live 测试；记录缺陷和债务；每 PR 写 review memo。测试若推翻架构假设，应修订 ADR、需求/约束/代码/测试/运行监控，而非只打补丁。

每轮变化同步相关 artifacts；规则在需求变化后一轮 sprint 内更新。保留至少一条“测试证据→人工判断→架构修订→重新验证”的完整链。

### 阶段 6：前后对照评估与优化

在可比数据、模型、环境与参数下比较 baseline 和最终版本；记录质量、安全逃逸、延迟、token、成本、失败与重试。分别衡量应用运行和 coding agent 生成应用的 token。不要通过降低质量或篡改评估集制造改进。

I25 提出的工程质量方向：需求/架构/编码治理更强，生产级考虑、低耦合高内聚、职责清楚、追踪强、多轮 ADD、两类 token 消耗下降。新增业务功能本身不算软件工程原创点（I23）。

### 阶段 7：报告、视频和最终审计

整理 Report、贡献和每人反思；录制独立 10 分钟视频，展示前后行为变化及工程原创性；从干净环境按 README 复现；检查密钥、缺失文件、失效链接、门禁和分支保护；交 ZIP 与独立视频。

建议视频时间分配（非硬性）：1 分钟目标与基线，3 分钟前后效果，2 分钟架构及确定性边界，2 分钟追踪和门禁失败演示，2 分钟人工介入、迭代与结论。

## 8. Report.md 建议提纲与格式要求

P6–7：单一 Markdown 文件，**不超过 10,000 words（图不计入），12 pt、单倍行距呈现时超过 15 页**。两项须同时满足；Markdown 本身没有固定页数，建议自查渲染结果，提交主体仍是 Markdown。每名成员写一个约 300–500 words 的简短反思段，含姓名和学号。

建议结构：

1. 项目目的、范围、基线与最终成果。
2. 全体成员姓名、学号、相对贡献表及实际交付证据。
3. 需求工程与变动记录：需求波动、歧义解决、优先级取舍。
4. 架构设计过程、候选评估、多轮 ADD、上下文/记忆/权限设计。
5. 编码和验证治理：人工批准、受控生成、CI 与分支保护证据。
6. 开发过程优化：哪些活动减少返工、token 和认知负担。
7. 质量与比较评估：基线/最终、缺陷趋势、成本和局限。
8. 具体人工干预：人发现了什么、agent 漏掉了什么、如何纠正。
9. artifacts 如何协同演化：用真实变更链举例。
10. 每人自我反思及可核对证据索引。

相对贡献平均必须为 1.0。示例：有效产出工时 60、55、35，均值 50，权重 1.2、1.1、0.7。可用工时或 story points，但必须对应实际交付；纯声称投入而无产出不算有效贡献。（P4、7；I22）

## 9. 原文不一致或需确认的事项

| 问题 | 原文情况 | 本指南采用的稳妥处理 |
|---|---|---|
| blueprint 路径 | P5 说 D2 文档都在 `docs/architecture/`；P9、I24 将 blueprint 放根目录 | 以两份目录树一致的根目录为主，所有入口明确引用；如需目录内入口可加指向根文件的说明，避免两份内容漂移；最终向教师确认 |
| PRD 与 registry | P5 说 PRD 和 consolidated registry 都是 YAML，但只列一个 `requirements.yaml` | 在该文件同时组织 product 与 requirements；是否另需独立 PRD 文件待确认 |
| transcript 数量 | P2 总览说五份 annotated transcripts；P6 D5 又说 one full raw transcript，并用 each/collectively；目录按学生命名 | 不能推定任意数量即可；保存完整全过程，规划五份有注释 session 且覆盖所有成员，并确认五份与团队人数/文件组织的关系 |
| 可选架构文件 | P5 明确 logbook、risk list、option ledger 可选；P9 树全部展示 | 明确可选身份，建议实际维护以支持报告证据 |
| N 个需求 | I20 的 N meaningful functional requirements and non-functional requirements 数量分配不明 | 各准备 N 个最稳妥，确认后冻结范围 |
| 报告字数与页数 | 同时要求 ≤10000 words、12 pt 单倍行距 >15 页 | 同时遵守；中文如何计 words 及具体排版规则待确认 |
| 截止日期 | I7 仅给暂定第 13 周 | 不编造日历截止日期，以 Canvas/教师通知为准 |
| 文本残缺/疑似笔误 | P5 schema 描述末尾 “as a date”；P7 README 条款末尾 “and” 截断 | 结合 P8、P10 明确要求总结，不补造不存在的条款 |

## 10. 提交前核对

- [ ] 可运行应用包含真实 AI 功能及至少一个确定性安全边界。
- [ ] 新增需求有来源、MoSCoW、明确取舍和机器可检查标准。
- [ ] 架构、上下文预算/压缩、状态、权限、运行降级与追踪齐全。
- [ ] 人工批准发生在计划/测试/安全变更所要求的正确阶段，有真实证据。
- [ ] 代码由受监督的 agent 生成，完整会话及人工介入注释可核对。
- [ ] 离线、live、完整测试运行说明准确，测试与需求/不变量有 ID 关联。
- [ ] 六个门禁真正运行，有失败阻断证据；分支保护和安全路径人工评审已启用。
- [ ] AI-use log、review memo、debt register、bug diary 随迭代更新。
- [ ] Report 满足字数/呈现页数要求，有每人反思及平均 1.0 的贡献权重。
- [ ] ZIP 按规定结构组织且不含 API key；真实 GitHub 仓库与有意义历史可访问。
- [ ] 独立 10 分钟视频展示前后效果、工程原创性、追踪与 agent 治理。

验收的关键链条是：**需求 → 架构约束 → 受控计划与生成 → 独立验证 → 人工评审与门禁 → 可运行效果 → 真实过程证据**。
