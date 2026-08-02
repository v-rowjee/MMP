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
    status text not null default 'uploaded' check (status in ('uploaded', 'ready', 'failed')),
    row_count bigint not null default 0,
    meta jsonb not null default '{}'::jsonb,
    uploaded_at timestamptz not null default now(),
    unique (workspace_id, name)
);

create table if not exists public.dataset_fields (
    dataset_id uuid not null references public.datasets(id) on delete cascade,
    name text not null,
    original_name text not null,
    position int not null,
    dtype text not null,
    role text not null,
    profile jsonb not null default '{}'::jsonb,
    primary key (dataset_id, name)
);

create table if not exists public.analysis_runs (
    id uuid primary key default gen_random_uuid(),
    dataset_id uuid not null references public.datasets(id) on delete cascade,
    workspace_id text not null references public.workspaces(id) on delete cascade,
    status text not null check (status in ('dashboard_generating', 'dashboard_ready', 'failed')),
    dashboard jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

alter table public.workspaces enable row level security;
alter table public.datasets enable row level security;
alter table public.dataset_fields enable row level security;
alter table public.analysis_runs enable row level security;

create policy "Users manage their workspace" on public.workspaces
for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "Users manage their datasets" on public.datasets
for all to authenticated
using (
    exists (
        select 1 from public.workspaces
        where workspaces.id = datasets.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1 from public.workspaces
        where workspaces.id = datasets.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
);

create policy "Users manage their dataset fields" on public.dataset_fields
for all to authenticated
using (
    exists (
        select 1 from public.datasets
        join public.workspaces on workspaces.id = datasets.workspace_id
        where datasets.id = dataset_fields.dataset_id
        and workspaces.user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1 from public.datasets
        join public.workspaces on workspaces.id = datasets.workspace_id
        where datasets.id = dataset_fields.dataset_id
        and workspaces.user_id = (select auth.uid())
    )
);

create policy "Users manage their analysis runs" on public.analysis_runs
for all to authenticated
using (
    exists (
        select 1 from public.workspaces
        where workspaces.id = analysis_runs.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1 from public.workspaces
        where workspaces.id = analysis_runs.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('upload', 'upload', false, 52428800, array['text/csv', 'application/vnd.apache.parquet'])
on conflict (id) do update set public = false, file_size_limit = 52428800, allowed_mime_types = array['text/csv', 'application/vnd.apache.parquet'];

create policy "Users manage their upload objects" on storage.objects
for all to authenticated
using (
    bucket_id = 'upload'
    and exists (
        select 1 from public.workspaces
        where workspaces.id = (storage.foldername(name))[1]
        and workspaces.user_id = (select auth.uid())
    )
)
with check (
    bucket_id = 'upload'
    and exists (
        select 1 from public.workspaces
        where workspaces.id = (storage.foldername(name))[1]
        and workspaces.user_id = (select auth.uid())
    )
);
