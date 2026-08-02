# RTLScout 与「EDA Agent 设计要点」对照分析

> 目的：将 RTLScout（华为开源，arXiv 2606.06530，BSD-3-Clause-Clear）的工程实现逐项对照我们规划的「大脑 + Harness」设计要点，回答每个设计点"它是怎么解决的、我们该照抄什么、该自建什么"。
>
> 分析对象：`D:\code\EDAthon\RTLScout\rtlscout`（commit 87a00ed），代码路径均为仓库内相对路径。
>
> 一句话总览：RTLScout 证明了「LLM 提议 + 工具验证裁决」这套闭环在 RTL 生成/优化上是可工程化的，且其 **opencode 后端与 EDAthon 官方容器的形态完全一致**（opencode + 外部 LLM + 全套 EDA 工具）。它没有覆盖布线与 DRC 两类题，但 harness 骨架（统一评测入口、快照、权威重算、时间盒）可直接迁移。

---

## 一、总览：组件 → 设计点映射表

| RTLScout 组件（文件） | 对应设计点 | 作用一句话 |
|---|---|---|
| `core/opencode_backend.py` | 大脑接口、统一入口、时间管理 | 渲染 AGENTS.md/opencode.json/evaluate_design 包装脚本，启动一次干净会话，nudge 循环，导出会话 |
| `core/agents_md.py` | 任务目标与硬约束 | 生成给 shell 型 agent 的精简任务书（任务/工作流/参考指针） |
| `core/prompts.py` | 领域 Skill、搜索策略 | react 后端的系统提示词（策略步骤、硬规则、优化技巧、参考文档注册表） |
| `core/agent.py` | Correctness-first、best 管理、文件工具 | react 循环：7 个受限工具 + best 追踪 + 快照 |
| `core/evaluation.py` | 分层执行、统一 JSON 输出 | 一次评测的完整管线（编译→lint→仿真→成本→CEC）与双格式输出 |
| `core/correctness.py` | 日志解析 | Verilator lint+仿真，TB_SUMMARY 解析为逐项检查，sim_stats 提取 |
| `core/cost.py` | 固定参数、可插拔指标 | CostMetric 抽象 + 10+ 种成本度量（无工艺快指标 / 工艺级 PPA） |
| `core/equivalence.py` | Correctness-first 增强 | CEC 形式等价检查（Yosys→BLIF→yosys-abc cec） |
| `core/eval_store.py` | 外部记忆、统一入口（shim） | 无状态评测命令：agent_evals.jsonl + eval_i/ + best_design/ 落盘 |
| `core/reeval.py` | 评测防污染、可复现性 | 权威重算（基准自己的输入），一致门 + 篡改特征扫描 |
| `core/sandbox.py` / `core/containers.py` | 评测防污染（隔离） | LocalSandbox / ContainerSandbox（docker run --rm），进程组超时击杀，label 清理 |
| `core/runner.py` | 工作目录隔离 | provision_workspace（基准输入拷贝）+ runs/ 目录树 |
| `core/agent_backend.py` | 时间管理、后端抽象 | RunLimits（wall_clock_s/max_steps）、BackendRequest、react/opencode 二选一 |
| `core/multirun.py` | 候选搜索策略（进阶） | 精英池：fresh/播种混合，softmax 采样，经验文本传递 |
| `benchmarks/*` | 题目包格式 | description.txt + metadata.json + tb.sv + context/ + (golden_reference) |

---

## 二、大脑的设计点 → RTLScout 的实现

### 2.1 任务目标与硬约束 →「AGENTS.md + 引擎级文件保护」

**写清楚约束**：`core/agents_md.py` 渲染 AGENTS.md（`opencode_backend.py` 每次 run 写入 workspace）：

