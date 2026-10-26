-- Migration: create bulk_upload_jobs table
-- Run this once against the production database if alembic is not set up.

CREATE TABLE IF NOT EXISTS bulk_upload_jobs (
    id SERIAL PRIMARY KEY,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    csv_filename VARCHAR(255) NOT NULL,
    csv_content BYTEA NOT NULL,
    total_rows INTEGER,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    successful INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    errors JSONB,
    created_users JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_bulk_upload_jobs_created_by_id
    ON bulk_upload_jobs (created_by_id);

CREATE INDEX IF NOT EXISTS ix_bulk_upload_jobs_status
    ON bulk_upload_jobs (status);

CREATE INDEX IF NOT EXISTS ix_bulk_upload_jobs_created_at
    ON bulk_upload_jobs (created_at DESC);
