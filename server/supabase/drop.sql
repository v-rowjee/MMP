drop policy if exists "Users manage their upload objects" on storage.objects;
delete from storage.objects where bucket_id = 'upload';
delete from storage.buckets where id = 'upload';

drop table if exists public.analysis_runs cascade;
drop table if exists public.dataset_schemas cascade;
drop table if exists public.dataset_files cascade;
drop table if exists public.dataset_fields cascade;
drop table if exists public.datasets cascade;
drop table if exists public.workspaces cascade;