- **任务**：`# Task — optimize a <HDL> design` + `## Specification`（来自 `description.txt`）+ `## Objective`（**先功能正确、再最小化成本**，模块名与端口必须严格匹配规格）——对应"正确性要求 + 优化目标"
- **工作流**：`## How you work here`——有真实 shell、设计放 `design.sv`、**只用 `./evaluate_design` 评测**、把评测当黑盒（"do not burn your budget reading core/、成本实现、testbench 内部"）——对应"哪些能碰、哪些不能碰"
- **时间**：`## Time budget`——明确 wall-clock 预算、`./remaining_time` 查询、自动终止、无需收尾——对应"什么时候停止"
- **参考**：`## Reference docs & examples`——指针而非内联（"read these files yourself with `cat` instead of guessing"）——保持 prompt 精简

**禁止修改的硬约束**，RTLScout 不是靠提示词，而是**引擎级强制**：

- react 后端：`agent.py:_safe_write_path` 直接拒绝写入 `tb.sv`（agent.py:274-281），`_safe_path` 防路径穿越（agent.py:268-273）
- opencode 后端：文件保护交给权限系统（`opencode_backend.py:_permissions`，非 yolo 模式 deny `webfetch/websearch`）＋权威重算时基准的 `tb.sv`/`*.dat` 永远覆盖 agent 版本（见 3.9）

> **对我们的结论**：硬约束要"提示词声明 + 引擎强制"双保险。提示词只负责让模型自觉，引擎负责让模型做不到。

### 2.2 领域 Skill →「参考文档注册表 + 按需读取，而非技能文件」

RTLScout 的"技能"不是 skill 文件，而是三层结构（`prompts.py`、`agents_md.py`）：

1. **参考文档注册表**：`VERILOG_REFERENCES` / `SPIREHDL_REFERENCES`——每项是（路径, 一句话说明）。渲染进 AGENTS.md 时只给指针，agent 用 shell 自己 `cat`——**既省 token 又保留深度**
2. **内联策略片段**（react prompt）：`_STRATEGY_STEPS_3_TO_7`（先正确后优化）、`_CREATIVITY_AND_EVAL_BLOCK`（大胆尝试、可回退）、`_DELAY_OPTIMIZATION_TIPS`（accumulation order、critical path 分析等具体经验）
3. **按 run 开关的优化指导**：`_optimization_guidance`——只有启用某能力（`@abc_optimized`、`@arithmetic_optimized`、`--fsm-optimize`）才在 prompt 里出现对应说明（agents_md.py:147-182）

（仓库另有 `.opencode/skills/design-db-*`，那是"已验证子电路库"功能，与比赛无关，不迁移。）

> **对我们的结论**：造 `skills/rtl_debug.md`、`ppa_optimization.md` 等文件没问题，但挂载方式应该学 RTLScout——**AGENTS.md 里放指针，让 agent 按需 cat**，而不是把整份技能塞进系统提示词。

### 2.3 状态机 →「提示词规则 + 引擎门槛 + 时间盒」，不硬编码状态机

RTLScout **没有实现显式 FSM 状态机**。你列的 INSPECT→BASELINE→DIAGNOSE→…→STOP 由三套机制共同保证：

| 你的状态 | RTLScout 的对应物 |
|---|---|
| INSPECT / BASELINE | 提示词步骤 1-3：先读懂规格，写简单正确实现，**先 run_evaluation 建立基线**（`prompts.py:_STRATEGY_STEPS_3_TO_7`） |
| DIAGNOSE / PROPOSE / EDIT | "always call a tool" 规则 + 无工具调用时的强制提醒（`agent.py:738-745`："Please use a tool"）+ 小步修改提示（`_IMPORTANT_COMMON`："targeted, incremental changes"） |
| EVALUATE | 引擎强制：**每轮工具循环里只有 run_evaluation 能产生快照和 best 更新**（agent.py:559-625） |
| SELECT（接受/拒绝/回滚） | **引擎级 best 门槛**：`passed==True 且 cost.ok 才可能成为 best`（agent.py:594-613；eval_store.py:71-99 的 `select_best_eval`：lowest cost among 100%-correct）——"未通过功能验证不比较 PPA"是写死在代码里的 |
| RECORD | 每次评测自动落盘（见 2.4） |
| STOP / NEXT | `done` 工具（react）/ wall-clock 自动终止（opencode）/ nudge 守卫（见 2.8） |

