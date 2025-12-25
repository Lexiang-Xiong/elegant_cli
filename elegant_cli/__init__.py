import sys
import argparse
from typing import Dict, List, Any, Optional, Tuple

class ElegantCLI:
    """
    基于配置树的语义 CLI 引擎。
    """
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema

    def run(self, argv: List[str] = None) -> argparse.Namespace:
        if argv is None:
            argv = sys.argv
        
        raw_args = argv[1:] if argv else []

        # 如果检测到帮助标志，直接使用原生 Argparse 行为，不进行语义注入。
        # 这样 cb -h 会显示 Root Help，而不是跳到默认子命令的 Help。
        if "-h" in raw_args or "--help" in raw_args:
            return self.build_parser().parse_args(raw_args)
        
        # 1. 语义解析
        final_args = self.resolve(raw_args)
        
        # 2. 构建 Parser
        parser = self.build_parser()
        
        # 3. 执行
        return parser.parse_args(final_args)

    def resolve(self, tokens: List[str]) -> List[str]:
        return self._resolve_recursive(tokens, self.schema, is_root=True)

    def _resolve_recursive(self, tokens: List[str], node: Dict, is_root: bool = False) -> List[str]:
        args_def = node.get("args", {})
        sub_cmds = node.get("sub_command", {})
        
        # --- A. 提取当前层级的 Flag ---
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

        # --- B. 路由 (Routing) & 位置参数提取 ---
        target_cmd = None
        child_tokens = []
        positional_val = None
        
        cmd_keys = [k for k in sub_cmds.keys() if k != "__default__"]
        
        found_cmd = False
        for idx, r in enumerate(remaining):
            if r in cmd_keys:
                target_cmd = r
                found_cmd = True
                child_tokens = remaining[idx+1:]
                
                # 子命令之前的非flag参数，视为位置参数 (仅Root层)
                if is_root and idx > 0 and positional_val is None:
                    positional_val = remaining[0]
                break
        
        if not found_cmd:
            # 没找到显式命令，尝试提取位置参数 (仅 Root 层有效)
            if is_root and remaining and not remaining[0].startswith("-"):
                positional_val = remaining[0]
                child_tokens = remaining[1:]
            else:
                child_tokens = remaining
            
            # 使用默认子命令
            target_cmd = sub_cmds.get("__default__")

        # Root层位置参数默认值
        root_pos_key = None
        if is_root:
            for k, v in args_def.items():
                if not k.startswith("-"):
                    root_pos_key = k
                    if positional_val is None:
                        positional_val = v.get("default")
                    break

        # --- C. 递归 ---
        child_argv = []
        child_overrides = {}
        
        if target_cmd and target_cmd in sub_cmds:
            child_node = sub_cmds[target_cmd]
            raw_child_result = self._resolve_recursive(child_tokens, child_node, is_root=False)
            child_argv = [target_cmd] + raw_child_result
            child_overrides = child_node.get("overrides", {})

        # --- D. 组装 ---
        my_argv = []
        
        # 1. 注入位置参数
        if root_pos_key and positional_val:
            my_argv.append(str(positional_val))

        # 2. 注入 Flags
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

        return my_argv + child_argv

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        self._attach_args(parser, self.schema, is_root=True)
        return parser

    def _attach_args(self, parser, node, is_root=False):
        args_def = node.get("args", {})
        sub_cmds = node.get("sub_command", {})
        
        # 添加参数
        for flag, info in args_def.items():
            help_txt = info.get("help", "")
            
            # 位置参数
            if not flag.startswith("-"):
                parser.add_argument(flag, help=help_txt)
            # Flag 参数
            else:
                arg_type = info.get("type", "str")
                
                if arg_type == "bool":
                    parser.add_argument(flag, action="store_true", help=help_txt)
                elif arg_type == "list":
                    parser.add_argument(flag, nargs="+", default=None, help=help_txt)
                else:
                    # --- 修复点开始 ---
                    # 映射 Schema 中的字符串类型到 Python 真实类型
                    target_type = str
                    if arg_type == "int":
                        target_type = int
                    elif arg_type == "float":
                        target_type = float
                    
                    # 将 type 传递给 argparse，使其自动转换 "5" -> 5
                    parser.add_argument(flag, default=None, help=help_txt, type=target_type)
                    # --- 修复点结束 ---

        # 添加子命令
        valid_subs = {k: v for k, v in sub_cmds.items() if k != "__default__"}
        if valid_subs:
            if is_root:
                sp = parser.add_subparsers(dest="command")
            else:
                sp = parser.add_subparsers()
            
            for name, child_node in valid_subs.items():
                p = sp.add_parser(name, help=child_node.get("help"))
                self._attach_args(p, child_node, is_root=False)