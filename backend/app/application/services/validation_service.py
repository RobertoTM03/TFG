import hashlib
import os
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from loguru import logger

from app.config import Settings
from app.domain.models.chunk import SearchResult
from app.domain.models.evaluation import RuleEvaluation
from app.domain.models.validation_result import (
    FileMatch,
    RuleValidation,
    ValidationResult,
)
from app.infrastructure.container import Container

# Lines of context kept around each chunk when truncating large files
_CONTEXT_LINES = 20

ProgressCallback = Optional[Callable[[int, str], None]]


class ValidationService:
    """Orchestrates the complete validation pipeline."""

    def __init__(self, container: Container, settings: Settings) -> None:
        self._c = container
        self._settings = settings

    # Public entry point

    def validate(
        self,
        repository_url: str,
        rules: List[str],
        on_progress: ProgressCallback = None,
        enable_cross_check: Optional[bool] = None,
    ) -> ValidationResult:
        """Run the full validation pipeline with incremental indexing."""

        def _report(pct: int, msg: str) -> None:
            if on_progress:
                on_progress(pct, msg)

        repo_path = None
        try:
            # 1. Clone
            _report(0, "Cloning repository...")
            repo_path = self._c.repository.clone(repository_url)
            _report(5, "Repository cloned")

            model_name = self._c.embedding.name
            strategy_name = self._c.chunking.name
            collection_name = self._collection_name(
                repository_url, model_name, strategy_name,
            )

            # 2. Load files
            _report(8, "Loading source files...")
            files = self._c.repository.load_files(repo_path)
            files = self._normalize_source_paths(files, repo_path)

            # 3. Compute file hashes
            current_hashes = self._compute_file_hashes(files)
            logger.info(
                f"Loaded {len(files)} documents from "
                f"{len(current_hashes)} unique files"
            )

            if not current_hashes:
                raise ValueError(
                    "The repository contains no indexable source files. "
                    "Make sure the repository is not empty and contains "
                    "supported code files."
                )

            # 4. Stored hashes
            stored_hashes = self._c.database.get_file_hashes(
                repository_url, model_name, strategy_name,
            )

            # 5. Diff
            current_paths = set(current_hashes.keys())
            stored_paths = set(stored_hashes.keys())

            new_files = current_paths - stored_paths
            deleted_files = stored_paths - current_paths
            changed_files = {
                f for f in current_paths & stored_paths
                if current_hashes[f] != stored_hashes[f]
            }
            unchanged_files = current_paths - new_files - changed_files

            files_to_index = new_files | changed_files
            files_to_remove = deleted_files | changed_files
            collection_ready = self._c.vector_store.collection_exists(
                collection_name,
            )

            if not collection_ready and stored_hashes:
                logger.warning(
                    f"Collection '{collection_name}' missing in ChromaDB "
                    "but hashes exist -- forcing full re-index"
                )
                files_to_index = current_paths
                files_to_remove = set()

            # 6. Incremental indexing
            if (
                not files_to_index
                and not files_to_remove
                and collection_ready
            ):
                _report(15, "Repository already indexed -- skipping")
                logger.info(
                    f"Fully vectorised: {len(unchanged_files)} unchanged"
                )
            else:
                _report(15, "Indexing repository...")
                logger.info(
                    f"Incremental: {len(new_files)} new, "
                    f"{len(changed_files)} changed, "
                    f"{len(deleted_files)} deleted, "
                    f"{len(unchanged_files)} unchanged"
                )

                # 6a. Remove stale
                if files_to_remove and collection_ready:
                    removed = self._c.vector_store.delete_by_sources(
                        collection_name, list(files_to_remove),
                    )
                    logger.info(f"Removed {removed} stale chunks")

                # 6b. Hash entries for deleted files
                if deleted_files:
                    self._c.database.delete_file_hash_entries(
                        repository_url, model_name, strategy_name,
                        list(deleted_files),
                    )

                # 6c. Chunk and index new/changed files
                if files_to_index:
                    _report(20, "Chunking and embedding files...")
                    files_to_chunk = [
                        (path, content) for path, content in files
                        if path in files_to_index
                    ]
                    chunks = self._c.chunking.chunk_files(files_to_chunk)
                    
                    # Ensure repo_name is injected
                    repo_name_str = Path(repo_path).name
                    for chunk in chunks:
                        chunk.repo_name = repo_name_str
                        
                    logger.info(
                        f"Split {len(files_to_chunk)} files "
                        f"into {len(chunks)} chunks"
                    )

                    num_indexed = self._c.vector_store.index_documents(
                        chunks=chunks,
                        collection_name=collection_name,
                    )
                    _report(
                        65, f"Indexed {num_indexed} chunks",
                    )

                # 6d. Update hashes
                self._c.database.save_file_hashes(
                    repository_url, model_name, strategy_name,
                    current_hashes,
                )

                # 6e. Update indexed_repositories
                total = self._c.vector_store.collection_count(
                    collection_name,
                )
                self._c.database.save_indexed_repo(
                    repo_url=repository_url,
                    collection_name=collection_name,
                    num_chunks=total,
                    embedding_model=model_name,
                    chunking_strategy=strategy_name,
                )

            # 7. Repomap
            _report(70, "Generating repository map...")
            repomap = self._c.repomap.generate(repo_path)

            # 8. Similarity search per rule
            validations: List[RuleValidation] = []
            for idx, rule in enumerate(rules):
                pct = 72 + int((idx / max(len(rules), 1)) * 8)
                _report(pct, f"Searching for rule {idx + 1}/{len(rules)}...")
                logger.info(f"Searching for rule: {rule[:80]}...")

                results = self._c.vector_store.similarity_search(
                    query=rule,
                    collection_name=collection_name,
                    threshold=self._settings.SIMILARITY_THRESHOLD,
                    max_results=self._settings.MAX_RESULTS,
                )
                file_matches = self._results_to_file_matches(
                    results, repo_path,
                    self._settings.MAX_FILE_CONTENT_SIZE,
                )
                validations.append(
                    RuleValidation(rule=rule, related_files=file_matches),
                )
                logger.info(
                    f"  -> {len(file_matches)} files matched "
                    f"(from {len(results)} chunks)"
                )

            # 9. LLM evaluation -- one rule at a time
            cross_check_active = (
                enable_cross_check
                if enable_cross_check is not None
                else self._settings.ENABLE_CROSS_CHECK
            )
            if cross_check_active:
                _report(80, "Evaluating rules with cross-check (dual-model)...")
                llm_primary = self._c.llm_primary
                llm_secondary = self._c.llm_secondary
                cross_check_service = self._c.cross_check_service
                for idx, validation in enumerate(validations):
                    pct = 80 + int((idx / max(len(validations), 1)) * 14)
                    _report(
                        pct,
                        f"Cross-checking rule {idx + 1}/{len(validations)}...",
                    )
                    logger.info(
                        f"Cross-checking rule {idx + 1}: "
                        f"{validation.rule[:80]}..."
                    )

                    file_contents = [
                        fm.file_content for fm in validation.related_files
                    ]
                    eval_kwargs = dict(
                        rule=validation.rule,
                        repomap=repomap,
                        file_contents=file_contents,
                        repository_url=repository_url,
                    )

                    primary_eval = llm_primary.evaluate_rule(**eval_kwargs)
                    secondary_eval = llm_secondary.evaluate_rule(**eval_kwargs)

                    cross_checked = cross_check_service.reconcile(
                        primary_eval, secondary_eval,
                    )
                    validation.evaluation = cross_checked.final
                    validation.cross_check = cross_checked
                    logger.info(
                        f"  -> strategy={cross_checked.strategy_used} "
                        f"agreement={cross_checked.agreement} "
                        f"verdict={cross_checked.final.verdict} "
                        f"confidence={cross_checked.final.confidence:.0%}"
                    )

                llm_for_summary = llm_primary
                result_llm_model = llm_primary.name

            else:
                _report(80, "Evaluating rules with LLM...")
                llm = self._c.llm
                for idx, validation in enumerate(validations):
                    pct = 80 + int((idx / max(len(validations), 1)) * 14)
                    _report(
                        pct,
                        f"LLM evaluating rule {idx + 1}/{len(validations)}...",
                    )
                    logger.info(
                        f"LLM evaluating rule {idx + 1}: "
                        f"{validation.rule[:80]}..."
                    )

                    file_contents = [
                        fm.file_content for fm in validation.related_files
                    ]

                    evaluation = llm.evaluate_rule(
                        rule=validation.rule,
                        repomap=repomap,
                        file_contents=file_contents,
                        repository_url=repository_url,
                    )
                    validation.evaluation = evaluation
                    logger.info(
                        f"  -> verdict={evaluation.verdict} "
                        f"confidence={evaluation.confidence:.0%}"
                    )

                llm_for_summary = llm
                result_llm_model = llm.name

            # 10. Generate summary
            _report(95, "Generating summary...")
            all_evaluations = [
                v.evaluation for v in validations if v.evaluation
            ]
            summary = llm_for_summary.generate_summary(
                all_evaluations, repository_url,
            )

            _report(98, "Building result...")

            # 11. Result
            result = ValidationResult(
                id=str(uuid.uuid4()),
                repository_url=repository_url,
                repomap=repomap,
                validations=validations,
                summary=summary,
                embedding_model=model_name,
                chunking_strategy=strategy_name,
                llm_model=result_llm_model,
            )

            _report(100, "Done")
            return result

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise
        finally:
            if repo_path:
                self._c.repository.cleanup(repo_path)

    # Helpers

    @staticmethod
    def _collection_name(
        repo_url: str, model_name: str, strategy_name: str,
    ) -> str:
        raw = f"{repo_url}|{model_name}|{strategy_name}"
        digest = hashlib.md5(raw.encode()).hexdigest()[:12]
        repo_slug = (
            repo_url.rstrip("/").split("/")[-1]
            .replace(".", "_")
            .lower()
        )
        return f"{repo_slug}_{digest}"[:63]

    @staticmethod
    def _results_to_file_matches(
        results: List[SearchResult],
        repo_path: Path,
        max_file_size: int,
    ) -> List[FileMatch]:
        """Group results by file, read full content, build header."""
        if not results:
            return []

        file_groups: dict = defaultdict(list)
        for r in results:
            file_groups[r.chunk.file_path].append(r)

        matches: List[FileMatch] = []
        for file_path, file_results in file_groups.items():
            best_score = max(r.relevance_score for r in file_results)

            symbols: List[str] = []
            for r in file_results:
                if r.chunk.node_name and r.chunk.node_name not in symbols:
                    symbols.append(r.chunk.node_name)

            language = next(
                (r.chunk.language for r in file_results if r.chunk.language),
                None,
            )

            full_path = repo_path / file_path
            try:
                raw_content = full_path.read_text(
                    encoding="utf-8", errors="ignore",
                )
            except Exception:
                raw_content = "\n".join(
                    r.chunk.content for r in file_results
                )

            truncated = False
            if len(raw_content) > max_file_size:
                raw_content = ValidationService._extract_relevant_sections(
                    raw_content, file_results, max_file_size,
                )
                truncated = True

            header = ValidationService._build_header(file_path, symbols)
            file_content = f"{header}\n{raw_content}"

            matches.append(FileMatch(
                file_path=file_path,
                relevance_score=round(best_score, 4),
                file_content=file_content,
                language=language,
                matched_symbols=symbols,
                truncated=truncated,
            ))

        matches.sort(key=lambda m: m.relevance_score, reverse=True)
        return matches

    @staticmethod
    def _build_header(file_path: str, symbols: List[str]) -> str:
        """Build `[Archivo: X | Funcion: Y]` header for the LLM."""
        filename = os.path.basename(file_path)
        if not symbols:
            return f"[Archivo: {filename}]"
        label = "Funcion" if len(symbols) == 1 else "Funciones"
        return f"[Archivo: {filename} | {label}: {', '.join(symbols)}]"

    @staticmethod
    def _extract_relevant_sections(
        content: str,
        results: List[SearchResult],
        max_size: int,
    ) -> str:
        lines = content.split("\n")
        total_lines = len(lines)

        relevant: set = set()
        for r in results:
            start = max(0, r.chunk.start_line - 1 - _CONTEXT_LINES)
            end = min(total_lines, r.chunk.end_line + _CONTEXT_LINES)
            for i in range(start, end):
                relevant.add(i)

        if not relevant:
            return content[:max_size] + "\n... (truncated)"

        sorted_idx = sorted(relevant)
        sections: List[List[int]] = []
        current: List[int] = [sorted_idx[0]]
        for idx in sorted_idx[1:]:
            if idx == current[-1] + 1:
                current.append(idx)
            else:
                sections.append(current)
                current = [idx]
        sections.append(current)

        parts: List[str] = []
        for section in sections:
            parts.append("\n".join(lines[i] for i in section))

        result = "\n\n... (content omitted) ...\n\n".join(parts)
        if len(result) > max_size:
            result = result[:max_size] + "\n... (truncated)"
        return result

    @staticmethod
    def _normalize_source_paths(files: List[Tuple[str, str]], repo_path: Path) -> List[Tuple[str, str]]:
        normalized = []
        for abs_path, content in files:
            try:
                rel_path = os.path.relpath(abs_path, str(repo_path))
                # Normalize Windows paths to forward slashes
                rel_path = rel_path.replace("\\", "/")
                normalized.append((rel_path, content))
            except ValueError:
                normalized.append((abs_path, content))
        return normalized

    @staticmethod
    def _compute_file_hashes(files: List[Tuple[str, str]]) -> dict:
        hashes = {}
        for path, content in files:
            hashes[path] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return hashes