> **对我们的结论**：不要自己写状态机让模型"按状态转移"——**把门槛放进引擎，把顺序写进提示词，把停止交给时间盒**。三者都比显式状态机更不容易被模型绕过。

### 2.4 外部记忆 →「文件系统即记忆，无状态 shim 读写」

你规划的 `best.json / history.jsonl / current.json / failed_strategies.md`，RTLScout 的落盘结构（`core/eval_store.py` + `core/agent.py`）：

| 你的文件 | RTLScout 的对应物 | 内容 |
|---|---|---|
| history.jsonl | `agent_evals.jsonl`（每行一个 eval dict） | iteration(eval_index)、passed、cost_value、metrics、failure 信息（sim 输出截断）、cec、target_delay |
| best.json | `best_design/_best_meta.json` | eval_index、step_index、best_cost、cost_metric、design_file |
| current | `workspace/`（agent 正在改的） | 设计文件 + 辅助文件 |
| 每轮快照 | `eval_{i}/` = workspace 副本 + result.json + summary.txt | 完整可复现的一轮 |
| failed_strategies | 会话内上下文 + `summary.txt`（轮末反思四问） | 见 `_request_summary`（agent.py:808-849）与 `REFLECTION_PROMPTS`（opencode_backend.py:48-53） |

**关键机制**：eval shim 是**无状态子进程**——每次 `python -m core.eval_store` 都从 `agent_evals.jsonl` 重新推导 eval_index 与当前 best（eval_store.py:121-192）。所以"记忆"不依赖任何长驻进程或模型上下文，模型随时可以中断重来。

**跨 run 记忆**（多 run 播种）：`multirun.py` 把上一 run 的 best 设计文件拷进新 run 的 context（`build_seed_context`）+ 上一 run 的总结文本拼进系统提示词（`build_seed_prompt`）——"经验"以文本传递，"设计"以文件传递。

### 2.5 Correctness-first 决策 → 引擎级强制（不是权重）

RTLScout **完全采用你的方案**，且是在引擎里实现：

```python
# evaluation.py:405-409
passed = correctness.passed and cec_ok        # 功能错误 => 直接拒绝，无总分可谈

# agent.py:594 与 eval_store.py:71-99
best = 在 passed 且 cost.ok 的评测中取 cost 最低者   # 功能正确才比较指标
```

连"功能正确"都有两层定义：**仿真通过 + （若有 golden）CEC 等价**（evaluation.py:393-409）。没有"正确性权重 + PPA 权重"这种折中公式——与你的判断完全一致。

### 2.6 保存 best candidate → 引擎自动快照，current/best 天然分离

- **current** = `workspace/`（agent 实时在改）
- **best** = `best_design/`：每次评测若成为 new best，自动复制整个 workspace 并写 `_best_meta.json`（agent.py:518-541 `_snapshot_best`；eval_store.py:28-51）
- 每一轮评测另存 `eval_{i}/`（agent.py:543-557）
- **提交口径**：`run_benchmark.py` 的最终 `result.json`/`best_design/` 全部由权威重算后的 best 重建（reeval.py:238-242）——**提交的必须是 best，不是最后一次尝试**，正是你的要求

### 2.7 候选搜索策略 → 提示词约束 + 精英池（进阶）

**单 run 层面**（提示词，`prompts.py`）：

- "Use different filenames for different design variants so you can retrieve them later"——多候选并存
- "Make targeted, incremental changes rather than rewriting files from scratch"——小步、可解释
- "If an optimization breaks correctness, revert and try a different approach"——失败即回退换路
- "The best result is the one with lowest cost among designs that pass 100% of testbench checks"

