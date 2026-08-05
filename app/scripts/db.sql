create extension if not exists pgcrypto;

create table public.workspaces (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);

create table public.datasets (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    name text not null check (name ~ '^[a-z_][a-z0-9_]{0,62}$'),
    source_filename text not null,
    status text not null default 'uploaded' check (status in ('uploaded', 'ready', 'failed')),
    row_count bigint not null default 0,
    meta jsonb not null default '{}'::jsonb,
    uploaded_at timestamptz not null default now(),
    unique (workspace_id, name)
);

create table public.dataset_fields (
    dataset_id uuid not null references public.datasets(id) on delete cascade,
    name text not null,
    original_name text not null,
    position int not null,
    dtype text not null,
    role text not null,
    profile jsonb not null default '{}'::jsonb,
    primary key (dataset_id, name)
);

create table public.analysis_runs (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    status text not null check (status in ('dashboard_generating', 'dashboard_ready', 'failed')),
    dashboard jsonb not null default '{}'::jsonb,
    failure_stage text,
    failure_diagnostic text,
    created_at timestamptz not null default now()
);

create table public.analysis_run_datasets (
    analysis_id uuid not null references public.analysis_runs(id) on delete cascade,
    dataset_id uuid not null references public.datasets(id) on delete cascade,
    primary key (analysis_id, dataset_id)
);

grant usage on schema public to authenticated;
grant select, insert, update, delete on public.workspaces to authenticated;
grant select, insert, update, delete on public.datasets to authenticated;
grant select, insert, update, delete on public.dataset_fields to authenticated;
grant select, insert, update, delete on public.analysis_runs to authenticated;
grant select, insert, update, delete on public.analysis_run_datasets to authenticated;

alter table public.workspaces enable row level security;
alter table public.datasets enable row level security;
alter table public.dataset_fields enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.analysis_run_datasets enable row level security;

create policy "Users manage their workspace" on public.workspaces
for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "Users manage their datasets" on public.datasets
for all to authenticated
using (
    exists (
        select 1
        from public.workspaces
        where workspaces.id = datasets.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1
        from public.workspaces
        where workspaces.id = datasets.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
);

create policy "Users manage their dataset fields" on public.dataset_fields
for all to authenticated
using (
    exists (
        select 1
        from public.datasets
        join public.workspaces on workspaces.id = datasets.workspace_id
        where datasets.id = dataset_fields.dataset_id
        and workspaces.user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1
        from public.datasets
        join public.workspaces on workspaces.id = datasets.workspace_id
        where datasets.id = dataset_fields.dataset_id
        and workspaces.user_id = (select auth.uid())
    )
);

create policy "Users manage their analysis runs" on public.analysis_runs
for all to authenticated
using (
    exists (
        select 1
        from public.workspaces
        where workspaces.id = analysis_runs.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1
        from public.workspaces
        where workspaces.id = analysis_runs.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
);

create policy "Users manage their analysis run datasets" on public.analysis_run_datasets
for all to authenticated
using (
    exists (
        select 1
        from public.analysis_runs
        join public.workspaces on workspaces.id = analysis_runs.workspace_id
        join public.datasets on datasets.id = analysis_run_datasets.dataset_id
        where analysis_runs.id = analysis_run_datasets.analysis_id
        and datasets.workspace_id = analysis_runs.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
)
with check (
    exists (
        select 1
        from public.analysis_runs
        join public.workspaces on workspaces.id = analysis_runs.workspace_id
        join public.datasets on datasets.id = analysis_run_datasets.dataset_id
        where analysis_runs.id = analysis_run_datasets.analysis_id
        and datasets.workspace_id = analysis_runs.workspace_id
        and workspaces.user_id = (select auth.uid())
    )
);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('upload', 'upload', false, 52428800, array['text/csv', 'application/vnd.apache.parquet']);

create policy "Users manage their upload objects" on storage.objects
for all to authenticated
using (
    bucket_id = 'upload'
    and exists (
        select 1
        from public.workspaces
        where workspaces.id = (storage.foldername(name))[1]::uuid
        and workspaces.user_id = (select auth.uid())
    )
)
with check (
    bucket_id = 'upload'
    and exists (
        select 1
        from public.workspaces
        where workspaces.id = (storage.foldername(name))[1]::uuid
        and workspaces.user_id = (select auth.uid())
    )
);
