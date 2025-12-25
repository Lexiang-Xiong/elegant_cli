import pytest
from elegant_cli import ElegantCLI

# ==============================================================================
# 测试数据 Schema
# ==============================================================================
TEST_SCHEMA = {
    "args": {
        "-o": {"default": "root_default.md", "type": "str", "help": "输出文件"},
        "--debug": {"default": False, "type": "bool", "help": "调试模式"},
        "directory": {"default": ".", "type": "str", "help": "目标目录"}
    },
    "sub_command": {
        "__default__": "by_config",
        
        "scan": {
            "help": "扫描模式",
            "args": {
                "-c": {"default": False, "type": "bool"}
            },
            "sub_command": {
                "deep": {
                    "help": "深度扫描",
                    "args": { "--depth": {"default": "5", "type": "int"} }
                }
            }
        },
        
        "by_config": {
            "help": "配置模式",
            "overrides": { "-o": "config_override.md" }, # 测试父级覆盖
            "args": {
                "-m": {"default": "minimal", "type": "str"}
            }
        },
        
        "by_ext": {
            "help": "后缀模式",
            "args": {
                "-e": {"default": [], "type": "list", "required": True},
                "-l": {"default": "id", "type": "str"}
            }
        }
    }
}

@pytest.fixture
def cli():
    return ElegantCLI(TEST_SCHEMA)

# ==============================================================================
# 测试用例
# ==============================================================================

def test_basic_defaults(cli):
    """测试完全默认情况：应注入默认命令、默认目录、默认参数"""
    # 输入: main.exe
    args = cli.run(["main.exe"])
    
    assert args.command == "by_config"
    assert args.directory == "."
    # 验证 Override: by_config 应该覆盖 root 的 -o
    assert args.o == "config_override.md"
    # 验证子命令默认值
    assert args.m == "minimal"

def test_explicit_global(cli):
    """测试显式全局参数：用户输入应优先于 Override"""
    # 输入: main.exe -o user.md
    args = cli.run(["main.exe", "-o", "user.md"])
    
    assert args.o == "user.md"  # 用户胜
    assert args.command == "by_config" # 依然走默认命令

def test_explicit_positional(cli):
    """测试显式位置参数"""
    # 输入: main.exe /src
    args = cli.run(["main.exe", "/src"])
    
    assert args.directory == "/src"
    assert args.command == "by_config"
    assert args.o == "config_override.md"

def test_explicit_command_scan(cli):
    """测试显式切换子命令"""
    # 输入: main.exe scan
    args = cli.run(["main.exe", "scan"])
    
    assert args.command == "scan"
    assert args.c is False
    # scan 没有 override -o，所以应该是 root 的默认值
    assert args.o == "root_default.md"

def test_explicit_command_args(cli):
    """测试子命令参数"""
    # 输入: main.exe scan -c
    args = cli.run(["main.exe", "scan", "-c"])
    
    assert args.command == "scan"
    assert args.c is True

def test_mixed_order(cli):
    """测试乱序输入 (全局 flag 在后，目录在中间)"""
    # 输入: main.exe /src by_config -o final.md
    # 解析器应该能识别 /src 是目录，by_config 是命令
    args = cli.run(["main.exe", "/src", "by_config", "-o", "final.md"])
    
    assert args.directory == "/src"
    assert args.command == "by_config"
    assert args.o == "final.md"

def test_nested_command(cli):
    """测试嵌套子命令 (Recursive)"""
    # 输入: main.exe scan deep
    args = cli.run(["main.exe", "scan", "deep"])
    
    # Argparse 的嵌套 subparser 通常不会直接把深层名字赋给 command，
    # 而是取决于 dest 的定义。在我们的实现中，scan 是 command。
    # 我们需要在 build_parser 里检查是否正确进入了 deep。
    # 注意：argparse 默认行为，args.command 会是 'scan'，除非我们给深层定义了 dest。
    # 我们的库目前没有给深层显式 dest，但参数 --depth 应该存在。
    
    assert args.command == "scan"
    assert args.depth == 5  # 这是 deep 命令的默认参数
    assert args.o == "root_default.md"

def test_list_argument(cli):
    """测试列表参数"""
    # 输入: main.exe by_ext -e .py .js
    args = cli.run(["main.exe", "by_ext", "-e", ".py", ".js"])
    
    assert args.command == "by_ext"
    assert args.e == [".py", ".js"]
    assert args.l == "id" # 默认值

def test_resolve_logic_debug(cli):
    """直接测试 resolve 方法生成的列表结构 (白盒测试)"""
    # 场景: main.exe
    # 期望: ['.', '-o', 'config_override.md', 'by_config', '-m', 'minimal']
    # 注意顺序：位置参数 -> 全局 Flag -> 子命令 -> 子命令参数
    resolved = cli.resolve([])
    
    assert resolved[0] == "."
    assert "-o" in resolved
    assert "config_override.md" in resolved
    assert "by_config" in resolved
    assert "-m" in resolved
    assert "minimal" in resolved

def test_override_logic_complex(cli):
    """测试 Override 逻辑：只有当用户未输入时才 Override"""
    # 1. 用户未输入 -> 使用 Override
    args1 = cli.run(["main.exe"])
    assert args1.o == "config_override.md"
    
    # 2. 用户输入了 -> 使用用户输入 (忽略 Override)
    args2 = cli.run(["main.exe", "-o", "my.md"])
    assert args2.o == "my.md"

def test_help_flag_bypass(cli, capsys):
    """
    测试 Help 旁路机制：
    即便配置了默认子命令 (by_config)，输入 -h 也应该显示 Root 帮助，而不是跳转后的帮助。
    """
    # Argparse 遇到 -h 会抛出 SystemExit，这是预期行为
    with pytest.raises(SystemExit):
        cli.run(["cb", "-h"])
    
    # 捕获 stdout
    captured = capsys.readouterr()
    
    # 验证显示的是 Root 层的帮助信息 (包含所有子命令)
    assert "usage:" in captured.out
    assert "{scan,by_config,by_ext}" in captured.out
    # 确保没有进入 specific 子命令的帮助 (比如 by_config 的特有参数 -c)
    # 注意：如果 root 也有 -c 这里的断言要小心，但在我们的测试 Schema 里 root 没有 -c
    assert "[-c C]" not in captured.out

if __name__ == "__main__":
    pytest.main([__file__, "-v"])