**多 run 层面**（`multirun.py`，比赛的"中后期"选项）：`ElitePool`（max_size 默认 5、temperature 温度参数、softmax 采样）——每个新 run 按概率（`compute_fresh_probability`）要么 fresh 从零开始（探索）、要么用池中 best 播种（利用）。这对应你说的 Elite A/B/C，但 RTLScout 是**概率混合**而非分槽。

> **对我们的结论**：第一版只做单 best（符合你的"最小可用"），精英池留作比赛当天的进阶打法。

### 2.8 时间与 Token 管理 → RunLimits + 截止时间戳 + nudge 三守卫

| 你的设计点 | RTLScout 实现 |
|---|---|
| 预算定义 | `RunLimits(wall_clock_s, max_steps)`（agent_backend.py:36-47）；react 用 step 数，opencode 用 wall-clock（两者互斥适用） |
| 剩余预算告知 | `_deadline_epoch` 文件 + `remaining_time` 包装脚本（opencode_backend.py:291-307），agent 随时自查 |
| 提前停就催 | nudge 循环（opencode_backend.py:490-498）：agent 提前收手 → 用同一会话继续推 "keep going" |
| nudge 防跑飞 | 三守卫：剩余 < 45s 不催；最多 5 轮；**一轮没产生新 eval 就停**（判 done/卡死） |
| 硬终止 | 超时杀**整个进程组**（sandbox.py:85-120：`start_new_session` + `killpg`，SIGTERM 宽限 10s 再 SIGKILL）——opencode→bash→eval shim→yosys 全树都被收掉 |
| 失败不丢结果 | 框架兜底最终评测（opencode_backend.py:500-522：agent 被杀后 harness 自己再跑一次最后的 workspace 状态） |
| 停止条件 | 时间到（自动终止）/ max_steps（react）/ nudge 无产出（停催）；"同类错误重复出现"等启发式留给提示词判断 |

> **对我们的结论**：`remaining_time` + 自动终止 + "被杀也不丢结果"这套组合对 6 小时赛制是现成模板。

---

## 三、Harness 的设计点 → RTLScout 的实现

### 3.1 统一、简单的执行入口 → `evaluate_design` 包装脚本

- `write_eval_wrapper`（opencode_backend.py:272-288）在 workspace 生成可执行 `./evaluate_design [design_file]`，内部转发到 `python -m core.eval_store --workspace ... --run-root ...`
- 配置随 `_eval_config.json` 一次性写入（opencode_backend.py:255-269）：top module、cost metric、target_delay、technology、language、CEC 开关与 golden 路径——**模型永远不需要拼接任何 EDA 命令**
- 按题型拆分（evaluate_rtl.sh / evaluate_ppa.sh / ...）在 RTLScout 中等价于：同一入口 + 不同的 `_eval_config.json`（不同 cost_metric/technology/language）

### 3.2 固定工具参数与评测环境 → 配置一次写入 + 基准输入供给

- **评测参数**：`_eval_config.json`（设计顶层、成本指标、工艺 asap7/nangate45、target_delay、energy_exp）——每次评测同一份
- **工具参数**：`verilator_common_flags` 固定列表（correctness.py:61-71，`-Wall -Wno-*` 等）；CEC 流程固定（equivalence.py:50-58 的 yosys 脚本）
- **环境**：`provision_workspace`（runner.py:151-210）从**基准目录**拷贝 tb.sv、全部 `*.dat`、context/ ——候选 A/B 用同一套输入，指标才有比较意义
- **工具版本**：opencode 版本钉死并记录（`OPENCODE_PINNED_VERSION`，opencode_backend.py:37）；EDA 工具靠镜像锁定（README 说明全流程在预构建镜像内，版本随镜像固化）

### 3.3 分层执行短路 → 编译→lint→仿真→成本→CEC，带条件门

`evaluate()`（evaluation.py:306-420）的执行顺序，天然是短路链：

