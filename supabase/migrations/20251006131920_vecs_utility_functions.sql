-- Schema for utility functions
create schema util;

-- Utility function to get the Supabase project URL (required for Edge Functions)
create function util.project_url()
returns text
language sql
immutable
as $$
  select 'https://fxxbesjfsiygzqmqmwwr.supabase.co'::text;
$$;

-- Placeholder for service role key function
-- This will be overwritten by a local-only migration (*_set_service_role_key_local.sql)
-- that is gitignored and contains the actual service role key
create function util.service_role_key()
returns text
language sql
immutable
security definer
as $$
  select 'REPLACE_WITH_SERVICE_ROLE_KEY'::text;
$$;

-- Generic function to invoke any Edge Function
create or replace function util.invoke_edge_function(
  name text,
  body jsonb,
  timeout_milliseconds int = 5 * 60 * 1000  -- default 5 minute timeout
)
returns void
language plpgsql
security definer
as $$
declare
  headers_raw text;
  auth_header text;
begin
  -- If we're in a PostgREST session, reuse the request headers for authorization
  headers_raw := current_setting('request.headers', true);

  -- Determine which authorization to use
  auth_header := case
    when headers_raw is not null then
      (headers_raw::json->>'authorization')
    else
      'Bearer ' || util.service_role_key()
  end;

  -- Perform async HTTP request to the edge function
  perform net.http_post(
    url => util.project_url() || '/functions/v1/' || name,
    headers => jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', auth_header
    ),
    body => body,
    timeout_milliseconds => timeout_milliseconds
  );
end;
$$;

-- Generic trigger function to clear a column on update
create or replace function util.clear_column()
returns trigger
language plpgsql as $$
declare
    clear_column text := TG_ARGV[0];
begin
    NEW := NEW #= hstore(clear_column, NULL);
    return NEW;
end;
$$;

-- Queue for processing embedding jobs
select pgmq.create('embedding_jobs');

-- Generic trigger function to queue embedding jobs
create or replace function util.queue_embeddings()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  content_function text = TG_ARGV[0];
  embedding_column text = TG_ARGV[1];
begin
  perform pgmq.send(
    queue_name => 'embedding_jobs',
    msg => jsonb_build_object(
      'id', NEW.id,
      'schema', TG_TABLE_SCHEMA,
      'table', TG_TABLE_NAME,
      'contentFunction', content_function,
      'embeddingColumn', embedding_column
    )
  );
  return NEW;
end;
$$;

-- Function to process embedding jobs from the queue
create or replace function util.process_embeddings(
  batch_size int = 10,
  max_requests int = 10,
  timeout_milliseconds int = 5 * 60 * 1000 -- default 5 minute timeout
)
returns void
language plpgsql
as $$
declare
  job_batches jsonb[];
  batch jsonb;
begin
  with
    -- First get jobs and assign batch numbers
    numbered_jobs as (
      select
        message || jsonb_build_object('jobId', msg_id) as job_info,
        (row_number() over (order by 1) - 1) / batch_size as batch_num
      from pgmq.read(
        queue_name => 'embedding_jobs',
        vt => timeout_milliseconds / 1000,
        qty => max_requests * batch_size
      )
    ),
    -- Then group jobs into batches
    batched_jobs as (
      select
        jsonb_agg(job_info) as batch_array,
        batch_num
      from numbered_jobs
      group by batch_num
    )
  -- Finally aggregate all batches into array
  select array_agg(batch_array)
  from batched_jobs
  into job_batches;

  -- Only process if there are jobs
  if job_batches is not null then
    -- Invoke the embed edge function for each batch
    foreach batch in array job_batches loop
      perform util.invoke_edge_function(
        name => 'embed',
        body => batch,
        timeout_milliseconds => timeout_milliseconds
      );
    end loop;
  end if;
end;
$$;

-- Schedule the embedding processing
select
  cron.schedule(
    'process-embeddings',
    '10 seconds',
    $$
    select util.process_embeddings();
    $$
  );
