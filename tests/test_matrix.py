import pytest
import itertools
from elegant_cli import ElegantCLI

# ==============================================================================
# 1. 定义标准测试 Schema
# ==============================================================================
TEST_SCHEMA = {
    "args": {
        "directory": {"default": "DEFAULT_DIR", "type": "str", "help": "位置参数"},
        "-o": {"default": "DEFAULT_O", "type": "str", "help": "全局Flag"}
    },
    "sub_command": {
        "__default__": "by_config",
        
        "scan": {
            "help": "Scan模式",
            "args": {
                "-c": {"default": False, "type": "bool"}
            }
        },
        "by_config": {
            "help": "Config模式",
            "overrides": { "-o": "OVERRIDE_O" },
            "args": {
                "-m": {"default": "DEFAULT_M", "type": "str"}
            }
        }
    }
}

# ==============================================================================
# 2. 定义测试维度 (Dimensions)
# ==============================================================================

# 维度 A: 位置参数 (Directory)
# 格式: (CLI输入片段, 期望值)
POS_ARGS = [
    ([], "DEFAULT_DIR"),       # 1. 缺省
    (["/custom/path"], "/custom/path") # 2. 显式
]

# 维度 B: 全局 Flag (-o)
# 格式: (CLI输入片段, 期望值类型)
#   TYPE_DEFAULT: 使用Schema默认
#   TYPE_USER: 使用用户输入
GLOBAL_FLAGS = [
    ([], "TYPE_DEFAULT"),      # 1. 缺省
    (["-o", "USER_O"], "TYPE_USER") # 2. 显式
]

# 维度 C: 子命令及其参数 (Command & Sub-Args)
# 格式: (CLI输入片段, 期望Command名, 期望Override规则, 验证函数)
# 验证函数接收 args 对象，检查该命令特有的参数是否正确
COMMAND_SCENARIOS = [
    # 场景 1: 隐式默认命令 (by_config) + 缺省参数
    # 对应输入: cb ...
    ([], "by_config", "OVERRIDE_O", lambda a: a.m == "DEFAULT_M"),

    # 场景 2: 隐式默认命令 (by_config) + 显式参数 (这里就是你之前报错的 cb -m global)
    # 对应输入: cb ... -m custom
    (["-m", "USER_M"], "by_config", "OVERRIDE_O", lambda a: a.m == "USER_M"),

    # 场景 3: 显式默认命令 (by_config)
    # 对应输入: cb ... by_config
    (["by_config"], "by_config", "OVERRIDE_O", lambda a: a.m == "DEFAULT_M"),

    # 场景 4: 显式普通命令 (scan)
    # 对应输入: cb ... scan
    (["scan"], "scan", None, lambda a: a.c is False),

    # 场景 5: 显式普通命令 (scan) + 显式参数
    # 对应输入: cb ... scan -c
    (["scan", "-c"], "scan", None, lambda a: a.c is True),
]

# ==============================================================================
# 3. 生成笛卡尔积 (The Matrix)
# ==============================================================================
def generate_test_cases():
    """生成所有可能的组合"""

    return list(itertools.product(POS_ARGS, GLOBAL_FLAGS, COMMAND_SCENARIOS))

# ==============================================================================
# 4. 执行矩阵测试
# ==============================================================================
@pytest.mark.parametrize("pos_data, global_data, cmd_data", generate_test_cases())
def test_cli_matrix(pos_data, global_data, cmd_data):
    """
    全组合测试引擎。
    pos_data: 位置参数维度
    global_data: 全局Flag维度
    cmd_data: 命令及参数维度
    """
    # 1. 解包数据
    pos_tokens, expected_dir = pos_data
    global_tokens, global_type = global_data
    cmd_tokens, expected_cmd, override_val, verify_sub_args = cmd_data

    # 2. 组装 CLI 输入列表
    # 不仅测试组合，还测试顺序的鲁棒性。
    input_argv = ["cb"] + pos_tokens + global_tokens + cmd_tokens
    
    # 3. 运行引擎
    cli = ElegantCLI(TEST_SCHEMA)
    print(f"Testing ARGV: {input_argv}") # 方便 Debug 看到当前测的是哪个组合
    args = cli.run(input_argv)

    # 4. 验证基础属性
    assert args.directory == expected_dir
    assert args.command == expected_cmd

    # 5. 验证全局参数 -o (核心逻辑：用户输入 > Override > 默认值)
    if global_type == "TYPE_USER":
        assert args.o == "USER_O"  # 用户输入优先级最高
    elif override_val:
        assert args.o == override_val # 其次是子命令的 Override
    else:
        assert args.o == "DEFAULT_O" # 最后是 Root 默认值

    # 6. 验证子命令特有参数
    assert verify_sub_args(args)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])