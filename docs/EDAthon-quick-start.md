# EDAthon 快速上手流程

这份文档整理一个轻量的本地练习流程，覆盖 RTL 修复、PPA 感知 RTL 优化、DRC 修复和 OpenROAD routing closure。

它是队内练习笔记，不是官方赛题答案。

## 环境检查

如果工具通过 Docker 镜像提供，先检查本地镜像：

```powershell
docker images
```

然后在仓库根目录验证工具链：

```powershell
docker run --rm -v "${PWD}:/workspace" -w /workspace edathon-openroad-tools:local bash -lc "which iverilog && which vvp && which yosys && openroad -version && python3 --version"
```

期望能找到这些工具：

- `iverilog` 和 `vvp`：用于 Verilog 仿真
- `yosys`：用于综合和 cell count 检查
- `klayout`：用于 layout DRC
- `openroad`：用于物理设计流程实验

不要提交本地 API key、`.env`、OpenCode provider 配置、仿真生成文件或 OpenROAD 运行目录。

## RTL 修复流程

修复前后使用同一条命令：

```sh
iverilog -g2012 -o sim.out <dut>.v <tb>.v && vvp sim.out
```

调试顺序：

1. 如果 `iverilog` 失败，这是 compile error。优先检查语法、模块名、端口列表和缺失分号。
2. 如果 `vvp sim.out` 输出 `FAIL` 或 `$fatal`，这是 functional failure。读取失败向量，只修 DUT。
3. testbench 是规格说明，通常不要改。
4. 重跑同一条命令，直到输出 `PASS`。

## PPA 优化流程

PPA 题先保证功能等价，再比较综合结果：

```sh
iverilog -g2012 -o sim.out ppa_reference.v ppa_target.v tb_ppa_factor.v && vvp sim.out
yosys -p "read_verilog ppa_target.v; synth -top ppa_target; stat"
```

只有同时满足下面两点，才能说优化成功：

- 仿真仍然通过。
- 被优化的综合指标确实改善。

对于小 RTL 例子，Yosys cell count 只是面积代理指标，适合练习。正式比赛可能还会用 timing、power 和 technology-mapped flow。

## DRC 修复流程

生成 layout 并运行 DRC：

```sh
klayout -b -r make_layout.rb
klayout -b -r rules.drc -rd input=layout.gds -rd report=drc_report.lyrdb
```

调试顺序：

1. 读取 violation 类别，例如 minimum width 或 minimum spacing。
2. 把 database unit 换算成 micron。
3. 修改 layout generator，不改 DRC 规则。
4. 重跑 DRC，确认最终 report 中没有 violation item。

## OpenROAD Routing Closure 流程

对于 global routing 实验：

1. 先通过 flow 生成有效的 OpenROAD database。
2. 运行题目 Tcl 脚本。
3. 如果 global route 失败，查看 congestion 指标。
4. 只修改题目脚本中暴露出的 flow/routing 参数。
5. 不要修改 technology file 或 platform rule。

常看的报告字段：

- `Total Congestion`
- `Max H`
- `Max V`
- per-layer resource usage

## 队内 Git 提交流程

练习材料不要直接在 `main` 上提交，先开自己的 branch。

```sh
git status
git pull
git switch -c miya/edathon-workflow-notes
git add docs workspace
git diff --cached
git commit -m "add EDAthon practice workflows and prompt guides"
git push -u origin miya/edathon-workflow-notes
```

命令含义：

- `git status`：查看当前有哪些改动。
- `git pull`：开 branch 前先同步远程最新代码。
- `git switch -c`：创建自己的贡献分支。
- `git add`：选择要放进 commit 的文件。
- `git diff --cached`：检查即将提交的内容。
- `git commit`：在本地创建一个提交点。
- `git push`：把 branch 上传到 GitHub。

push 后在 GitHub 上打开 Pull Request，让队友 review 后再 merge 到主分支。
