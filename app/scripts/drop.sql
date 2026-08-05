DO $$ 
BEGIN
    -- 1. Execute deletion by bypassing constraint checks via a cascade truncate
    -- This ignores the triggers by dropping data directly at the table level
    TRUNCATE storage.objects RESTART IDENTITY CASCADE;
    TRUNCATE storage.buckets RESTART IDENTITY CASCADE;

    RAISE NOTICE 'All Supabase buckets and files have been successfully deleted.';
EXCEPTION WHEN OTHERS THEN
    -- 2. Fallback: If truncate is blocked, loop and drop via internal storage schema functions
    DECLARE
        bucket_record RECORD;
    BEGIN
        FOR bucket_record IN SELECT id FROM storage.buckets LOOP
            DELETE FROM storage.objects WHERE bucket_id = bucket_record.id;
            DELETE FROM storage.buckets WHERE id = bucket_record.id;
        END LOOP;
    END;
END $$;



drop table if exists public.analysis_run_datasets cascade;
drop table if exists public.analysis_runs cascade;
drop table if exists public.dataset_schemas cascade;
drop table if exists public.dataset_files cascade;
drop table if exists public.dataset_fields cascade;
drop table if exists public.datasets cascade;
drop table if exists public.workspaces cascade;