```
Spire/Amaranth 编译（失败 => 立即返回 FAIL，不再跑任何东西）   evaluation.py:347-383
  ↓
Verilator lint（失败 => passed=False）                        correctness.py:179-181
  ↓
Verilator 仿真（失败 => passed=False）
  ↓
成本度量（独立于正确性，但 best 门槛要求 passed）
  ↓
CEC（仅当仿真通过 且 提供了 golden_reference 才跑）            evaluation.py:393-403
```

> **对我们的结论**：RTLScout 的短路在"编译失败立即返回"和"CEC 仅在通过后跑"两处最彻底；cost 仍会跑（因为要记录指标）。**我们做 PPA 题时可以更激进**：sim 失败时跳过 Yosys/OpenSTA（官方评测只看功能对不对时，这个优化能省下大把时间）——这是我们要自建的增强点。

### 3.4 解析原始日志 → 三层提取

1. **逐项检查解析**：`parse_testbench_checks`（correctness.py:107-130）——仿真输出里找 `TB_SUMMARY total=N errors=M` 行，展开为 N 个 check（passed/failed），从而得到"通过/失败测试数"；解析失败时抛出带输出尾部的异常（绝不静默）
2. **标量统计**：`parse_sim_stats`（correctness.py:133-155）——`TB_CYCLES total=C` / `TB_READS` / `TB_WRITES`，供能量类指标用
3. **压缩成短摘要**：`EvaluationResult.summary_str`（evaluation.py:88-133）——把数千行日志压成固定格式：`Correctness: PASS/FAIL → Lint → Sim → Checks(ok/tot) → 截断的 lint/sim 输出 → Cost 指标 → 最差时序路径（中段省略保留首尾）→ CEC 结论`；`_truncate` 中间省略（evaluation.py:43-50）

成本侧同样：`metrics()` 只暴露标量（evaluation.py:68-74），`worst_timing_path` 等非标量走独立字段并截断到 4500 字符。

### 3.5 输出统一结构 → JSON（to_dict）+ 文本（summary_str）双格式

`EvaluationResult.to_dict`（evaluation.py:135-172）就是你要的 JSON：

```json
{
  "passed": true,
  "pass_rate": 1.0,
  "cost_value": 1772,
  "cost_metric": "area",
  "metrics": { "area": 1772, "delay": 3.85 },
  "worst_slack": 0.15,
  "worst_timing_path": "...",
  "correctness": { "passed": true, "lint_ok": true, "sim_ok": true,
                   "total_checks": 12, "passed_checks": 12, "pass_rate": 1.0,
                   "sim_stdout": "...(截断)" },
  "cost": { "ok": true, "value": 1772, "error": "" },
  "cec": { "ran": true, "equivalent": true }
}
```

分工完全符合你的设计：**模型平时读 summary_str 文本（agent 视角），JSON 落盘供 harness/人/后续工具消费**；原始日志（sim stdout/stderr 截断、worst timing path）作为按需深挖的入口。

### 3.6 超时与异常处理 → 每个子进程独立超时 + 错误显式化

| 场景 | 处理 |
|---|---|
| 编译/仿真/CEC 超时 | `_run(..., timeout)` 捕获 `TimeoutExpired` → `SimResult(ok=False, stderr="Timeout expired")`（correctness.py:43-58）；编译超时（evaluation.py:245-254）；CEC 超时（equivalence.py:129-133） |
| 成本工具超时 | 各 CostMetric 自带超时，错误信息如 `"<metric> timed out after Xs"`（cost.py:310） |
| 工具崩溃/输出缺失 | `CostResult(ok=False, error=...)`，`cost_value=None` ——**绝不会出现"空文件被当成指标为零"** |
| 恶意/崩溃的候选 | reeval 对 adversarial `.py` 异常兜底：记录 `error` 字段并置 `passed=False`（reeval.py:117-122） |
| 评测 shim 半截写入 | `read_evals` 容忍 torn line（eval_store.py:112-117），已完成 eval 不丢 |

关键原则：**所有失败都有显式结构化表达（ok=False + error 字段），不依赖空输出传达失败**——正是你强调的。

