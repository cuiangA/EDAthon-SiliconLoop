import subprocess
import sys


# 所有需要评测的模块
TESTS = [
    {
        "name": "adder4",
        "design": "adder4.v",
        "testbench": "tb_adder4.v",
    },
    {
        "name": "mux4",
        "design": "mux4.v",
        "testbench": "tb_mux4.v",
    },
]


def run_command(command):
    """执行命令并返回执行结果。"""
    return subprocess.run(
        command,
        text=True,
        capture_output=True
    )


def test_module(test):
    """编译并仿真一个模块。"""

    name = test["name"]
    design = test["design"]
    testbench = test["testbench"]
    output_file = f"{name}.out"

    print("=" * 50)
    print(f"正在测试：{name}")

    # 编译命令：
    # iverilog -Wall -o adder4.out adder4.v tb_adder4.v
    compile_command = [
        "iverilog",
        "-Wall",
        "-o",
        output_file,
        design,
        testbench,
    ]

    compile_result = run_command(compile_command)

    if compile_result.returncode != 0:
        print(f"[COMPILE FAILED] {name}")
        print(compile_result.stdout)
        print(compile_result.stderr)
        return False

    print(f"[COMPILE PASSED] {name}")

    # 仿真命令，例如：vvp adder4.out
    simulation_result = run_command(["vvp", output_file])
    simulation_log = (
        simulation_result.stdout
        + simulation_result.stderr
    )

    if simulation_result.returncode != 0:
        print(f"[SIMULATION ERROR] {name}")
        print(simulation_log)
        return False

    # 检查 testbench 输出的成功标志
    if "ALL TESTS PASSED" in simulation_log:
        print(f"[PASS] {name}")
        return True

    print(f"[FAIL] {name}")
    print(simulation_log)
    return False


def main():
    passed_count = 0

    for test in TESTS:
        if test_module(test):
            passed_count += 1

    total_count = len(TESTS)

    print("=" * 50)
    print(f"测试结果：{passed_count}/{total_count} 个模块通过")

    if passed_count == total_count:
        print("ALL MODULES PASSED")
        sys.exit(0)

    print("SOME MODULES FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()