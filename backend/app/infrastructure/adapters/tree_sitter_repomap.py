import os
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger
from tree_sitter import Language, Parser

import tree_sitter_javascript as tsjavascript
import tree_sitter_python as tspython

from app.domain.ports import RepomapPort

REPOMAP_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".yml", ".yaml", ".json", ".toml",
    ".sql", ".sh", ".bash",
    ".css", ".html",
    ".h", ".cpp", ".ino",
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", "dist", "build",
    ".eggs", ".egg-info",
}


class TreeSitterRepomapAdapter(RepomapPort):
    """Generates a repository map using Tree-sitter for code symbol extraction."""

    def __init__(self) -> None:
        self._parsers: Dict[str, Parser] = {}
        self._init_parsers()

    def _init_parsers(self) -> None:
        try:
            py_parser = Parser()
            py_lang = Language(tspython.language())
            py_parser.language = py_lang
            self._parsers["python"] = py_parser
        except Exception as e:
            logger.warning(f"Failed to init Python parser: {e}")

        try:
            js_parser = Parser()
            js_lang = Language(tsjavascript.language())
            js_parser.language = js_lang
            self._parsers["javascript"] = js_parser
        except Exception as e:
            logger.warning(f"Failed to init JS parser: {e}")

    def generate(self, repo_path: Path) -> str:
        logger.info(f"Generating repomap for {repo_path}...")
        repo_name = repo_path.name

        file_tree = self._build_file_tree(repo_path)

        lines = [
            f"# Repository Map: {repo_name}",
            "",
            "## Directory Structure",
            "```text",
        ]
        lines.extend(self._format_tree(file_tree, prefix=""))
        lines.append("```")

        lines.extend(["", "## Code Symbols", ""])
        symbols = self._extract_all_symbols(repo_path)
        
        for filepath, file_symbols in sorted(symbols.items()):
            rel_path = os.path.relpath(filepath, repo_path)
            # Normalize path separators for the output map
            rel_path = rel_path.replace("\\", "/")
            
            lines.append(f"### {rel_path}")
            for symbol in file_symbols:
                indent = "  " * symbol["depth"]
                sig = symbol.get("signature", "")
                lines.append(
                    f"{indent}- {symbol['kind']} **{symbol['name']}**{sig}"
                )
            lines.append("")

        repomap = "\n".join(lines)
        logger.info(f"Repomap generated: {len(lines)} lines")
        return repomap

    # File tree

    def _build_file_tree(self, root: Path) -> Dict:
        tree: Dict = {}
        try:
            entries = sorted(root.iterdir())
        except PermissionError:
            return tree
            
        for item in entries:
            if item.name.startswith(".") and item.name != ".env.example":
                continue
            if item.name in SKIP_DIRS:
                continue
                
            if item.is_dir():
                subtree = self._build_file_tree(item)
                if subtree:
                    tree[item.name + "/"] = subtree
            elif item.suffix in REPOMAP_EXTENSIONS or item.name in (
                "Dockerfile", "Makefile", "README.md",
            ):
                tree[item.name] = None
                
        return tree

    def _format_tree(self, tree: Dict, prefix: str) -> List[str]:
        lines: List[str] = []
        items = list(tree.items())
        
        for i, (name, subtree) in enumerate(items):
            is_last = i == len(items) - 1
            connector = "    " if is_last else "    "
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name}")
            
            if subtree is not None:
                extension = "    " if is_last else "│   "
                lines.extend(
                    self._format_tree(subtree, prefix + extension)
                )
                
        return lines

    # Symbol extraction

    def _extract_all_symbols(
        self, repo_path: Path,
    ) -> Dict[str, List[Dict]]:
        symbols: Dict[str, List[Dict]] = {}
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS and not d.startswith(".")
            ]
            
            for fname in sorted(files):
                filepath = os.path.join(root, fname)
                lang = self._detect_language(fname)
                
                if lang and lang in self._parsers:
                    try:
                        with open(
                            filepath, "r", encoding="utf-8", errors="ignore",
                        ) as f:
                            source = f.read()
                        file_symbols = self._extract_symbols(source, lang)
                        if file_symbols:
                            symbols[filepath] = file_symbols
                    except Exception as e:
                        logger.debug(f"Repomap failed to read {filepath}: {e}")
                        continue
                        
        return symbols

    @staticmethod
    def _detect_language(filename: str) -> Optional[str]:
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "javascript",
            ".tsx": "javascript",
        }
        _, ext = os.path.splitext(filename)
        return ext_map.get(ext)

    def _extract_symbols(
        self, source: str, language: str,
    ) -> List[Dict]:
        parser = self._parsers.get(language)
        if not parser:
            return []
            
        source_bytes = source.encode("utf-8", errors="ignore")
        try:
            tree = parser.parse(source_bytes)
            root = tree.root_node
        except Exception:
            return []

        symbols: List[Dict] = []
        if language == "python":
            self._extract_python_symbols(
                root, source_bytes, symbols, depth=0,
            )
        elif language == "javascript":
            self._extract_js_symbols(
                root, source_bytes, symbols, depth=0,
            )
        return symbols

    def _extract_python_symbols(
        self, node, source_bytes: bytes, symbols: List[Dict], depth: int,
    ) -> None:
        for child in node.children:
            if child.type == "class_definition":
                name = self._get_node_name(child)
                if name:
                    symbols.append(
                        {"kind": "class", "name": name, "depth": depth}
                    )
                    body = self._find_child_by_type(child, "block")
                    if body:
                        for method_node in body.children:
                            if method_node.type == "function_definition":
                                method_name = self._get_node_name(method_node)
                                sig = self._get_python_signature(
                                    method_node, source_bytes,
                                )
                                if method_name:
                                    symbols.append({
                                        "kind": "method",
                                        "name": method_name,
                                        "signature": sig,
                                        "depth": depth + 1,
                                    })
                                    
            elif child.type == "function_definition":
                name = self._get_node_name(child)
                sig = self._get_python_signature(child, source_bytes)
                if name:
                    symbols.append({
                        "kind": "function",
                        "name": name,
                        "signature": sig,
                        "depth": depth,
                    })

    def _extract_js_symbols(
        self, node, source_bytes: bytes, symbols: List[Dict], depth: int,
    ) -> None:
        for child in node.children:
            if child.type == "class_declaration":
                name = self._get_node_name(child)
                if name:
                    symbols.append(
                        {"kind": "class", "name": name, "depth": depth}
                    )
                    body = self._find_child_by_type(child, "class_body")
                    if body:
                        for member in body.children:
                            if member.type == "method_definition":
                                method_name = self._get_node_name(member)
                                if method_name:
                                    symbols.append({
                                        "kind": "method",
                                        "name": method_name,
                                        "depth": depth + 1,
                                    })
                                    
            elif child.type == "function_declaration":
                name = self._get_node_name(child)
                if name:
                    symbols.append(
                        {"kind": "function", "name": name, "depth": depth}
                    )
                    
            elif child.type in (
                "lexical_declaration", "variable_declaration",
            ):
                for decl in child.children:
                    if decl.type == "variable_declarator":
                        name = self._get_node_name(decl)
                        value = self._find_child_by_type(
                            decl, "arrow_function",
                        )
                        if name and value:
                            symbols.append({
                                "kind": "function",
                                "name": name,
                                "depth": depth,
                            })
                            
            elif child.type == "export_statement":
                self._extract_js_symbols(
                    child, source_bytes, symbols, depth,
                )

    @staticmethod
    def _get_node_name(node) -> Optional[str]:
        for child in node.children:
            if child.type in ("identifier", "property_identifier"):
                return child.text.decode("utf-8", errors="ignore")
        return None

    @staticmethod
    def _find_child_by_type(node, type_name: str):
        for child in node.children:
            if child.type == type_name:
                return child
        return None

    @staticmethod
    def _get_python_signature(node, source_bytes: bytes) -> str:
        for child in node.children:
            if child.type == "parameters":
                try:
                    return source_bytes[
                        child.start_byte : child.end_byte
                    ].decode("utf-8", errors="ignore")
                except Exception:
                    pass
        return "()"
