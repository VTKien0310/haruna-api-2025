CREATE TABLE medias (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    name TEXT NOT NULL,
    type INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    thumbnail_path TEXT,
    mime TEXT NOT NULL DEFAULT '',
    size INTEGER NOT NULL DEFAULT 0,
    uploader_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE translation_histories (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    owner_id TEXT NOT NULL,
    source_language TEXT NOT NULL,
    target_language TEXT NOT NULL,
    source_text TEXT NOT NULL,
    translation TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE profiles (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    user_id TEXT,
    name TEXT,
    birth_date TEXT NOT NULL,
    work_start_date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE pto_banks (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    owner_id TEXT NOT NULL,
    annual_balance INTEGER NOT NULL,
    extended_balance INTEGER NOT NULL,
    seniority_balance INTEGER NOT NULL,
    year INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE pto_affect_entries (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    entry_id TEXT,
    entry_type TEXT,
    no_deduction INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE pto_transactions (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    pto_bank_id TEXT NOT NULL REFERENCES pto_banks (id),
    entry_id TEXT NOT NULL REFERENCES pto_affect_entries (id),
    cause TEXT NOT NULL,
    value INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE TABLE check_in_entries (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL
);

CREATE TABLE leave_work_entries (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    date TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL
);

CREATE TABLE remote_work_entries (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    date TEXT NOT NULL,
    type INTEGER NOT NULL
);

CREATE TABLE time_off_entries (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    date TEXT NOT NULL,
    type INTEGER NOT NULL
);

CREATE TABLE work_time_entries (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    date TEXT NOT NULL,
    type INTEGER NOT NULL
);

CREATE TABLE workday_exceptions (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))) NOT NULL,
    type INTEGER NOT NULL,
    date TEXT NOT NULL,
    time INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
