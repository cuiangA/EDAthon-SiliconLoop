import re
import subprocess
## iverilog ：把verilog的源码编译成可运行的仿真文件
## vvp：运行编译得到的仿真文件
## run_verilog.py：用python自动调用前两个工具并读取结果

compile_command = [
    "iverilog",
    "-Wall",
    "-o",
    "sim.out",
    "and_gate.v",
    "tb_and_gate.v",
]

print("正在编译 Verilog...")

result = subprocess.run(
    compile_command,
    capture_output=True,
    text=True,
)

if result.returncode != 0:
    error_log = result.stderr
    print("编译失败：")
    print(error_log)

    matches = re.findall(r"([^:\n]+):(\d+):\s*(.*)", error_log)

    for filename, line_number, message in matches:
        print(f"定位结果：{filename} 第 {line_number} 行")
        print(f"错误信息：{message}")

    raise SystemExit(1)

print("编译成功，开始仿真...")

result = subprocess.run(
    ["vvp", "sim.out"],
    capture_output=True,
    text=True,
)

print(result.stdout)

if result.returncode != 0:
    print("仿真失败：")
    print(result.stderr)
    raise SystemExit(1)

print("仿真完成")