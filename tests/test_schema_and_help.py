import pytest
from elegant_cli import ElegantCLI, ConfigurationError

# ==============================================================================
# 1. Schema Validation Tests (P1 Feature)
# ==============================================================================

def test_schema_invalid_type():
    """测试非法类型定义"""
    bad_schema = {
        "args": {
            "-x": {"type": "unknown_type", "default": 1}
        }
    }
    with pytest.raises(ConfigurationError) as excinfo:
        ElegantCLI(bad_schema)
    assert "Invalid type 'unknown_type'" in str(excinfo.value)

def test_schema_missing_default_command():
    """测试定义的默认子命令不存在"""
    bad_schema = {
        "sub_command": {
            "__default__": "ghost_command",
            "real_command": {"help": "exists"}
        }
    }
    with pytest.raises(ConfigurationError) as excinfo:
        ElegantCLI(bad_schema)
    assert "Default command 'ghost_command' defined in root but not found" in str(excinfo.value)

def test_schema_nested_invalid():
    """测试深层嵌套中的配置错误"""
    bad_schema = {
        "sub_command": {
            "__default__": "cmd1",
            "cmd1": {
                "sub_command": {
                    "__default__": "cmd2", # defined but cmd2 missing
                    "cmd3": {} 
                }
            }
        }
    }
    with pytest.raises(ConfigurationError) as excinfo:
        ElegantCLI(bad_schema)
    assert "Default command 'cmd2' defined in root.cmd1" in str(excinfo.value)

# ==============================================================================
# 2. Help Routing Tests (P0 Feature)
# ==============================================================================

# 定义一个专门用于测试 Help 的 Schema
HELP_SCHEMA = {
    "args": {
        "-g": {"default": False, "type": "bool", "help": "GlobalFlag"}
    },
    "sub_command": {
        "__default__": "default_cmd",
        
        "default_cmd": {
            "help": "Default Command Help",
            "args": {
                "-s": {"default": False, "type": "bool", "help": "SpecificFlag"}
            }
        },
        
        "other_cmd": {
            "help": "Other Command Help",
            "args": {}
        }
    }
}

@pytest.fixture
def help_cli():
    return ElegantCLI(HELP_SCHEMA)

def test_help_root_implicit(help_cli, capsys):
    """
    场景: 用户只输入 -h
    期望: 显示 Root Help (包含命令列表: default_cmd, other_cmd)，而不是跳进 default_cmd
    """
    # 修正：第一个参数是脚本名 "main.py"
    with pytest.raises(SystemExit):
        help_cli.run(["main.py", "-h"])
    
    captured = capsys.readouterr().out
    
    # 验证显示了子命令列表 (Root Help 特征)
    assert "{default_cmd,other_cmd}" in captured
    # 验证没有显示子命令特有的参数 (Subcommand Help 特征)
    assert "SpecificFlag" not in captured

def test_help_subcommand_explicit(help_cli, capsys):
    """
    场景: 用户输入 default_cmd -h
    期望: 显示 default_cmd 的 Help
    """
    # 修正：第一个参数是脚本名 "main.py"
    with pytest.raises(SystemExit):
        help_cli.run(["main.py", "default_cmd", "-h"])
        
    captured = capsys.readouterr().out
    
    # 验证显示了子命令描述
    assert "Default Command Help" in captured
    # 验证显示了子命令特有参数
    assert "SpecificFlag" in captured

def test_help_subcommand_implicit_context(help_cli, capsys):
    """
    场景: 用户输入 -s -h (其中 -s 是 default_cmd 特有的)
    期望: 智能识别上下文，显示 default_cmd 的 Help
    """
    # 修正：第一个参数是脚本名 "main.py"
    with pytest.raises(SystemExit):
        help_cli.run(["main.py", "-s", "-h"])
        
    captured = capsys.readouterr().out
    
    # 验证显示了子命令 Help (因为 -s 锁定了上下文)
    assert "Default Command Help" in captured
    assert "SpecificFlag" in captured

def test_help_subcommand_other(help_cli, capsys):
    """
    场景: 用户输入 other_cmd -h
    期望: 显示 other_cmd 的 Help
    """
    # 修正：第一个参数是脚本名 "main.py"
    with pytest.raises(SystemExit):
        help_cli.run(["main.py", "other_cmd", "-h"])
        
    captured = capsys.readouterr().out
    assert "Other Command Help" in captured

if __name__ == "__main__":
    pytest.main([__file__, "-v"])