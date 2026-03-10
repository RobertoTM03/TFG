from typing import List, Optional, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter
from tree_sitter import Language, Parser

import tree_sitter_javascript as tsjavascript
import tree_sitter_python as tspython

from app.domain.models.chunk import CodeChunk
from app.domain.ports import ChunkingPort


class TreeSitterChunkingAdapter(ChunkingPort):
    """Splits code into chunks using Tree-sitter AST parsing."""

    def __init__(self, include_methods: bool = True) -> None:
        self._include_methods = include_methods
        self._parsers = {
            "python": self._create_parser(tspython.language()),
            "javascript": self._create_parser(tsjavascript.language()),
            "typescript": self._create_parser(tsjavascript.language()),
        }

    @staticmethod
    def _create_parser(language_capsule) -> Parser:
        parser = Parser()
        try:
            lang = Language(language_capsule)
            parser.language = lang
        except (TypeError, AttributeError):
            try:
                parser.set_language(language_capsule)
            except AttributeError:
                parser.language = language_capsule
        return parser

    @property
    def name(self) -> str:
        suffix = "+methods" if self._include_methods else ""
        return f"TreeSitter (AST{suffix})"

    def chunk_files(self, files: List[Tuple[str, str]]) -> List[CodeChunk]:
        all_chunks: List[CodeChunk] = []

        for file_path, content in files:
            lang = self._detect_language(file_path)

            if lang and lang in self._parsers:
                chunks = self._split_with_tree_sitter(file_path, content, lang)
            else:
                chunks = self._split_with_fallback(file_path, content, lang)

            all_chunks.extend(chunks)

        return all_chunks

    @staticmethod
    def _detect_language(filepath: str) -> Optional[str]:
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        for ext, lang in ext_map.items():
            if filepath.endswith(ext):
                return lang
        return None

    def _split_with_tree_sitter(
        self, file_path: str, content: str, language: str
    ) -> List[CodeChunk]:
        source_bytes = content.encode("utf-8")
        parser = self._parsers[language]
        tree = parser.parse(source_bytes)
        root_node = tree.root_node

        if language == "python":
            chunks = self._extract_python_chunks(
                root_node, source_bytes, file_path
            )
        elif language in ("javascript", "typescript"):
            chunks = self._extract_js_chunks(
                root_node, source_bytes, file_path, language
            )
        else:
            chunks = []

        if not chunks:
            # Fallback if no specific AST nodes were found
            return self._split_with_fallback(file_path, content, language)

        return chunks

    def _split_with_fallback(
        self, file_path: str, content: str, language: Optional[str]
    ) -> List[CodeChunk]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=100
        )
        texts = splitter.split_text(content)
        
        chunks = []
        for text in texts:
            # Approximate line calculation
            start_idx = content.find(text)
            start_line = content.count("\n", 0, start_idx) + 1 if start_idx != -1 else 0
            end_line = start_line + text.count("\n")
            
            chunks.append(
                CodeChunk(
                    content=text,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    language=language,
                    node_type="fallback_text_split",
                )
            )
        return chunks

    def _extract_python_chunks(
        self, root_node, source_bytes: bytes, file_path: str
    ) -> List[CodeChunk]:
        chunks: List[CodeChunk] = []
        query_patterns = [
            "(function_definition) @function",
            "(class_definition) @class",
        ]
        if self._include_methods:
            query_patterns.append(
                "(class_definition (block (function_definition) @method))"
            )

        for pattern in query_patterns:
            try:
                query = tspython.language().query(pattern)
                captures = query.captures(root_node)
                for node, _ in captures:
                    chunk = self._create_chunk_from_node(
                        node, source_bytes, file_path, "python"
                    )
                    if chunk:
                        chunks.append(chunk)
            except Exception:
                continue
        return chunks

    def _extract_js_chunks(
        self, root_node, source_bytes: bytes, file_path: str, language: str
    ) -> List[CodeChunk]:
        chunks: List[CodeChunk] = []
        query_patterns = [
            "(function_declaration) @function",
            "(class_declaration) @class",
            "(method_definition) @method",
            "(arrow_function) @arrow",
            "(function_expression) @func_expr",
        ]
        for pattern in query_patterns:
            try:
                query = tsjavascript.language().query(pattern)
                captures = query.captures(root_node)
                for node, capture_name in captures:
                    if capture_name == "method" and not self._include_methods:
                        continue
                    chunk = self._create_chunk_from_node(
                        node, source_bytes, file_path, language
                    )
                    if chunk:
                        chunks.append(chunk)
            except Exception:
                continue
        return chunks

    def _create_chunk_from_node(
        self, node, source_bytes: bytes, file_path: str, language: str
    ) -> Optional[CodeChunk]:
        try:
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            chunk_text = source_bytes[
                node.start_byte : node.end_byte
            ].decode("utf-8")
            node_name = self._extract_node_name(node)

            return CodeChunk(
                content=chunk_text,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                language=language,
                node_name=node_name,
                node_type=node.type,
            )
        except Exception:
            return None

    @staticmethod
    def _extract_node_name(node) -> Optional[str]:
        try:
            for child in node.children:
                if child.type in ("identifier", "property_identifier"):
                    return child.text.decode("utf-8")
            return None
        except Exception:
            return None