### 3.7 工作目录隔离 → 三层目录树 + 可选容器级隔离

```
runs/<benchmark>/<model>/<timestamp>/     ← 一次 run（runner.py:243-245）
├── workspace/                            ← agent 的当前工作区
├── eval_1/  eval_2/ ...                  ← 每轮快照（workspace + result.json + summary.txt）
├── best_design/                          ← 已验证最优
├── agent_evals.jsonl                     ← 全部评测的追加日志
└── result.json / summary.txt / chat_log.txt
```

- 每轮之间：`obj_dir` 清空重建（agent.py:571-574），互不污染
- 权威重算：全新 `tempfile.mkdtemp` judge 工作区（reeval.py:96-100）
- **容器级隔离**（进阶模式）：`ContainerSandbox`（sandbox.py:157-247）为每个 agent run / 每个待评分候选 `docker run --rm` 一个全新容器，identity mount（host 路径==容器路径，绕开 docker-in-docker 路径陷阱），label（`rtlscout.*`）管理，`--user uid:gid` 保证可写，network/cpu/memory 限制

### 3.8 自动保存与回滚 → 保存全自动，回滚靠"best 口径"

- **保存**：引擎自动——每轮 eval 快照、best 自动刷新（见 2.6）。没有"要不要存"的人工环节
- **回滚**：RTLScout 没有显式 `restore_best` 命令——回滚体现在两个层面：
  1. **引擎不认账**：改坏了就只是"多一条 eval 记录"，best 不动
  2. **提交口径**：最终提交/播种只从 `best_design/` 取
- **决策分工**：agent 只产生候选与评测；"是否 best"由 `select_best_eval` 纯函数判定（eval_store.py:71-99）——**决策在引擎、执行在引擎**，模型无法干预

> **对我们的结论**：可以加 `save_best.sh / restore_best.sh` 让"把 best 拷回 current 继续改"更方便（比赛时我们人会用），但判定逻辑必须留在脚本/引擎里。

### 3.9 保证评测不可被候选污染 → 权威重算（本仓库最有价值的机制）

`core/reeval.py` 是 RTLScout 的安全核心，四层防线：

1. **权威重算**：agent 结束后，对每个 `eval_{i}/` 在**全新工作区**里重跑评测——工作区由 `provision_workspace` 用**基准自己的输入**（tb.sv、*.dat、context）搭好，只覆盖 agent 的**设计源文件**（reeval.py:96-102）
2. **永不取自 agent 的黑名单**：`_NEVER_FROM_AGENT` = {tb.sv, obj_dir, _cec, _golden, _best_meta.json, result.json, summary.txt, agent_evals.jsonl, .spire_cache}（reeval.py:34-37）——benchmark 的 testbench/数据永远赢
3. **一致门（agreement gate）**：对比 advisory 与 authoritative 的 pass 与 cost（相对误差 > 1e-3 记 diverged）（reeval.py:259-280）——**防作弊也防非确定性**
4. **篡改特征扫描**：对会话日志正则扫 `tb.sv`、`run_eval.py`、`PATH=` 修改等可疑痕迹（reeval.py:41-47, 139-153）

配套（`opencode_backend.py:11-17` 注释的信任模型）：**opencode 有 shell，其自报分数永远不可信，reeval 是强制步骤**（`BackendConfig.wants_reeval`，agent_backend.py:84-88）。

> **对我们的结论**：比赛场景没有恶意 agent（题目和评测是官方的），但**非确定性和误判风险完全真实**——"提交前用基准输入独立重跑一遍"这个习惯直接照搬，成本极低收益极高。

### 3.10 可复现性 → 版本钉死 + provenance 记录 + 一致门兜底

