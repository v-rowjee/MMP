-- MMP — initial schema (v3)
-- Run once in the Supabase SQL editor, or save as a CLI migration:
--   supabase migration new init
--
-- Three metadata tables. User data lives in per-workspace schemas
-- (ws_xxxxxxxx) created at runtime and is not part of this script.
--
-- Data placement: uploaded rows are materialised into the workspace schema so
-- generated SQL can join and run pgvector filters in one statement. The
-- original file stays in Supabase Storage at {workspace_id}/{dataset_id}.csv
-- so ingest is replayable.
--
-- Safe to re-run: every statement is idempotent.

-- ============================================================ extensions

create extension if not exists vector  with schema extensions;  -- embedding columns
create extension if not exists pg_trgm with schema extensions;  -- FK inference


-- ============================================================ workspaces
-- One per user, enforced by the unique constraint on user_id.
-- The id IS the Postgres schema name.
--
-- Three columns because there is nothing else true about a workspace. No
-- display name — with one per user there is no switcher to show it in. No
-- updated_at, because nothing here is mutable.

create table if not exists public.workspaces (
    id         text        primary key,
    user_id    uuid        not null unique references auth.users (id) on delete cascade,
    created_at timestamptz not null default now(),

    constraint workspaces_id_format check (id ~ '^ws_[a-z0-9]{8}$')
);


-- ============================================================ datasets
-- One row per uploaded table. `name` is the physical table name inside the
-- workspace schema.
--
-- No primary_key or time_column here: dataset_fields.role already records
-- which field is an id and which is a time axis. If two fields ever share a
-- role and one must be canonical, that flag belongs on the field.
--
-- `meta` holds what ingest learned but nothing queries on: parse warnings,
-- detected delimiter, encoding, header offset. Promote a key to a real column
-- when something needs to filter by it, not before.

create table if not exists public.datasets (
    id              uuid        primary key default gen_random_uuid(),
    workspace_id    text        not null references public.workspaces (id) on delete cascade,
    name            text        not null,
    source_filename text        not null,
    status          text        not null default 'ready',
    row_count       bigint      not null default 0,
    meta            jsonb       not null default '{}'::jsonb,
    uploaded_at     timestamptz not null default now(),

    constraint datasets_unique_name   unique (workspace_id, name),
    constraint datasets_name_format   check (name ~ '^[a-z_][a-z0-9_]{0,62}$'),
    constraint datasets_row_count_pos check (row_count >= 0),
    constraint datasets_status_valid  check (status in ('ingesting', 'ready', 'failed'))
);

create index if not exists datasets_workspace_idx
    on public.datasets (workspace_id, uploaded_at desc);


-- ============================================================ dataset_fields
-- One row per user-visible column. Read by the schema card, the SQL guard
-- whitelist and every agent gate.
--
-- System columns (__row_id, *__embedding) are deliberately absent, which is
-- what keeps them invisible to the planner.
--
-- Keyed by (dataset_id, name) — names are already unique per dataset and
-- nothing references a field by surrogate id.

create table if not exists public.dataset_fields (
    dataset_id       uuid    not null references public.datasets (id) on delete cascade,
    name             text    not null,
    original_name    text    not null,
    position         int     not null,
    dtype            text    not null,
    role             text    not null,
    embedding_column text,
    profile          jsonb   not null default '{}'::jsonb,

    primary key (dataset_id, name),

    constraint fields_name_format check (name ~ '^[a-z_][a-z0-9_]{0,62}$'),
    constraint fields_role_valid
        check (role in ('time', 'measure', 'dimension', 'id', 'text')),
    constraint fields_unique_position
        unique (dataset_id, position) deferrable initially immediate
);


-- ============================================================ row level security
-- The anon key ships to the browser, so every table in `public` is reachable
-- through PostgREST. RLS enabled with NO policies denies all client access.
-- The backend connects as `postgres`, which bypasses RLS entirely.
--
-- A read policy later is a single join:
--   using (exists (select 1 from public.workspaces w
--                  where w.id = workspace_id and w.user_id = auth.uid()))

alter table public.workspaces     enable row level security;
alter table public.datasets       enable row level security;
alter table public.dataset_fields enable row level security;

alter table public.workspaces     force row level security;
alter table public.datasets       force row level security;
alter table public.dataset_fields force row level security;


-- ============================================================ read-only role
-- Generated SQL executes as this role. Granted usage on ws_* schemas
-- individually at workspace creation time, and never on `public`.

do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'mmp_readonly') then
        create role mmp_readonly nologin;
    end if;
end
$$;

revoke all on schema public from mmp_readonly;


-- ============================================================ verify

-- select table_name from information_schema.tables
--   where table_schema = 'public' order by table_name;
-- select extname, extversion from pg_extension where extname in ('vector', 'pg_trgm');