# 06_drc_spacing

EDAthon 风格 DRC 修复小练习。

这个练习用 KLayout 生成两个 Metal1 矩形，并检查两条规则：

- Metal1 最小宽度：0.05 um
- Metal1 最小间距：0.06 um

## 文件

- `make_layout_bad.rb`：故意违反 width 和 spacing
- `make_layout.rb`：修复后的 layout generator
- `rules.drc`：DRC 规则文件

## 基线失败

```sh
klayout -b -r make_layout_bad.rb
klayout -b -r rules.drc -rd input=layout_bad.gds -rd report=drc_report_bad.lyrdb
```

期望基线结果：

- 2 个 `M1_WIDTH` violation
- 1 个 `M1_SPACE` violation

## 修复后 Layout

```sh
klayout -b -r make_layout.rb
klayout -b -r rules.drc -rd input=layout.gds -rd report=drc_report.lyrdb
```

期望最终结果：

- 0 个 DRC violation

## 修复说明

当 `dbu = 0.001 um` 时，1 database unit 等于 0.001 um。

基线矩形：

- 矩形 1：`(0, 0, 40, 200)`，宽度 0.04 um
- 矩形 2：`(70, 0, 110, 200)`，宽度 0.04 um
- 间距：`70 - 40 = 30 dbu = 0.03 um`

修复后矩形：

- 矩形 1：`(0, 0, 60, 200)`，宽度 0.06 um
- 矩形 2：`(130, 0, 190, 200)`，宽度 0.06 um
- 间距：`130 - 60 = 70 dbu = 0.07 um`

这次修复只修改 layout geometry，不修改 DRC 规则。
