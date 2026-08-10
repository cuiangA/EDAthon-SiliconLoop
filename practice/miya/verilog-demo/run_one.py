import subprocess
import sys
from pathlib import Path


def run_command(command):
    """运行一条命令，返回退出码和全部输出。"""

    print("$", " ".join(command))

    result = subprocess.run(
        command,
        text=True,
        capture_output=True
    )

    output = result.stdout + result.stderr

    if output:
        print(output)

    return result.returncode, output


def main():
    # sys.argv 保存命令行传给 Python 的参数
    if len(sys.argv) != 4:
        print("用法:")
        print("python run_one.py <模块名> <设计文件> <测试文件>")
        sys.exit(1)

    module_name = sys.argv[1]
    design_file = sys.argv[2]
    testbench_file = sys.argv[3]

    # 检查输入文件是否存在
    for filename in [design_file, testbench_file]:
        if not Path(filename).exists():
            print(f"ERROR: 找不到文件 {filename}")
            sys.exit(1)

    output_file = f"{module_name}.out"

    # 第一步：编译 Verilog
    compile_command = [
        "iverilog",
        "-Wall",
        "-o",
        output_file,
        design_file,
        testbench_file
    ]

    return_code, compile_log = run_command(compile_command)

    if return_code != 0:
        print(f"{module_name}: COMPILE FAILED")
        sys.exit(1)

    print(f"{module_name}: COMPILE PASSED")

    # 第二步：运行仿真
    simulation_command = ["vvp", output_file]
    return_code, simulation_log = run_command(simulation_command)

    if return_code != 0:
        print(f"{module_name}: SIMULATION COMMAND FAILED")
        sys.exit(1)

    # 第三步：读取 testbench 的最终结论
    if "ALL TESTS PASSED" in simulation_log:
        print(f"{module_name}: PASS")
        sys.exit(0)

    print(f"{module_name}: FAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()