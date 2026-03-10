from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.domain.models.chunk import CodeChunk
from app.infrastructure.adapters.tree_sitter_chunker import (
    TreeSitterChunkingAdapter,
)


class TreeSitterLimitedChunkingAdapter(TreeSitterChunkingAdapter):
    """Tree-sitter AST parsing with size limits."""

    def __init__(
        self,
        include_methods: bool = True,
        max_chunk_size: int = 2048,
        chunk_overlap: int = 256,
    ) -> None:
        super().__init__(include_methods=include_methods)
        self._max_chunk_size = max_chunk_size
        self._chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._max_chunk_size,
            chunk_overlap=self._chunk_overlap,
        )

    @property
    def name(self) -> str:
        suffix = "+methods" if self._include_methods else ""
        return f"TreeSitter-Limited-{self._max_chunk_size} (AST{suffix})"

    def chunk_files(self, files: List[tuple[str, str]]) -> List[CodeChunk]:
        # 1. First get the naturally parsed AST chunks using the parent class
        ast_chunks = super().chunk_files(files)
        # 2. Subdivide any chunks that are too large
        return self._apply_size_limits(ast_chunks)

    def _apply_size_limits(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        result: List[CodeChunk] = []
        for chunk in chunks:
            chunk_length = len(chunk.content)
            
            if chunk_length <= self._max_chunk_size:
                result.append(chunk)
            else:
                # Subdivide large chunk using LangChain's recursive text splitter as a utility
                split_texts = self._splitter.split_text(chunk.content)
                for i, split_text in enumerate(split_texts):
                    
                    # Approximate new start/end lines for the sub-chunk
                    start_idx = chunk.content.find(split_text)
                    relative_start_line = chunk.content.count("\n", 0, start_idx) if start_idx != -1 else 0
                    
                    new_start_line = chunk.start_line + relative_start_line
                    new_end_line = new_start_line + split_text.count("\n")
                    
                    sub_chunk = CodeChunk(
                        content=split_text,
                        file_path=chunk.file_path,
                        start_line=new_start_line,
                        end_line=new_end_line,
                        language=chunk.language,
                        node_name=chunk.node_name,
                        node_type=chunk.node_type,
                    )
                    
                    result.append(sub_chunk)
                    
        return result
