# 07_openroad_grt_closure

EDAthon 风格 OpenROAD global-routing closure 小练习。

这个实验使用 OpenROAD-flow-scripts 的 `nangate45/gcd` 设计作为本地替代案例，用来练习 congestion diagnosis。

它不是官方赛题，只是队内练习材料。

## 文件

- `p3_low_capacity_grt_bad.tcl`：故意过度削减 routing capacity
- `p3_low_capacity_grt_fixed.tcl`：放宽 capacity reduction，使 global route 能通过

两个脚本都假设 `gcd` flow 已经生成：

- `/OpenROAD-flow-scripts/flow/results/nangate45/gcd/base/4_cts.odb`
- `/OpenROAD-flow-scripts/flow/results/nangate45/gcd/base/4_cts.sdc`

## 生成基线设计并运行 bad case

在仓库根目录运行：

```powershell
docker run --rm -v "${PWD}:/workspace" -w /OpenROAD-flow-scripts/flow edathon-openroad-tools:local bash -lc "make DESIGN_CONFIG=./designs/nangate45/gcd/config.mk SKIP_CTS_REPAIR_TIMING=1 && openroad /workspace/workspace/07_openroad_grt_closure/p3_low_capacity_grt_bad.tcl"
```

期望 bad case 结果：

- OpenROAD 报告 global-routing congestion。
- 本地观察到的 baseline 为 `Total Congestion = 295`。

## 运行 fixed case

```powershell
docker run --rm -v "${PWD}:/workspace" -w /OpenROAD-flow-scripts/flow edathon-openroad-tools:local bash -lc "make DESIGN_CONFIG=./designs/nangate45/gcd/config.mk SKIP_CTS_REPAIR_TIMING=1 && openroad /workspace/workspace/07_openroad_grt_closure/p3_low_capacity_grt_fixed.tcl"
```

期望 fixed case 结果：

- global route 不再因为 congestion 报错
- 本地观察到最终 `Total Congestion = 0`

## 修复说明

bad 脚本使用：

```tcl
set_global_routing_layer_adjustment metal2-metal10 0.95
```

这会留下过少 routing capacity，从而制造一个可控的 congestion failure。fixed 脚本使用：

```tcl
set_global_routing_layer_adjustment metal2-metal10 0.70
```

这样保留更多 routing resource，本地 global-route 实验可以闭合。

这个练习中不要修改 technology files、LEF/Liberty files、platform rules 或 OpenROAD flow scripts。
