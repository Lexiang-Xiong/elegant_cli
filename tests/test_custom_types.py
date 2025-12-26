import pytest
from elegant_cli import ElegantCLI, TypeRegistry, ConfigurationError

def test_custom_type_execution():
    """
    测试自定义类型转换逻辑：
    注册一个 'shout' 类型，将输入转换为大写并加感叹号。
    """
    # 1. 注册自定义类型
    # 定义转换函数: str -> Any
    def to_shout(value: str):
        return value.upper() + "!!!"
    
    TypeRegistry.register("shout", to_shout)

    # 2. 定义使用该类型的 Schema
    schema = {
        "args": {
            "-msg": {"type": "shout", "default": "default"}
        }
    }

    # 3. 运行 CLI
    cli = ElegantCLI(schema)
    
    # Case A: 使用默认值 (注意：默认值通常不经过 Type Converter，取决于 argparse 实现，
    # 但 ElegantCLI 的逻辑是将 default 值直接赋给 argparse。
    # 如果希望默认值也被转换，需要在 Schema 定义时就写好，或者在 post-process 处理。
    # 这里我们主要测试用户输入的情况)
    
    # Case B: 用户输入
    # 模拟输入: prog.py -msg hello
    args = cli.run(["prog.py", "-msg", "hello"])
    
    assert args.msg == "HELLO!!!"

def test_custom_type_validation():
    """
    测试自定义类型的 Schema 校验：
    确保注册后的类型能通过校验，未注册的依然报错。
    """
    # 1. 注册一个新类型 'date'
    TypeRegistry.register("date", lambda x: x) # 伪实现

    # 2. 测试合法 Schema
    good_schema = {
        "args": {
            "--start": {"type": "date"} # 应该是合法的
        }
    }
    # 如果校验失败这里会抛出异常
    ElegantCLI(good_schema) 

    # 3. 测试非法 Schema
    bad_schema = {
        "args": {
            "--end": {"type": "unknown_type_xyz"}
        }
    }
    
    with pytest.raises(ConfigurationError) as excinfo:
        ElegantCLI(bad_schema)
    
    error_msg = str(excinfo.value)
    assert "Invalid type 'unknown_type_xyz'" in error_msg
    # 验证报错信息里是否包含了我们新注册的类型，证明校验逻辑是动态的
    assert "date" in error_msg
    assert "shout" in error_msg # 之前用例注册的应该也在


if __name__ == "__main__":
    pytest.main([__file__, "-v"])