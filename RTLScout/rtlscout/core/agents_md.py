"""为 OpenCode 运行渲染 AGENTS.md —— 每种 HDL 一个精简渲染器。

OpenCode agent 拥有真实的 shell 和读权限,因此这些提示词刻意保持精简:
任务/目标 → 工作流(共享的执行部分)→ 精简的 HDL 要点 → 参考资料指针
(按需读取)→ 优化指引 → 种子设计。它删去了 react 循环的机制细节
(内部工具列表 ``create_file``/``run_evaluation``/``done``、"总是调用工具"
规则、步数预算),因为当 agent 拥有 shell 时这些都不适用——因此 react
提示词所需的"忽略那些工具说明"覆盖在这里也没有必要。

各语言的差异集中在 ``_CFG`` 中:
  - Spire:内联精选提示(``deps/spire-hdl/docs/hints.md``)+ 指向 spire-hdl
    的 README;支持优化装饰器标志。
  - Amaranth:一段简短的内联说明(其 API 并非广为人知,仓库内也没有
    可读的文档)+ 指向参考设计。
  - Verilog:一行说明 + 指向参考设计。

复用 ``core/prompts.py`` 中的参考注册表;优化指引以简短指针形式输出
(OpenCode agent 可自行读取所引用的 README)。
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from core.prompts import AMARANTH_REFERENCES, SPIREHDL_REFERENCES, VERILOG_REFERENCES, _SPIRE

if TYPE_CHECKING:
    from core.agent_backend import BackendRequest

# spire-hdl 在主 README 旁附带主题 README——这里只给指针(不内联),
# 让拥有 shell 的 agent 按需读取。
# README.md 位于 spire-hdl 根目录;主题 README 位于 docs/ 下(Spire >= 0.2.0)。
_SPIRE_DOC_READMES = [
    ("README.md", "main Spire overview — start here"),
    ("docs/README_arithmetic_generator.md", "configurable multiplier/adder generators"),
    ("docs/README_arithmetic_optimization.md", "arithmetic architecture optimization"),
    ("docs/README_optimization_decorators.md", "@abc_optimized / etc."),
    ("docs/README_fsm_optimization.md", "FSM / state-encoding optimization"),
    ("docs/README_state_machines.md", "state machines"),
    ("docs/README_control_structures.md",
     "if_/switch_ control structures + selection emission modes "
     "(selection_topology('tournament'/'onehot'/'bittree') — log-depth mux-cascade rewrites)"),
    ("docs/README_reductions.md",
     "balanced log-depth reduction trees (spire.reduce: max_/min_/argmax_/sum_/reduce_tree/prefix_scan "
     "— loop-built running max/min chains are O(N) deep and synthesis cannot rebalance them)"),
    ("docs/README_composite_types.md", "structs / arrays / composite types"),
    ("docs/README_memories.md", "memories"),
    ("docs/README_custom_verilog.md", "embedding custom Verilog"),
]

_VERILOG_ESSENTIALS = (
    "## Verilog notes\n\n"
    "Write synthesizable Verilog/SystemVerilog directly in `design.sv` (split helpers across "
    "files if useful). The module name and ports must match the specification exactly. Your "
    "design is checked for correctness (Verilator simulation against the testbench) and cost "
    "(Yosys synthesis)."
)

_AMARANTH_ESSENTIALS = (
    "## Amaranth notes\n\n"
    "Amaranth HDL is a Python library that generates synthesizable Verilog via Yosys. Define "
    "your design as an `Elaboratable`, then convert it to Verilog and write `design.v`:\n\n"
    "```python\n"
    "from amaranth import *\n"
    "from amaranth.back.verilog import convert\n\n"
    "class MyDesign(Elaboratable):\n"
    "    def __init__(self):\n"
    "        self.a = Signal(8); self.b = Signal(8); self.y = Signal(8)\n"
    "    def elaborate(self, platform):\n"
    "        m = Module()\n"
    "        m.d.comb += self.y.eq(self.a + self.b)\n"
    "        return m\n\n"
    "top = MyDesign()\n"
    "with open('design.v', 'w') as f:\n"
    "    f.write(convert(top, ports=[top.a, top.b, top.y], name='<module_name>'))\n"
    "```\n\n"
    "The emitted module name and ports must match the specification exactly. Your working "
    "directory is on the Python path, so `from helper import ...` works."
)

# 语言 -> (HDL 名称, 参考注册表, 文档 README 列表, 内联要点, 是否支持优化标志)
_CFG = {
    "verilog":  dict(hdl="Verilog / SystemVerilog", refs=VERILOG_REFERENCES, doc_readmes=[],
                     essentials=_VERILOG_ESSENTIALS, opt_flags=False),
    "amaranth": dict(hdl="Amaranth HDL (Python → Verilog)", refs=AMARANTH_REFERENCES,
                     doc_readmes=[], essentials=_AMARANTH_ESSENTIALS, opt_flags=False),
    "spirehdl": dict(hdl="Spire HDL (Python EDSL → Verilog)", refs=SPIREHDL_REFERENCES,
                     doc_readmes=_SPIRE_DOC_READMES, essentials=None, opt_flags=True),
}

# Spire 精选提示文件的位置(hints.md),位于 spire-hdl 仓库的 docs/ 目录下
_HINTS_PATH = _SPIRE / "docs" / "hints.md"


def _demote_headings(md: str) -> str:
    """为每个 markdown 标题前添加一个 '#',使外部文档嵌套在当前 AGENTS.md 之下。
    感知代码块:绝不触碰 ``` 代码块内部的 '#' 注释。"""
    out, in_fence = [], False
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("#"):
            line = "#" + line
        out.append(line)
    return "\n".join(out)


def _objective(req: "BackendRequest", metric_name: str, cfg: dict) -> str:
    """构造开头部分:任务标题 + 规格说明 + 优化目标(正确性优先,再最小化成本)。"""
    # 若成本度量带有说明(metric_note),则追加到目标段落末尾
    note = getattr(req.cost_metric, "metric_note", "") if req.cost_metric else ""
    note_line = f"\n\n**Cost metric `{metric_name}`:** {note}" if note else ""
    return (
        f"# Task — optimize a {cfg['hdl']} design\n\n"
        f"## Specification\n{req.benchmark.description}\n\n"
        f"## Objective\n"
        f"Write a **functionally correct** design (module name + ports must match the spec "
        f"exactly), then minimize **{metric_name}** without breaking correctness. Correctness "
        f"first, then cost.{note_line}"
    )


def _essentials(cfg: dict) -> str:
    """精简的 HDL 要点。Spire 内联精选提示文件(标题降级一级);
    verilog/amaranth 使用简短的内联说明。"""
    if cfg["essentials"] is not None:
        return cfg["essentials"]
    if _HINTS_PATH.exists():
        return _demote_headings(_HINTS_PATH.read_text().strip())
    return (f"## Spire essentials\n\nRead `{_HINTS_PATH}` for the key API + common mistakes, "
            f"then the READMEs below.")


def _references(cfg: dict) -> str:
    """生成"参考资料与示例"小节:指示 agent 用 cat 自行阅读文件,而非内联在提示词中。"""
    lines = [
        "## Reference docs & examples",
        "",
        "You have a shell and read access — **read these files yourself with `cat` instead of "
        "guessing.** They are not inlined here, to keep this prompt small.",
    ]
    if cfg["doc_readmes"]:
        lines += ["", "**Docs (start with the main README):**"]
        lines += [f"- `{_SPIRE / fname}` — {desc}" for fname, desc in cfg["doc_readmes"]]
    if cfg["refs"]:
        lines += ["", "**Reference implementations / examples (read the ones you need):**"]
        lines += [f"- `{ref['path']}` — {ref['description']}" for ref in cfg["refs"]]
    return "\n".join(lines)


def _optimization_guidance(req: "BackendRequest", cfg: dict) -> str:
    """react 提示词中优化指引的精简指针版。react 循环会内联 spire-hdl 的优化
    README(它没有 shell);OpenCode agent 可以自行 cat,因此这里只强调
    本次运行启用了哪些能力,并指向要阅读的文档。"""
    if not cfg["opt_flags"]:
        return ""

    # R: 生成指向 spire-hdl 优化文档的路径引用(渲染为内联代码)
    def R(name):
        return f"`{_SPIRE / 'docs' / name}`"

    items = []
    if req.abc_optimize:
        items.append(f"- **`@abc_optimized`** — wrap combinational logic with the decorator that "
                     f"runs an ABC logic-synthesis script over it. See {R('README_optimization_decorators.md')}.")
    if req.arith_autoconfig:
        items.append(f"- **`replace_arithmetic_ops()` / `@arithmetic_optimized`** — reconfigure how "
                     f"`*`/`+`/etc. map to multiplier/adder architectures instead of the default "
                     f"operator mapping (apply it targeted to dedicated parts of the design, not as a "
                     f"blanket whole-design pass). See {R('README_arithmetic_optimization.md')}.")
    if req.fsm_optimize:
        items.append(f"- **FSM / state-encoding** — the `State` API plus the `optimized_fsm` / "
                     f"`optimized_encoding` wrappers, for alternative state encodings on sequential "
                     f"designs. See {R('README_fsm_optimization.md')} and {R('README_state_machines.md')}.")
    if req.flowy_optimize:
        items.append(f"- **`@flowy_optimized`** (Mockturtle) — combinational optimization via "
                     f"Mockturtle. See {R('README_optimization_decorators.md')}. **Note:** Mockturtle "
                     f"is not in the default image, so this only helps in a flowy-enabled environment.")
    if req.dont_touch_main_arith:
        items.append("- **Do not touch the main arithmetic** — do **not** modify the core "
                     "`MultiplierConfig` / `AdderConfig`; optimize everything else.")
    if not items:
        return ""
    return ("## Optimization guidance (enabled for this run)\n\n"
            "These synthesis-aware capabilities are highlighted. You already have the Spire READMEs "
            "and source pointed at above — read the referenced doc for the exact API; the notes "
            "below are the emphasis.\n\n" + "\n".join(items))


def _seed(seed_text: str) -> str:
    """生成"种子设计与前序 agent 的经验"小节;种子文本为空时返回空串。"""
    return ("## Seed design & lessons from previous agents\n\n" + seed_text.strip()
            if seed_text and seed_text.strip() else "")


def render_opencode_agents_md(req: "BackendRequest", *, execution_section: str,
                              metric_name: str, seed_text: str = "") -> str:
    """组装完整的 AGENTS.md,用于任何受支持 HDL 的 OpenCode 运行。

    ``execution_section`` 是后端构建的共享 OpenCode 工作流块(shell、
    ./evaluate_design、./remaining_time、时间预算、收尾)——传入进来
    以确保各语言之间只保留一份副本。
    """
    # 按语言取配置;未知语言回退到 Verilog
    cfg = _CFG.get(req.language, _CFG["verilog"])
    # 依序组装各小节,过滤空小节后以空行拼接
    sections = [
        _objective(req, metric_name, cfg),
        execution_section,
        _essentials(cfg),
        _references(cfg),
        _optimization_guidance(req, cfg),
        _seed(seed_text),
    ]
    return "\n\n".join(s for s in sections if s) + "\n"
