create table prediction_log (
    request_id uuid primary key,
    created_at timestamptz not null default now(),
    endpoint text not null check (endpoint in ('predict', 'explain')),
    model_version text not null,
    model_sha256 text not null,
    features jsonb not null,
    probability_bad double precision not null check (probability_bad between 0 and 1),
    threshold double precision not null,
    prediction text not null check (prediction in ('bad', 'good')),
    latency_ms double precision not null check (latency_ms >= 0)
);

-- Para el reporte de drift por rango de fechas y la limpieza por retención
create index prediction_log_created_at_idx on prediction_log (created_at);
