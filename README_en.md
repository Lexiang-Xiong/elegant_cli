# Elegant CLI

[English](README_en.md) | [中文](README.md)

**Elegant CLI is a lightweight Python command-line argument parsing engine. It transforms verbose `argparse` code into an intuitive dictionary configuration (Schema).**

It primarily solves three pain points when handling complex CLIs with native `argparse`:
1.  **Default Routing**: Automatically executes a default subcommand when none is provided (no need to manually check `sys.argv`).
2.  **Context Overrides**: Automatically modifies parent/global parameter default values when entering specific subcommands (no need for extensive `if/else` logic).
3.  **Clean Structure**: Replaces dozens of lines of `add_argument` code with a single nested dictionary.

Ideal for quickly building tool scripts that contain multi-level subcommands and complex default value logic.

## 📦 Installation

```bash
pip install git+https://github.com/Lexiang-Xiong/elegant_cli.git
```

## ⚡ Concise Example

**Scenario: A Build Tool.**
*   **Global**: Has a positional argument `target_dir`, defaulting to current directory `.`.
*   **Check Mode**: Default behavior if no command is entered. Supports `-a` (`--all`) flag for full check.
*   **Build Mode**: If `build` is entered, the default directory automatically changes to `./src` (Overriding the global default).

```python
from elegant_cli import ElegantCLI

# 1. Define the Configuration Tree
SCHEMA = {
    # Global arguments (Mixing positional args and flags)
    "args": {
        "target_dir": {"default": ".", "help": "Target Directory"},
        "--verbose": {"default": False, "type": "bool", "help": "Verbose logging"}
    },
    
    # Subcommand definitions
    "sub_command": {
        "__default__": "check",  # Default behavior when no command is provided
        
        "check": {
            "help": "Check code",
            "args": {
                # Boolean Flag: False by default, True if -a is present
                "-a": {"default": False, "type": "bool", "help": "Check all files"}
            }
        },
        
        "build": {
            "help": "Build project",
            # [Core Feature] Automatically override target_dir default when entering build mode
            "overrides": { "target_dir": "./src" }, 
            "args": {
                "--minify": {"default": False, "type": "bool"}
            }
        }
    }
}

def main():
    # 2. Run (Returns a standard argparse.Namespace)
    args = ElegantCLI(SCHEMA).run()

    print(f"Command: {args.command}")
    print(f"Directory: {args.target_dir}")
    
    if args.command == "check":
        print(f"Check All: {args.a}")  # Corresponds to -a argument

if __name__ == "__main__":
    main()
```

### Demo

1.  **Default Routing + Default Args**
    *(No cmd -> check; No -a -> Check All is False)*
    ```bash
    $ python main.py
    Command: check
    Directory: .
    Check All: False
    ```

2.  **Default Routing + Flag Switch**
    *(No cmd -> check; With -a -> Check All is True)*
    ```bash
    $ python main.py -a
    Command: check
    Directory: .
    Check All: True
    ```

3.  **Context Override**
    *(Enter build -> Directory automatically changes to ./src)*
    ```bash
    $ python main.py build
    Command: build
    Directory: ./src
    ```

4.  **User Priority**
    *(User specified directory -> Overrides all defaults)*
    ```bash
    $ python main.py build /tmp
    Command: build
    Directory: /tmp
    ```

## 📄 License

MIT License