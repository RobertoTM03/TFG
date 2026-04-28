CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE; -- also installs pgvector

-- Users authenticated via GitHub OAuth
CREATE TABLE IF NOT EXISTS users (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id      INTEGER UNIQUE NOT NULL,
    github_login   TEXT NOT NULL,
    avatar_url     TEXT NOT NULL DEFAULT '',
    access_token   TEXT NOT NULL,
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_token ON users (access_token);

-- GitHub App installations                                            --
-- One row per (installation_id). account_login is the GitHub         --
CREATE TABLE IF NOT EXISTS installations (
    installation_id  BIGINT PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_login    TEXT NOT NULL,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_installations_user    ON installations (user_id);
CREATE INDEX IF NOT EXISTS idx_installations_account ON installations (user_id, account_login);

-- Validation rules per repository per user
CREATE TABLE IF NOT EXISTS rules (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    repository_full_name  TEXT NOT NULL,
    rule_text             TEXT NOT NULL,
    position              INTEGER NOT NULL DEFAULT 0,
    created_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rules_user_repo ON rules (user_id, repository_full_name);

-- Validation tasks (background processing)
CREATE TABLE IF NOT EXISTS tasks (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                UUID REFERENCES users(id) ON DELETE SET NULL,
    repository_url         TEXT NOT NULL,
    repository_full_name   TEXT NOT NULL,
    rules                  JSONB NOT NULL,
    status                 TEXT NOT NULL DEFAULT 'pending',
    progress               INTEGER NOT NULL DEFAULT 0,
    progress_message       TEXT NOT NULL DEFAULT '',
    result                 JSONB,
    error                  TEXT,
    enable_cross_check     BOOLEAN NOT NULL DEFAULT FALSE,
    github_installation_id BIGINT,
    pr_number              INTEGER,
    pr_head_sha            TEXT,
    pr_head_ref            TEXT,
    pr_author              TEXT,
    partial_result         JSONB,
    retry_count            INTEGER NOT NULL DEFAULT 0,
    retry_after            TIMESTAMP WITH TIME ZONE,
    created_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at             TIMESTAMP WITH TIME ZONE,
    completed_at           TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_tasks_user        ON tasks (user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status      ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_pr_author   ON tasks (pr_author);
CREATE INDEX IF NOT EXISTS idx_tasks_repo_pr     ON tasks (repository_full_name, pr_number);
CREATE INDEX IF NOT EXISTS idx_tasks_retry_after ON tasks (retry_after) WHERE status = 'pending';

-- Shared task access (view-only grants)
CREATE TABLE IF NOT EXISTS task_viewers (
    task_id    UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (task_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_task_viewers_user ON task_viewers (user_id);

-- Repository registry — single source of truth for repo identity
CREATE TABLE IF NOT EXISTS repositories (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url        TEXT UNIQUE NOT NULL,
    full_name  TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexed repositories cache (vector store collections)
CREATE TABLE IF NOT EXISTS indexed_repositories (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id     UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    collection_name   TEXT UNIQUE NOT NULL,
    num_chunks        INTEGER DEFAULT 0,
    embedding_model   TEXT NOT NULL,
    chunking_strategy TEXT NOT NULL,
    indexed_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(repository_id, embedding_model, chunking_strategy)
);

-- File content hashes for incremental indexing
CREATE TABLE IF NOT EXISTS file_hashes (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    indexed_repository_id UUID NOT NULL REFERENCES indexed_repositories(id) ON DELETE CASCADE,
    file_path             TEXT NOT NULL,
    content_hash          TEXT NOT NULL,
    updated_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(indexed_repository_id, file_path)
);

CREATE INDEX IF NOT EXISTS idx_file_hashes_lookup
    ON file_hashes (indexed_repository_id);

-- Per-repository configuration set by repository owners
CREATE TABLE IF NOT EXISTS repo_configs (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    repository_full_name    TEXT NOT NULL,
    max_evaluations_per_pr  INTEGER NOT NULL DEFAULT 3,
    approval_threshold      FLOAT   NOT NULL DEFAULT 0.8,
    enable_cross_check      BOOLEAN NOT NULL DEFAULT TRUE,
    pr_evaluation_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
    max_chunks_per_rule     INTEGER NOT NULL DEFAULT 5,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, repository_full_name)
);

CREATE INDEX IF NOT EXISTS idx_repo_configs_user_repo
    ON repo_configs (user_id, repository_full_name);
