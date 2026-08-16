# 04_reg_en_debug

EDAthon 风格 RTL 修复小练习。

testbench 检查一个 8-bit register，带同步低有效复位和 enable。关键规则：

- reset 优先级高于 enable
- enable 为低时，寄存器保持原值

## 文件

- `reg_en.v`：待修复设计
- `tb_reg_en.v`：testbench，也就是规格说明

## 运行方式

在本目录运行：

```sh
iverilog -g2012 -o sim.out reg_en.v tb_reg_en.v && vvp sim.out
```

或者在仓库根目录通过 Docker 工具镜像运行：

```powershell
docker run --rm -v "${PWD}:/workspace" -w /workspace/workspace/04_reg_en_debug edathon-openroad-tools:local bash -lc "iverilog -g2012 -o sim.out reg_en.v tb_reg_en.v && vvp sim.out"
```

## 期望输出

```text
PASS: reg_en
```

## 调试要点

这个练习适合区分三类常见问题：

- compile error：例如缺少分号
- functional simulation failure：例如 reset 没有优先级
- state-holding bug：例如 `en` 为低时仍然载入 `d`

修复题中只应该修改 `reg_en.v`。`tb_reg_en.v` 作为规格说明，通常不改。
