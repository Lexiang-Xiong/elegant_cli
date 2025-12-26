# Elegant CLI

[English](README_en.md) | [中文](README.md)

**Elegant CLI 是一个生产级的轻量 Python 命令行参数解析引擎。它将繁琐的 `argparse` 代码转换为直观的字典配置（Schema）。**

它在保持轻量（Core < 400 lines）的同时，解决了构建复杂 CLI 工具的核心痛点：

1.  **智能路由 (Smart Routing)**：不输入子命令时自动执行默认行为；输入 `-h` 时根据上下文自动显示根帮助或子命令帮助。
2.  **上下文覆盖 (Context Overrides)**：进入深层子命令时，自动修改父级/全局参数的默认值。
3.  **静态校验 (Strict Validation)**：在程序启动时自动检查 Schema 配置，杜绝类型拼写错误或死链接。
4.  **类型扩展 (Type Registry)**：内置 `str`, `int`, `float`, `bool`, `list`，并支持注册自定义类型。

---

## 📦 安装

```bash
pip install git+https://github.com/Lexiang-Xiong/elegant_cli.git
```

## ⚡ 快速开始

```python
from elegant_cli import ElegantCLI

# 1. 定义配置树
SCHEMA = {
    "args": {
        "target_dir": {"default": ".", "help": "目标目录"},
        "--verbose": {"default": False, "type": "bool"}
    },
    "sub_command": {
        "__default__": "check",
        "check": {
            "help": "检查代码",
            "args": { "-a": {"default": False, "type": "bool"} }
        },
        "build": {
            "help": "构建项目",
            "overrides": { "target_dir": "./src" }, 
            "args": { "--minify": {"default": False, "type": "bool"} }
        }
    }
}

def main():
    # 2. 运行
    args = ElegantCLI(SCHEMA).run()
    
    # 3. 访问参数
    print(f"模式: {args.command}")
    print(f"目录: {args.target_dir}")

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

## 🧠 核心机制：参数访问与扁平化

理解 ElegantCLI 的**参数扁平化 (Flattening)** 机制对于开发至关重要。

### 1. 所有的参数都在同一层级
无论你的 Schema 嵌套了多少层（例如 `deploy -> prod -> deep -> ...`），最终返回的 `args` 对象是一个扁平的 `argparse.Namespace`。

*   **Flag 转换规则**：`--dry-run` 转换为 `args.dry_run`（去横杠，变下划线）。
*   **位置参数**：`target_dir` 转换为 `args.target_dir`。

### 2. 访问逻辑
由于 Python 是动态语言，访问属性前建议先判断 `command`。

```python
# 假设进入了 'build' 模式
if args.command == "build":
    # 安全：因为 --minify 是 build 定义的
    if args.minify: 
        run_minify()
        
    # 安全：target_dir 是全局参数
    print(args.target_dir) 

elif args.command == "check":
    # 危险！args.minify 在 check 模式下可能不存在（取决于默认值注入策略），
    # 或者是 None。最佳实践是只访问当前命令上下文内的参数。
    pass
```

## 🛡️ 生产环境兜底措施

ElegantCLI 将错误严格分为两类，以便在生产环境中进行分级处理。

### 1. 启动时：配置错误 (ConfigurationError)
当你的 Schema 写错了（如类型拼写错误 `typ: int`，或者默认命令 `__default__` 指向了不存在的键）。
*   **触发时机**：`ElegantCLI(SCHEMA)` 初始化时。
*   **行为**：抛出 `elegant_cli.ConfigurationError`。
*   **措施**：这是开发阶段的 Bug，必须修复代码，**不应在运行时被忽略**。

### 2. 运行时：用户输入错误
当用户输入了错误的参数（如 `--count abc` 需要整数）。
*   **触发时机**：`run()` 方法执行时。
*   **行为**：打印错误信息到 stderr 并触发 `SystemExit` (Exit Code 2)。
*   **措施**：这是预期内的用户行为，通常无需代码捕获，让其打印 Help 即可。

### 生产代码模版

```python
import sys
from elegant_cli import ElegantCLI, ConfigurationError

def main():
    try:
        # 1. 初始化阶段 (极速校验)
        cli = ElegantCLI(SCHEMA)
    except ConfigurationError as e:
        # 兜底：防止带病上线的配置导致服务崩溃，应报警并退出
        print(f"[FATAL] CLI Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. 执行阶段 (处理 sys.argv)
    # 如果用户输入错误，内部会自动处理并 SystemExit，无需由此处捕获
    args = cli.run()

    # 3. 业务逻辑
    process(args)

if __name__ == "__main__":
    main()
```

## 🛠️ 进阶：自定义类型注册

```python
from elegant_cli import TypeRegistry

# 注册一个将输入转为大写的类型
TypeRegistry.register("shout", lambda x: x.upper())

SCHEMA = {
    "args": { "--msg": {"type": "shout", "default": "hi"} }
}
# 运行 --msg hello -> args.msg 为 "HELLO"
```

## 📄 License

MIT License