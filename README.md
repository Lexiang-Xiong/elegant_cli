# Elegant CLI

[English](README_en.md) | [中文](README.md)

**Elegant CLI 是一个轻量级的 Python 命令行参数解析引擎。它将繁琐的 argparse 代码转换为直观的字典配置（Schema）。**

它主要解决原生 `argparse` 在处理复杂 CLI 时的三个痛点：
1.  **默认路由**：不输入子命令时，自动执行默认子命令（无需手动检查 `sys.argv`）。
2.  **上下文覆盖**：进入特定子命令时，自动修改父级/全局参数的默认值（无需编写大量 `if/else`）。
3.  **结构清晰**：用一个嵌套字典替代几十行 `add_argument` 代码。

适合需要快速构建包含多级子命令、且参数默认值逻辑复杂的工具脚本。

## 📦 安装

```bash
pip install git+https://github.com/Lexiang-Xiong/elegant_cli.git
```

## ⚡ 极简示例

**场景：一个构建工具。**
*   **全局**：有一个位置参数 `target_dir`，默认是当前目录 `.`。
*   **Check 模式**：如果不输入命令，默认进入检查模式。支持 `-a` (`--all`) 参数来全量检查。
*   **Build 模式**：如果输入 `build`，默认目录自动变更为 `./src`（覆盖全局默认值）。

```python
from elegant_cli import ElegantCLI

# 1. 定义配置树
SCHEMA = {
    # 全局参数 (混合了位置参数和 Flag)
    "args": {
        "target_dir": {"default": ".", "help": "目标目录"},
        "--verbose": {"default": False, "type": "bool", "help": "详细日志"}
    },
    
    # 子命令定义
    "sub_command": {
        "__default__": "check",  # 不输命令时的默认行为
        
        "check": {
            "help": "检查代码",
            "args": {
                # 布尔值 Flag: 不输为 False, 输入 -a 则为 True
                "-a": {"default": False, "type": "bool", "help": "检查所有文件"}
            }
        },
        
        "build": {
            "help": "构建项目",
            # 【核心功能】进入 build 模式，自动修改 target_dir 默认值
            "overrides": { "target_dir": "./src" }, 
            "args": {
                "--minify": {"default": False, "type": "bool"}
            }
        }
    }
}

def main():
    # 2. 运行 (返回标准 argparse.Namespace)
    args = ElegantCLI(SCHEMA).run()

    print(f"执行命令: {args.command}")
    print(f"操作目录: {args.target_dir}")
    
    if args.command == "check":
        print(f"全量检查: {args.a}")  # 对应 -a 参数

if __name__ == "__main__":
    main()
```

### 效果演示

1.  **默认路由 + 默认参数**
    *(不输命令 -> 进 check; 没输 -a -> 全量检查为 False)*
    ```bash
    $ python main.py
    执行命令: check
    操作目录: .
    全量检查: False
    ```

2.  **默认路由 + Flag 开关**
    *(不输命令 -> 进 check; 输了 -a -> 全量检查为 True)*
    ```bash
    $ python main.py -a
    执行命令: check
    操作目录: .
    全量检查: True
    ```

3.  **上下文覆盖**
    *(进 build -> 目录自动变为 ./src)*
    ```bash
    $ python main.py build
    执行命令: build
    操作目录: ./src
    ```

4.  **用户优先**
    *(用户指定目录 -> 覆盖一切默认值)*
    ```bash
    $ python main.py build /tmp
    执行命令: build
    操作目录: /tmp
    ```

### LLM协同使用

在基于LLM自动开发的项目中希望快速集成ElegantCLI，可以参考[LLM_PROMPT.md](LLM_PROMPT.md)，必要时将该文件发给LLM即可。

## 📄 License

MIT License