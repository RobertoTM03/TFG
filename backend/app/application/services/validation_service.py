import hashlib
import os
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from loguru import logger

from app.application.services.cross_check_service import CrossCheckService
from app.domain.models.chunk import SearchResult
from app.domain.models.cross_check import CrossCheckedEvaluation
from app.domain.models.evaluation import RuleEvaluation
from app.domain.models.validation_result import (
    FileMatch,
    RuleValidation,
    ValidationResult,
)
from app.domain.ports import (
    ChunkingPort,
    EmbeddingPort,
    IndexingRepositoryPort,
    LLMPort,
    RepomapPort,
    RepositoryPort,
    VectorStorePort,
)

# Lines of context kept around each chunk when truncating large files
_CONTEXT_LINES = 20

ProgressCallback = Optional[Callable[[int, str], None]]


class ValidationService:
    """Orchestrates the complete validation pipeline."""

    def __init__(
        self,
        repository: RepositoryPort,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
        chunking: ChunkingPort,
        repomap: RepomapPort,
        llm: LLMPort,
        llm_primary: LLMPort,
        llm_secondary: LLMPort,
        cross_check_service: CrossCheckService,
        indexing_repo: IndexingRepositoryPort,
        similarity_threshold: float,
        max_results: int,
        max_file_content_size: int,
    ) -> None:
        self._repository = repository
        self._embedding = embedding
        self._vector_store = vector_store
        self._chunking = chunking
        self._repomap = repomap
        self._llm = llm
        self._llm_primary = llm_primary
        self._llm_secondary = llm_secondary
        self._cross_check_service = cross_check_service
        self._indexing_repo = indexing_repo
        self._similarity_threshold = similarity_threshold
        self._max_results = max_results
        self._max_file_content_size = max_file_content_size

    # Public entry point

    def validate(
        self,
        repository_url: str,
        rules: List[str],
        on_progress: ProgressCallback = None,
        enable_cross_check: Optional[bool] = None,
        clone_url: Optional[str] = None,
        pr_branch: Optional[str] = None,
        max_chunks_per_rule: Optional[int] = None,
        partial_results: Optional[List[dict]] = None,
        on_rule_evaluated: Optional[Callable[[int, "RuleValidation"], None]] = None,
        llm_override: Optional["LLMPort"] = None,
        llm_primary_override: Optional["LLMPort"] = None,
        llm_secondary_override: Optional["LLMPort"] = None,
    ) -> ValidationResult:
        """Run the full validation pipeline with incremental indexing."""

        def _report(pct: int, msg: str) -> None:
            if on_progress:
                on_progress(pct, msg)

        _start = time.monotonic()
        repo_path = None
        use_pr_delta = False
        collection_name = ""
        try:
            # 1. Clone — use the authenticated URL if provided.
            _report(0, "Cloning repository...")
            repo_path = self._repository.clone(
                clone_url or repository_url,
                branch=pr_branch,
            )
            _report(5, "Repository cloned")

            model_name = self._embedding.name
            strategy_name = self._chunking.name
            collection_name = self._collection_name(
                repository_url, model_name, strategy_name,
            )

            # 2. Load files
            _report(8, "Loading source files...")
            files = self._repository.load_files(repo_path)

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

            # 4. Stored hashes (reflect main branch state)
            stored_hashes = self._indexing_repo.get_file_hashes(
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
            main_indexed = self._vector_store.collection_exists(collection_name)

            # Decide indexing strategy:
            # - PR + main already indexed → two-layer delta (don't touch main index)
            # - PR + no main index        → bootstrap: full index as main (branch='')
            # - No PR                     → standard incremental indexing
            use_pr_delta = pr_branch is not None and main_indexed

            if use_pr_delta:
                # 6. Two-layer PR path: only embed changed files as ephemeral delta
                _report(15, "PR delta mode: indexing changed files only...")
                logger.info(
                    f"PR delta '{pr_branch}': {len(files_to_index)} files to embed "
                    f"({len(new_files)} new, {len(changed_files)} changed), "
                    f"{len(unchanged_files)} served from main index"
                )

                if files_to_index:
                    _report(20, "Chunking and embedding PR changes...")
                    files_to_chunk = [
                        (path, content) for path, content in files
                        if path in files_to_index
                    ]
                    chunks = self._chunking.chunk_files(files_to_chunk)

                    repo_name_str = Path(repo_path).name
                    for chunk in chunks:
                        chunk.repo_name = repo_name_str

                    logger.info(
                        f"Split {len(files_to_chunk)} changed files "
                        f"into {len(chunks)} chunks (PR delta)"
                    )
                    num_indexed = self._vector_store.index_documents(
                        chunks=chunks,
                        collection_name=collection_name,
                        branch=pr_branch,
                    )
                    _report(65, f"Indexed {num_indexed} PR delta chunks")
                else:
                    _report(65, "No file changes in PR — using main index only")

            else:
                # 6. Standard incremental indexing (updates main index, branch='')
                if not main_indexed and stored_hashes:
                    logger.warning(
                        f"Collection '{collection_name}' missing in vector store "
                        "but hashes exist -- forcing full re-index"
                    )
                    files_to_index = current_paths
                    files_to_remove = set()

                if (
                    not files_to_index
                    and not files_to_remove
                    and main_indexed
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

                    # 6a. Remove stale chunks from main
                    if files_to_remove and main_indexed:
                        removed = self._vector_store.delete_by_sources(
                            collection_name, list(files_to_remove),
                        )
                        logger.info(f"Removed {removed} stale chunks")

                    # 6b. Hash entries for deleted files
                    if deleted_files:
                        self._indexing_repo.delete_file_hash_entries(
                            repository_url, model_name, strategy_name,
                            list(deleted_files),
                        )

                    # 6c. Chunk and index new/changed files into main (branch='')
                    if files_to_index:
                        _report(20, "Chunking and embedding files...")
                        files_to_chunk = [
                            (path, content) for path, content in files
                            if path in files_to_index
                        ]
                        chunks = self._chunking.chunk_files(files_to_chunk)

                        repo_name_str = Path(repo_path).name
                        for chunk in chunks:
                            chunk.repo_name = repo_name_str

                        logger.info(
                            f"Split {len(files_to_chunk)} files "
                            f"into {len(chunks)} chunks"
                        )
                        num_indexed = self._vector_store.index_documents(
                            chunks=chunks,
                            collection_name=collection_name,
                        )
                        _report(65, f"Indexed {num_indexed} chunks")

                    # 6d. Update indexed_repositories
                    total = self._vector_store.collection_count(collection_name)
                    ir_id = self._indexing_repo.save_indexed_repo(
                        repo_url=repository_url,
                        collection_name=collection_name,
                        num_chunks=total,
                        embedding_model=model_name,
                        chunking_strategy=strategy_name,
                    )

                    # 6e. Update file hashes
                    self._indexing_repo.save_file_hashes(ir_id, current_hashes)

            # 7. Repomap
            _report(70, "Generating repository map...")
            repomap = self._repomap.generate(repo_path)

            # 8. Similarity search per rule
            # PR delta mode: UNION search (main + delta, PR version wins on conflict)
            # Standard mode: search main only
            search_pr_branch = pr_branch if use_pr_delta else None
            validations: List[RuleValidation] = []
            for idx, rule in enumerate(rules):
                pct = 72 + int((idx / max(len(rules), 1)) * 8)
                _report(pct, f"Searching for rule {idx + 1}/{len(rules)}...")
                logger.info(f"Searching for rule: {rule[:80]}...")

                results = self._vector_store.similarity_search(
                    query=rule,
                    collection_name=collection_name,
                    threshold=self._similarity_threshold,
                    max_results=max_chunks_per_rule if max_chunks_per_rule is not None else self._max_results,
                    pr_branch=search_pr_branch,
                )
                file_matches = self._results_to_file_matches(
                    results, repo_path,
                    self._max_file_content_size,
                )
                validations.append(
                    RuleValidation(rule=rule, related_files=file_matches),
                )
                logger.info(
                    f"  -> {len(file_matches)} files matched "
                    f"(from {len(results)} chunks)"
                )

            # 9. LLM evaluation -- one rule at a time
            # Restore already-evaluated rules from partial results
            saved = partial_results or []
            cross_check_active = enable_cross_check if enable_cross_check is not None else False

            # Resolve effective LLM instances (per-repo overrides take precedence)
            effective_llm = llm_override or self._llm
            effective_llm_primary = llm_primary_override or self._llm_primary
            effective_llm_secondary = llm_secondary_override or self._llm_secondary

            if cross_check_active:
                _report(80, "Evaluating rules with cross-check (dual-model)...")
                for idx, validation in enumerate(validations):
                    if idx < len(saved):
                        self._restore_cross_check(validation, saved[idx])
                        logger.info(
                            f"Rule {idx + 1} restored from partial results "
                            f"(verdict={validation.evaluation.verdict if validation.evaluation else 'n/a'})"
                        )
                        continue

                    pct = 80 + int((idx / max(len(validations), 1)) * 14)
                    _report(pct, f"Cross-checking rule {idx + 1}/{len(validations)}...")
                    logger.info(f"Cross-checking rule {idx + 1}: {validation.rule[:80]}...")

                    file_contents = [fm.file_content for fm in validation.related_files]
                    eval_kwargs = dict(
                        rule=validation.rule,
                        repomap=repomap,
                        file_contents=file_contents,
                        repository_url=repository_url,
                    )

                    primary_eval = effective_llm_primary.evaluate_rule(**eval_kwargs)
                    secondary_eval = effective_llm_secondary.evaluate_rule(**eval_kwargs)

                    final_eval, cross_checked = self._cross_check_service.reconcile(
                        validation.rule, primary_eval, secondary_eval,
                    )
                    validation.evaluation = final_eval
                    validation.cross_check = cross_checked
                    logger.info(
                        f"  -> agreement={cross_checked.agreement} "
                        f"discriminator_used={cross_checked.discriminator_used} "
                        f"verdict={final_eval.verdict}"
                    )

                    if on_rule_evaluated:
                        on_rule_evaluated(idx, validation)

                result_llm_model = effective_llm_primary.name

            else:
                _report(80, "Evaluating rules with LLM...")
                for idx, validation in enumerate(validations):
                    if idx < len(saved):
                        self._restore_evaluation(validation, saved[idx])
                        logger.info(
                            f"Rule {idx + 1} restored from partial results "
                            f"(verdict={validation.evaluation.verdict if validation.evaluation else 'n/a'})"
                        )
                        continue

                    pct = 80 + int((idx / max(len(validations), 1)) * 14)
                    _report(pct, f"LLM evaluating rule {idx + 1}/{len(validations)}...")
                    logger.info(f"LLM evaluating rule {idx + 1}: {validation.rule[:80]}...")

                    file_contents = [fm.file_content for fm in validation.related_files]
                    evaluation = effective_llm.evaluate_rule(
                        rule=validation.rule,
                        repomap=repomap,
                        file_contents=file_contents,
                        repository_url=repository_url,
                    )
                    validation.evaluation = evaluation
                    logger.info(f"  -> verdict={evaluation.verdict}")

                    if on_rule_evaluated:
                        on_rule_evaluated(idx, validation)

                result_llm_model = effective_llm.name

            _report(98, "Building result...")

            # 10. Result
            result = ValidationResult(
                id=str(uuid.uuid4()),
                repository_url=repository_url,
                repomap=repomap,
                validations=validations,
                embedding_model=model_name,
                chunking_strategy=strategy_name,
                llm_model=result_llm_model,
                processing_time_seconds=round(time.monotonic() - _start, 2),
            )

            _report(100, "Done")
            return result

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise
        finally:
            if repo_path:
                self._repository.cleanup(repo_path)
            if use_pr_delta and pr_branch and collection_name:
                try:
                    deleted = self._vector_store.delete_branch(
                        collection_name, pr_branch,
                    )
                    logger.info(
                        f"Cleaned up PR delta: {deleted} chunks removed "
                        f"(branch='{pr_branch}')"
                    )
                except Exception as e:
                    logger.warning(f"Could not clean up PR delta: {e}")

    # Helpers

    @staticmethod
    def _collection_name(
        repo_url: str, model_name: str, strategy_name: str,
    ) -> str:
        raw = f"{repo_url}|{model_name}|{strategy_name}"
        return hashlib.md5(raw.encode()).hexdigest()  # 32 chars, always unique

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
    def _restore_evaluation(validation: "RuleValidation", saved: dict) -> None:
        ev = saved.get("evaluation") or {}
        validation.evaluation = RuleEvaluation(
            verdict=ev.get("verdict", "fail"),
            explanation=ev.get("explanation", ""),
            suggestions=ev.get("suggestions", []),
            llm_provider=ev.get("llm_provider", ""),
            tokens_used=ev.get("tokens_used", 0),
        )

    @staticmethod
    def _restore_cross_check(validation: "RuleValidation", saved: dict) -> None:
        ValidationService._restore_evaluation(validation, saved)
        cc = saved.get("cross_check")
        if cc:
            primary = RuleEvaluation(
                verdict=cc.get("primary_verdict", "fail"),
                explanation=cc.get("primary_explanation", ""),
                llm_provider=cc.get("primary_model", ""),
                suggestions=cc.get("primary_suggestions", []),
            )
            secondary = RuleEvaluation(
                verdict=cc.get("secondary_verdict", "fail"),
                explanation=cc.get("secondary_explanation", ""),
                llm_provider=cc.get("secondary_model", ""),
                suggestions=cc.get("secondary_suggestions", []),
            )
            validation.cross_check = CrossCheckedEvaluation(
                primary=primary,
                secondary=secondary,
                agreement=cc.get("agreement", False),
                discriminator_used=cc.get("discriminator_used", False),
                discriminator_model=cc.get("discriminator_model"),
                discriminator_reasoning=cc.get("discriminator_reasoning"),
            )

    @staticmethod
    def _compute_file_hashes(files: List[Tuple[str, str]]) -> dict:
        hashes = {}
        for path, content in files:
            hashes[path] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return hashes
