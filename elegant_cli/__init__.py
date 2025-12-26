import sys
import argparse
from typing import Dict, List, Any, Optional, Tuple, Set

# --- P1: Exception Definitions ---
class ElegantCLIError(Exception):
    """Base exception for ElegantCLI."""
    pass

class ConfigurationError(ElegantCLIError):
    """Raised when the schema configuration is invalid."""
    pass

# --- P2: Type Registry (New) ---
class TypeRegistry:
    """
    Central registry for argument type converters.
    Allows extending supported types (e.g., custom date parsers) without modifying core logic.
    """
    _converters = {
        "str": str,
        "int": int,
        "float": float,
    }

    @classmethod
    def register(cls, name: str, converter: Any):
        """Register a new type converter."""
        cls._converters[name] = converter

    @classmethod
    def get(cls, name: str) -> Any:
        """Get converter by name. Defaults to str if not found."""
        return cls._converters.get(name, str)
    
    @classmethod
    def is_valid(cls, name: str) -> bool:
        """Check if a type name is registered."""
        return name in cls._converters

class ElegantCLI:
    """
    Configuration-driven semantic CLI engine.
    """
    def __init__(self, schema: Dict[str, Any]):
        # --- P1: Static Validation ---
        self._validate_schema(schema)
        self.schema = schema

    def _validate_schema(self, schema: Dict[str, Any], path: str = "root"):
        """Recursively validate the schema structure."""
        args = schema.get("args", {})
        sub_cmds = schema.get("sub_command", {})
        
        # 1. Validate Types
        # Structural types (handled specially) + Scalar types (handled by Registry)
        structural_types = {"bool", "list"}
        
        for flag, info in args.items():
            arg_type = info.get("type", "str")
            
            # Check if it's a known structural type or a registered scalar type
            if arg_type not in structural_types and not TypeRegistry.is_valid(arg_type):
                valid_list = ", ".join(list(structural_types) + list(TypeRegistry._converters.keys()))
                raise ConfigurationError(
                    f"Invalid type '{arg_type}' for argument '{flag}' at {path}. "
                    f"Supported types: {valid_list}"
                )
                
        # 2. Validate Default Command
        default_cmd = sub_cmds.get("__default__")
        if default_cmd and default_cmd not in sub_cmds:
             raise ConfigurationError(f"Default command '{default_cmd}' defined in {path} but not found in sub_commands")
             
        # 3. Recursive Check
        for name, node in sub_cmds.items():
            if name == "__default__": continue
            self._validate_schema(node, path=f"{path}.{name}")

    def run(self, argv: List[str] = None) -> argparse.Namespace:
        if argv is None:
            argv = sys.argv
        
        raw_args = argv[1:] if argv else []
        
        # --- P0: Fix Help Routing ---
        
        # 1. Always Resolve first
        final_args = self.resolve(raw_args)
        
        # 2. Build Parser
        parser = self.build_parser()
        
        # 3. Smart Help Logic
        # If -h exists, decide whether to show Root Help or Subcommand Help
        if "-h" in raw_args or "--help" in raw_args:
            if self._should_show_root_help(raw_args, final_args):
                # Fallback to raw args to trigger Root Help
                return parser.parse_args(raw_args)
            
        return parser.parse_args(final_args)

    def _should_show_root_help(self, raw_args: List[str], final_args: List[str]) -> bool:
        """
        Determine if we should show Root Help instead of Subcommand Help.
        Logic: If Implicit Routing occurred AND User provided NO specific flags for that command -> Show Root Help.
        """
        sub_cmds = self.schema.get("sub_command", {})
        valid_cmds = {k for k in sub_cmds if k != "__default__"}
        
        # Identify the resolved command
        resolved_cmd = None
        cmd_node = None
        
        for arg in final_args:
            if arg in valid_cmds:
                resolved_cmd = arg
                cmd_node = sub_cmds[arg]
                break
        
        if not resolved_cmd:
            return False # No subcommand context, let argparse handle it
            
        # 1. Explicit Command Check (e.g. "cb scan -h")
        if resolved_cmd in raw_args:
            return False # User typed the command, show its help
            
        # 2. Implicit Context Check (e.g. "cb -c -h" where -c belongs to implicit scan)
        if cmd_node:
            child_args_def = cmd_node.get("args", {})
            for raw in raw_args:
                # If user entered a flag defined in the subcommand
                if raw.startswith("-") and raw in child_args_def:
                    return False
        
        # 3. Default case: Implicit command but no specific context -> Root Help
        return True

    def resolve(self, tokens: List[str]) -> List[str]:
        return self._resolve_recursive(tokens, self.schema, is_root=True)

    def _resolve_recursive(self, tokens: List[str], node: Dict, is_root: bool = False) -> List[str]:
        args_def = node.get("args", {})
        sub_cmds = node.get("sub_command", {})
        
        # --- A. Extract Flags ---
        user_flags = {}
        remaining = []
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("-") and token in args_def:
                arg_type = args_def[token].get("type", "str")
                if arg_type == "bool":
                    user_flags[token] = True
                    i += 1
                elif arg_type == "list":
                    vals = []
                    i += 1
                    while i < len(tokens) and not tokens[i].startswith("-"):
                        vals.append(tokens[i])
                        i += 1
                    user_flags[token] = vals
                else:
                    if i + 1 < len(tokens) and not tokens[i+1].startswith("-"):
                        user_flags[token] = tokens[i+1]
                        i += 2
                    else:
                        i += 1 
            else:
                remaining.append(token)
                i += 1

        # --- B. Routing ---
        target_cmd = None
        child_tokens = []
        positional_val = None
        
        cmd_keys = [k for k in sub_cmds.keys() if k != "__default__"]
        
        found_cmd = False
        cmd_idx_in_remaining = -1
        
        for idx, r in enumerate(remaining):
            if r in cmd_keys:
                target_cmd = r
                found_cmd = True
                cmd_idx_in_remaining = idx
                child_tokens = remaining[idx+1:]
                
                if is_root and idx > 0 and positional_val is None:
                    positional_val = remaining[0]
                break
        
        # Capture tokens that were in 'remaining' but NOT consumed as command or positional
        extra_args = []
        
        if not found_cmd:
            # Try explicit positional (Root Only)
            if is_root and remaining and not remaining[0].startswith("-"):
                positional_val = remaining[0]
                child_tokens = remaining[1:]
            else:
                child_tokens = remaining
            
            # Default Command
            target_cmd = sub_cmds.get("__default__")
        else:
            # Explicit command found. 
            # Collect tokens BEFORE the command (excluding positional)
            start_idx = 0
            if is_root and cmd_idx_in_remaining > 0 and positional_val is not None:
                start_idx = 1
            
            extra_args = remaining[start_idx:cmd_idx_in_remaining]

        root_pos_key = None
        if is_root:
            for k, v in args_def.items():
                if not k.startswith("-"):
                    root_pos_key = k
                    if positional_val is None:
                        positional_val = v.get("default")
                    break

        # --- C. Recursion ---
        child_argv = []
        child_overrides = {}
        
        if target_cmd and target_cmd in sub_cmds:
            child_node = sub_cmds[target_cmd]
            raw_child_result = self._resolve_recursive(child_tokens, child_node, is_root=False)
            child_argv = [target_cmd] + raw_child_result
            child_overrides = child_node.get("overrides", {})
        else:
            # No sub-command triggered (Leaf node or invalid command).
            extra_args.extend(child_tokens)

        # --- D. Assembly ---
        my_argv = []
        
        if root_pos_key and positional_val:
            my_argv.append(str(positional_val))

        for flag, info in args_def.items():
            if not flag.startswith("-"): continue
            
            val = None
            if flag in user_flags:
                val = user_flags[flag]
            elif flag in child_overrides:
                val = child_overrides[flag]
            else:
                val = info.get("default")
            
            if val is not None and val is not False:
                arg_type = info.get("type", "str")
                if arg_type == "bool":
                    if val is True: my_argv.append(flag)
                elif arg_type == "list":
                    if val:
                        my_argv.append(flag)
                        if isinstance(val, list):
                            my_argv.extend(val)
                        else:
                            my_argv.append(str(val))
                else:
                    my_argv.extend([flag, str(val)])
        
        # Append unknown/extra tokens (e.g. -h)
        my_argv.extend(extra_args)
        
        return my_argv + child_argv

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        self._attach_args(parser, self.schema, is_root=True)
        return parser

    def _attach_args(self, parser, node, is_root=False):
        args_def = node.get("args", {})
        sub_cmds = node.get("sub_command", {})
        
        for flag, info in args_def.items():
            help_txt = info.get("help", "")
            
            if not flag.startswith("-"):
                parser.add_argument(flag, help=help_txt)
            else:
                arg_type = info.get("type", "str")
                
                # --- P2: Refactored Type Handling ---
                if arg_type == "bool":
                    parser.add_argument(flag, action="store_true", help=help_txt)
                elif arg_type == "list":
                    parser.add_argument(flag, nargs="+", default=None, help=help_txt)
                else:
                    # Dynamic Lookup via Registry
                    target_type = TypeRegistry.get(arg_type)
                    parser.add_argument(flag, default=None, help=help_txt, type=target_type)

        valid_subs = {k: v for k, v in sub_cmds.items() if k != "__default__"}
        if valid_subs:
            if is_root:
                sp = parser.add_subparsers(dest="command")
            else:
                sp = parser.add_subparsers()
            
            for name, child_node in valid_subs.items():
                help_str = child_node.get("help")
                p = sp.add_parser(name, help=help_str, description=help_str)
                self._attach_args(p, child_node, is_root=False)