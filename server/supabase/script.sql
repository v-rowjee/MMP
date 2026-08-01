create extension if not exists vector with schema extensions;
create extension if not exists pg_trgm with schema extensions;

create table if not exists public.workspaces (
    id text primary key check (id ~ '^ws_[a-z0-9]{8}$'),
    user_id uuid not null unique references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);

create table if not exists public.datasets (
    id uuid primary key default gen_random_uuid(),
    workspace_id text not null references public.workspaces(id) on delete cascade,
    name text not null check (name ~ '^[a-z_][a-z0-9_]{0,62}$'),
    source_filename text not null,
    status text not null default 'uploaded' check (status in ('uploaded', 'ingesting', 'ready', 'failed')),
    row_count bigint not null default 0 check (row_count >= 0),
    meta jsonb not null default '{}'::jsonb,
    uploaded_at timestamptz not null default now(),
    unique (workspace_id, name)
);

create table if not exists public.dataset_fields (
    dataset_id uuid not null references public.datasets(id) on delete cascade,
    name text not null check (name ~ '^[a-z_][a-z0-9_]{0,62}$'),
    original_name text not null,
    position int not null,
    dtype text not null,
    role text not null check (role in ('time', 'measure', 'dimension', 'id', 'text')),
    embedding_column text,
    profile jsonb not null default '{}'::jsonb,
    primary key (dataset_id, name),
    unique (dataset_id, position)
);

alter table public.workspaces enable row level security;
alter table public.datasets enable row level security;
alter table public.dataset_fields enable row level security;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('upload', 'upload', false, 52428800, array['text/csv'])
on conflict (id) do update set public = false, file_size_limit = 52428800, allowed_mime_types = array['text/csv'];