- opencode 版本钉死 `OPENCODE_PINNED_VERSION=1.17.11`，每次 run 写 `_opencode_provenance.json`（opencode_backend.py:598-620：pinned version、model、argv、returncode、timed_out、nudge 轮数、会话导出结果）
- 评测输入全部来自基准 + 固定 flags（3.2）
- **诚实说明局限**：EDA 工具版本依赖镜像（orfs:latest 未钉 commit——这正是我们交接说明里标记的已知问题）；yosys/abc 的随机种子未锁 → 一致性门（3.9）作为非确定性的最后兜底，agent 自报与权威分不一致会被标记

---

## 四、大脑与 Harness 的接口 → 一条命令 + 两份文件

| 方向 | RTLScout 的实现 |
|---|---|
| 大脑 → Harness | `./evaluate_design [design_file]`（= `python -m core.eval_store`，配置读 `_eval_config.json`）；react 后端等价物是 `run_evaluation` 工具调用（agent.py:145-153） |
| Harness → 大脑 | 文本 `summary_str()`（含 `Best so far: <cost> <metric> (eval N)` 行）；完整 JSON 落盘到 `eval_{i}/result.json` + 追加进 `agent_evals.jsonl` |
| 状态 | 完全无共享——shim 每次从文件恢复索引（eval_store.py:121-148）；"one run == one fresh session == one fresh context"（agent_backend.py:11-13），跨 run 只传种子文件与经验文本 |

接口的松耦合程度：**换评测工具（Icarus→Verilator→Yosys→OpenROAD→KLayout）只需要换 `evaluate()` 内部与 cost_metric 实现，大脑和接口不动**——这正是"大脑与工具链可独立修改"的工程保证。

---

## 五、四道题的分工映射与覆盖缺口

| 题型 | 大脑职责（RTLScout 提示词覆盖） | Harness 职责（RTLScout 实现） | RTLScout 覆盖度 |
|---|---|---|---|
| RTL 补全 | 定位逻辑/时序/reset/位宽问题（prompt 策略 + 仿真失败信息反馈） | Verilator lint+sim、TB_SUMMARY 逐项解析、第一个失败信息 | **完全覆盖**（这是它的主场景） |
| RTL PPA | 结构选择（算术结构、寄存器、MUX 深度） | Yosys stat 快指标、OpenROAD STA 工艺级 area/delay/power、CEC 守门 | **完全覆盖**（cost.py 全系指标即为此设计） |
| 全局布线 | 选择和调整 Tcl 参数 | OpenROAD 跑分、提取 congestion/overflow/wirelength | **未覆盖**——需自建 harness（复用骨架：入口+快照+权威重算） |
| DRC 修复 | 判断移动/修改哪些图形 | KLayout 跑分、提取违规数与坐标 | **未覆盖**——需自建 harness（复用骨架） |

**迁移要点**：布线/DRC 两题没有现成实现，但"eval 入口 → 快照 → 权威重算 → best 管理"骨架 100% 复用；差异只在 `evaluate()` 内部换成 OpenROAD/KLayout 命令与各自的日志解析。RTLScout 的 `_eval_config.json` 模式（一份配置文件驱动评测）天然支持扩展。

---

## 六、最小可用方案对照

| 你规划的最小版本 | RTLScout 的对应最小件 | 文件 |
|---|---|---|
| 题目包（problem.md/残缺 RTL/tb） | `benchmarks/<name>/` = description.txt + metadata.json + tb.sv + context/ | 直接照抄格式 |
| evaluate.sh | `evaluate_design` 包装 + `python -m core.eval_store` | opencode_backend.py:272-288、eval_store.py |
| parse_result.py | `parse_testbench_checks` + `summary_str` + `to_dict` | correctness.py、evaluation.py |
| result.json | `eval_{i}/result.json` + `agent_evals.jsonl` + `best_design/_best_meta.json` | eval_store.py |
| logs/ | `SimResult` 捕获 stdout/stderr + eval 快照 | correctness.py:11-17、agent.py:543-557 |
| AGENTS.md + rtl_skill.md | AGENTS.md 渲染器（任务+工作流+参考指针） | agents_md.py |
| 独立复评 | `reeval_run`（基准输入 + 一致门） | reeval.py |

