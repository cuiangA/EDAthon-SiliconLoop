# 05_ppa_factor

EDAthon 风格 PPA 感知 RTL 优化小练习。

目标行为：

```verilog
y = (a & b) | (a & c)
```

优化实现使用布尔代数因式分解：

```verilog
y = a & (b | c)
```

这个变换保持功能不变，同时在这个小型 Yosys cell-count 实验中减少综合后的门数量。

## 文件

- `ppa_reference.v`：仿真参考行为
- `ppa_baseline.v`：故意保留较低效结构，用于面积对比
- `ppa_target.v`：优化后的实现
- `tb_ppa_factor.v`：功能等价 testbench

## 功能检查

```sh
iverilog -g2012 -o sim.out ppa_reference.v ppa_target.v tb_ppa_factor.v && vvp sim.out
```

期望输出：

```text
PASS: ppa_target is functionally equivalent to ppa_reference
```

## Yosys Cell Count

基线版本：

```sh
yosys -p "read_verilog ppa_baseline.v; synth -top ppa_baseline; stat"
```

优化版本：

```sh
yosys -p "read_verilog ppa_target.v; synth -top ppa_target; stat"
```

本地观察结果：

- baseline：24 cells，包含 16 个 `$_AND_` 和 8 个 `$_OR_`
- optimized target：16 cells，包含 8 个 `$_AND_` 和 8 个 `$_OR_`

这是一个小型训练例子。正式 PPA 评分可能会使用 timing、power 和 technology-mapped flow，而不只是 generic cell count。
