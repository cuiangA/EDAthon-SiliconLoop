# EDAthon 比赛 Prompt 速查

这份文档整理 EDAthon 风格题目的常用 Prompt。目标不是让 AI 只给建议，而是让它同时给出：

1. 要执行的具体命令。
2. 期望输出或失败现象。
3. 看到结果后的下一步操作。
4. 最终可复查的修复报告。

不要把 API key、`.env`、provider 配置或私人路径贴进 Prompt。

## P1：RTL 修复题 Prompt

适用于编译错误或功能仿真失败。

```text
You are helping with an EDAthon RTL repair task.

Directory: <lab directory>
Files:
- <dut>.v is the design under test.
- <tb>.v is the testbench and must not be modified.

Please:
1. Run:
   iverilog -g2012 -o sim.out <dut>.v <tb>.v && vvp sim.out
2. Classify the result as compile error or functional simulation failure.
3. If it fails, identify the smallest likely bug in <dut>.v only.
4. Do not modify the testbench or module interface.
5. After the fix, rerun the same command.
6. Report:
   - What failed
   - Root cause
   - Which line changed
   - Final compile result
   - Final simulation result
```

期望最终输出：

```text
PASS: <module name>
```

## P2：PPA 感知 RTL 优化题 Prompt

适用于功能已经正确，但希望综合后面积更小、逻辑更简单的题目。

```text
You are helping with an EDAthon PPA-aware RTL optimization task.

Files:
- ppa_reference.v defines the required behavior.
- ppa_target.v is the implementation to optimize.
- tb_ppa_factor.v checks functional equivalence.

Rules:
- Modify only ppa_target.v.
- Keep the module name and port list unchanged.
- Simulation correctness is required before comparing area.

Please run:
iverilog -g2012 -o sim.out ppa_reference.v ppa_target.v tb_ppa_factor.v && vvp sim.out

Then run Yosys statistics:
yosys -p "read_verilog ppa_target.v; synth -top ppa_target; stat"

Find a small algebraic or structural RTL rewrite that preserves behavior and
reduces the Yosys cell count. After changing the RTL, rerun both commands and
write a short report with baseline result, transformation, final result, and
cell-count change.
```

## P3：OpenROAD Global Routing Closure Prompt

适用于 OpenROAD 全局布线脚本因为拥堵失败的题目。

```text
You are helping with an EDAthon OpenROAD global routing closure task.

Script: <global_route_script>.tcl

Please:
1. Run the OpenROAD script.
2. If it fails, identify whether the failure is congestion, missing input files,
   or a Tcl/script error.
3. For congestion, inspect Total Congestion, Max H, Max V, and per-layer usage.
4. Modify only the tunable routing or flow parameter in the task script.
5. Do not modify technology files, LEF/Liberty files, or OpenROAD source scripts.
6. Rerun the script and report:
   - Baseline failure type
   - Failed routing metric
   - Parameter changed
   - Why the change helps
   - Final congestion
   - Whether global route passed
```

常见可调参数包括 routing capacity adjustment、congestion iterations、placement
density、route layer 设置等。前提是这些参数是题目脚本中暴露出来的 tunable，不要直接改工艺库或官方流程脚本。

## P4：DRC 修复题 Prompt

适用于 KLayout 报告 layout rule violation 的题目。

```text
You are helping with an EDAthon DRC repair task.

Files:
- make_layout.rb generates the layout.
- rules.drc defines the DRC rules and must not be modified.

Please:
1. Generate the layout.
2. Run KLayout DRC.
3. Read the DRC report and classify the violations by rule category.
4. Modify only make_layout.rb.
5. Do not delete shapes to bypass the check.
6. Rerun DRC and report:
   - Baseline DRC result
   - Failed rule categories
   - Geometry causing the failure
   - Coordinate or size changes
   - Final DRC result
```

对于几何类 DRC 题，修改坐标前一定先把 database unit 换算成 micron，避免凭感觉移动图形。