**fake provider 冒烟测试**（无需 API Key 跑通全链路）：`core/fake_provider.py` + `run_benchmark.py --model fake:...`——我们的 DeepSeek Key 到位前，可以照此思路用假模型先验证 harness 骨架。

---

## 七、对 EDAthon 的迁移结论

**直接照抄（现成模板）：**

1. 题目包格式（description.txt/metadata.json/tb.sv/context）——我们造模拟题直接用
2. `evaluate_design` 统一入口 + `_eval_config.json` 配置模式——四类题共用一个循环
3. 快照与 best 管理（eval_i/ + agent_evals.jsonl + best_design/_best_meta.json）——回滚与版本选择的基础
4. 权威重算 + 一致门——提交前用基准输入独立复跑（防非确定性）
5. AGENTS.md 渲染方式：任务/工作流/参考指针三段式，硬约束"提示词+引擎"双保险
6. `remaining_time` + 自动终止 + 进程组击杀 + 被杀不丢结果——6 小时赛制时间盒
7. nudge 三守卫（剩余时间/轮数/无产出）
8. `TB_SUMMARY`/`TB_CYCLES` 测试台输出约定——让 parse 通用
9. CEC（yosys-abc cec，golden reference）——PPA 题功能守门
10. 无状态 shim（文件即记忆）——不依赖长驻进程，适合比赛现场随时起停

**必须自建（RTLScout 没有）：**

1. 布线题的 OpenROAD harness（提取 congestion/overflow/wirelength/via + WNS/TNS）
2. DRC 题的 KLayout harness（规则/层/坐标解析 + 新增违规检测 + 连通性检查）
3. DeepSeek provider 接入（RTLScout 支持 DeepInfra/Anthropic/OpenRouter，需仿照加 deepseek，或用 OpenAI 兼容端点直连）
4. 我们自己的 `skills/`（rtl_debug.md、ppa_optimization.md、routing_optimization.md、drc_repair.md——按"指针进 AGENTS.md"方式挂载）
5. 更激进的短路：sim 失败跳过综合/STA（PPA 题省时）

**不照搬：** Spire/Amaranth 语言流、design DB 子电路库、多 run 精英池（比赛初期）、Mockturtle。

---

## 附录：关键文件索引

| 文件 | 长度 | 关注点 |
|---|---|---|
| `core/opencode_backend.py` | 631 | 每次 run 的完整生命周期（渲染→启动→nudge→最终评测→总结→导出→provenance） |
| `core/agents_md.py` | 207 | AGENTS.md 结构（任务/工作流/参考/优化指导/种子） |
| `core/prompts.py` | 845 | react 系统提示词：策略步骤、硬规则、技巧、参考注册表 |
| `core/agent.py` | 849 | react 循环：7 工具、文件保护、best 追踪、快照 |
| `core/evaluation.py` | 420 | 评测管线 + summary_str/to_dict 双输出 |
| `core/correctness.py` | 200 | Verilator lint/sim + TB_SUMMARY/TB_CYCLES 解析 |
| `core/cost.py` | 1629 | CostMetric 抽象 + 无工艺/工艺级指标全系 |
| `core/equivalence.py` | 205 | CEC（Yosys→BLIF→yosys-abc cec） |
| `core/eval_store.py` | 249 | 无状态评测 shim + 快照/best 落盘 |
| `core/reeval.py` | 373 | 权威重算 + 一致门 + 篡改扫描 |
| `core/sandbox.py` | 277 | Local/Container 沙箱 + 进程组超时击杀 |
| `core/containers.py` | 88 | label 化容器清理 |
| `core/runner.py` | 540 | provision_workspace + runs 目录树 |
| `core/agent_backend.py` | 187 | RunLimits/BackendRequest/后端选择 |
| `core/multirun.py` | 808 | 精英池（max_size/温度/softmax 采样/播种） |
| `core/fake_provider.py` | 166 | 无 API 冒烟测试 |
