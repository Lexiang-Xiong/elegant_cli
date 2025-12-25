# Elegant CLI 开发指南 (System Prompt)

本项目使用内部库 `lib.elegant_cli` 来构建 Python 命令行工具。这是一个基于 **Schema（配置字典）** 驱动的语义引擎，旨在替代原生的 `argparse` 编写方式。

**当你要为本项目编写新的 CLI 入口或修改现有 CLI 时，请务必使用 `ElegantCLI`。**

## 1. 核心能力
- **Recursive Routing (递归路由)**: 支持 `sub_command` 中嵌套 `sub_command`，实现无限层级命令（如 `git remote add`）。
- **Context Overrides (上下文覆盖)**: 子命令（无论多深）都可以通过 `overrides` 修改父级参数的默认值。
- **Auto Injection (智能注入)**: 自动处理位置参数与 Flag 的冲突，自动推导参数类型。

## 2. 代码模板 (Master Template)

以下示例展示了 **多层嵌套 (Nesting)**、**列表参数**、**类型转换** 以及 **深层默认值覆盖** 的完整用法。

```python
from lib.elegant_cli import ElegantCLI

CLI_SCHEMA = {
    # ==========================================
    # 1. 全局参数 (Global Arguments)
    # ==========================================
    "args": {
        # 位置参数 (Key 不带前缀): 默认当前目录
        "work_dir": {"default": ".", "help": "Working Directory"},
        # Flag 参数 (Key 带前缀): 字符串类型
        "-c": {"default": "config.yaml", "type": "str", "help": "Config file"}
    },
    
    # ==========================================
    # 2. 命令路由 (Command Routing)
    # ==========================================
    "sub_command": {
        "__default__": "status", # 根层级的默认命令
        
        # --- 简单命令 ---
        "status": {
            "help": "Show status",
            "args": {
                "-v": {"default": False, "type": "bool"}
            }
        },
        
        # --- 嵌套命令容器 (Parent Command) ---
        "deploy": {
            "help": "Deploy management",
            # 定义该层级的参数
            "args": {
                "--dry-run": {"default": False, "type": "bool"}
            },
            
            # 【关键】递归定义子命令 (Nested Sub-commands)
            "sub_command": {
                "__default__": "dev", # deploy 下的默认命令
                
                # Level 2 Command: deploy dev
                "dev": {
                    "help": "Deploy to development",
                    "args": {
                        "--debug": {"default": True, "type": "bool"}
                    }
                },
                
                # Level 2 Command: deploy prod
                "prod": {
                    "help": "Deploy to production",
                    # 【关键】深层覆盖：进入 prod 时，顶层的 work_dir 自动变更
                    "overrides": { "work_dir": "./dist/prod" },
                    "args": {
                        "--force": {"default": False, "type": "bool"},
                        # 列表类型参数 (nargs='+')
                        "--tags": {"default": ["latest"], "type": "list"}
                    }
                }
            }
        }
    }
}

def main():
    # 1. 启动引擎
    # 返回标准的 argparse.Namespace 对象
    args = ElegantCLI(CLI_SCHEMA).run()
    
    # 2. 业务逻辑
    # 注意：参数名会自动转换为属性 (例如 --dry-run 变为 args.dry_run)
    print(f"Working Dir: {args.work_dir}") 
    print(f"Config: {args.c}")
    
    # 路由判断
    if args.command == "status":
        print(f"Status (Verbose: {args.v})")
        
    elif args.command == "deploy":
        print(f"Dry Run: {args.dry_run}")
        
        # 由于 argparse 的扁平化特性，我们可以通过检查参数存在性
        # 或者在 schema 中定义特定的标识参数来判断进入了哪个子命令
        # 在此例中，我们可以通过 --force (prod特有) 或 --debug (dev特有) 来区分
        
        if hasattr(args, "force"): # 也就是进入了 prod
            print(f"Deploying to PROD (Force: {args.force})")
            print(f"Tags: {args.tags}")
        elif hasattr(args, "debug"): # 也就是进入了 dev
            print("Deploying to DEV")

if __name__ == "__main__":
    main()
```

## 3. Schema 字段速查表

Schema 是一个嵌套字典结构。

### `args` (参数定义)
| 属性 | 说明 | 示例 |
| :--- | :--- | :--- |
| **Key** | 参数名。`-` 开头为 Flag，否则为位置参数 | `"-o"`, `"directory"` |
| `default` | 默认值。 | `"summary.md"`, `False`, `["py"]` |
| `type` | 类型提示。支持 `str`, `int`, `float`, `bool`, `list` | `bool` (转为 store_true), `list` (转为 nargs='+') |
| `help` | 帮助文档 | `"Output file path"` |
| `required` | 是否必填 (主要用于 list 类型) | `True` |

### `sub_command` (递归路由)
定义当前层级的子命令。
- **`__default__`**: (String) 当用户未输入子命令时的默认跳转目标。
- **Key**: (String) 子命令名称 (如 `scan`, `deploy`)。
- **Value**: (Dict) 该子命令的 Schema 节点。**该节点内可再次包含 `sub_command` 以实现无限嵌套。**

### `overrides` (上下文覆盖)
- **位置**: 仅在子命令节点中有效。
- **作用**: 当路由进入该命令时，强制修改父级或全局参数的默认值。
- **示例**: `"overrides": { "-o": "prod.log" }`

## 4. 最佳实践

1.  **位置参数**：在 Root 层定义位置参数（如 `target_dir`）时，Schema 会自动将其视为可选参数处理，但引擎逻辑会确保它总是有值（默认值或用户输入）。
2.  **Flag 命名**：尽量使用长参数（如 `--verbose`），引擎会自动将其转换为蛇形命名（`args.verbose`）。
3.  **列表参数**：当 `type` 为 `list` 时，默认贪婪匹配后续所有非 Flag 参数。