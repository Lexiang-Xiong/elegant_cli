# Elegant CLI

[English](README_en.md) | [中文](README.md)

**Elegant CLI is a production-ready lightweight Python command-line argument parsing engine. It transforms verbose `argparse` code into an intuitive dictionary configuration (Schema).**

While remaining lightweight (Core < 400 lines), it solves the core pain points of building complex CLIs:

1.  **Smart Routing**: Automatically executes default behaviors when no command is provided. Context-aware `-h` correctly displays help for the specific subcommand or root.
2.  **Context Overrides**: Automatically modifies parent/global parameter default values when entering deep subcommands.
3.  **Strict Validation**: Validates the Schema configuration at startup, catching typos (e.g., invalid types) and broken links immediately.
4.  **Extensible Types**: Built-in support for `str`, `int`, `float`, `bool`, `list`, with a Registry system for custom types.

---

## 📦 Installation

```bash
pip install git+https://github.com/Lexiang-Xiong/elegant_cli.git
```

## ⚡ Quick Start

```python
from elegant_cli import ElegantCLI

# 1. Define Configuration
SCHEMA = {
    "args": {
        "target_dir": {"default": ".", "help": "Target Directory"},
        "--verbose": {"default": False, "type": "bool"}
    },
    "sub_command": {
        "__default__": "check",
        "check": {
            "help": "Check code",
            "args": { "-a": {"default": False, "type": "bool"} }
        },
        "build": {
            "help": "Build project",
            "overrides": { "target_dir": "./src" }, 
            "args": { "--minify": {"default": False, "type": "bool"} }
        }
    }
}

def main():
    # 2. Run
    args = ElegantCLI(SCHEMA).run()

    # 3. Access Arguments
    print(f"Command: {args.command}")
    print(f"Target: {args.target_dir}")

if __name__ == "__main__":
    main()
```

### Demo

1.  **Default Routing + Default Args**
    *(No cmd -> check; No -a -> Check All is False)*
    ```bash
    $ python main.py
    Command: check
    Target: .
    Check All: False
    ```

2.  **Default Routing + Flag Switch**
    *(No cmd -> check; With -a -> Check All is True)*
    ```bash
    $ python main.py -a
    Command: check
    Target: .
    Check All: True
    ```

3.  **Context Override**
    *(Enter build -> Target automatically changes to ./src)*
    ```bash
    $ python main.py build
    Command: build
    Target: ./src
    ```

4.  **User Priority**
    *(User specified target -> Overrides all defaults)*
    ```bash
    $ python main.py build /tmp
    Command: build
    Target: /tmp
    ```

## 🧠 Core Mechanism: Flattening & Access

Understanding how ElegantCLI **flattens** the argument tree is crucial.

### 1. Unified Namespace
Regardless of nesting depth (e.g., `deploy -> prod -> deep -> ...`), the final `args` object is a flat `argparse.Namespace`.

*   **Flag Naming**: `--dry-run` becomes `args.dry_run` (dashes to underscores).
*   **Positional**: `target_dir` becomes `args.target_dir`.

### 2. Access Logic
Since arguments from all subcommands are flattened, it is best practice to check `args.command` before accessing command-specific flags.

```python
if args.command == "build":
    # Safe: --minify is defined in 'build'
    if args.minify: 
        run_minify()
        
    # Safe: target_dir is global
    print(args.target_dir) 

elif args.command == "check":
    # Risky: args.minify may not exist here or be None.
    # Always scope access by command.
    pass
```

## 🛡️ Production Safety & Fail-safes

ElegantCLI strictly separates errors into two categories for better production handling.

### 1. Boot Time: ConfigurationError
Raised when your Schema is invalid (e.g., typo `typ: int` or broken default link).
*   **When**: `ElegantCLI(SCHEMA)` initialization.
*   **Action**: Raises `elegant_cli.ConfigurationError`.
*   **Handling**: This indicates a developer bug. It should prevent the app from starting.

### 2. Runtime: User Input Error
Raised when user input is invalid (e.g., passing strings to an integer flag).
*   **When**: `run()` execution.
*   **Action**: Prints to stderr and triggers `SystemExit` (Exit Code 2).
*   **Handling**: Standard CLI behavior. No need to catch in python code usually.

### Production Template

```python
import sys
from elegant_cli import ElegantCLI, ConfigurationError

def main():
    try:
        # 1. Init (Fail Fast on Bad Config)
        cli = ElegantCLI(SCHEMA)
    except ConfigurationError as e:
        # Fail-safe: Prevent starting with broken logic
        print(f"[FATAL] CLI Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Execution (Handles sys.argv)
    args = cli.run()

    # 3. Business Logic
    process(args)

if __name__ == "__main__":
    main()
```

## 🛠️ Advanced: Type Registry

```python
from elegant_cli import TypeRegistry

# Register a custom type
TypeRegistry.register("shout", lambda x: x.upper())

SCHEMA = {
    "args": { "--msg": {"type": "shout", "default": "hi"} }
}
# Run --msg hello -> args.msg is "HELLO"
```

## 📄 License

MIT License