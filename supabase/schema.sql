-- ============================================================
-- INVESAKK SAS — Gestión Logística
-- NIT 802014471-6 · Barranquilla, Colombia
-- Schema PostgreSQL para Supabase
-- Ejecutar en: Supabase → SQL Editor → New query
-- ============================================================

-- ── Extensiones ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Limpiar (útil para re-ejecutar) ──────────────────────────
DROP TABLE IF EXISTS facturas    CASCADE;
DROP TABLE IF EXISTS gps         CASCADE;
DROP TABLE IF EXISTS bodegas     CASCADE;
DROP TABLE IF EXISTS conductores CASCADE;
DROP TABLE IF EXISTS usuarios    CASCADE;

-- ── Tablas ───────────────────────────────────────────────────

CREATE TABLE usuarios (
    usuario   TEXT PRIMARY KEY,
    password  TEXT NOT NULL,
    role      TEXT NOT NULL CHECK (role IN ('admin','jefe','aux-jefe','conductor','ayudante')),
    cond_key  TEXT,
    nombre    TEXT,
    cargo     TEXT,
    sede      TEXT,
    celular   TEXT
);

CREATE TABLE conductores (
    clave     TEXT PRIMARY KEY,
    nombre    TEXT,
    short     TEXT,
    placa     TEXT,
    pedidos   INTEGER  DEFAULT 0,
    a_tiempo  INTEGER  DEFAULT 0,
    h24       INTEGER  DEFAULT 0,
    d2        INTEGER  DEFAULT 0,
    bono_c    NUMERIC  DEFAULT 0,
    bono_a    NUMERIC  DEFAULT 0,
    meta_c    NUMERIC  DEFAULT 0,
    meta_a    NUMERIC  DEFAULT 0,
    meta_h24  INTEGER  DEFAULT 0
);

CREATE TABLE facturas (
    id          BIGSERIAL PRIMARY KEY,
    cond_key    TEXT      NOT NULL REFERENCES conductores(clave) ON DELETE CASCADE,
    num         TEXT,
    tipo        TEXT,
    tip_desc    TEXT,
    cliente     TEXT,
    ciudad      TEXT,
    dpto        TEXT,
    placa       TEXT,
    valor       NUMERIC,
    peso        NUMERIC,
    fec_fact    DATE,
    fec_promesa DATE,
    fec_entr    DATE,
    dif_dias    NUMERIC,
    dif_horas   NUMERIC,
    es_mt       SMALLINT  DEFAULT 0
);

CREATE TABLE gps (
    id        BIGSERIAL PRIMARY KEY,
    placa     TEXT,
    conductor TEXT,
    vel       INTEGER DEFAULT 0,
    acc       INTEGER DEFAULT 0,
    brk       INTEGER DEFAULT 0
);

CREATE TABLE bodegas (
    id    BIGSERIAL PRIMARY KEY,
    sede  TEXT,
    ped   INTEGER DEFAULT 0,
    nt    INTEGER DEFAULT 0
);

-- ── Índices para las consultas más frecuentes ─────────────────
CREATE INDEX idx_facturas_cond_key  ON facturas (cond_key);
CREATE INDEX idx_facturas_fec_entr  ON facturas (fec_entr);
CREATE INDEX idx_facturas_mes       ON facturas (to_char(fec_entr, 'YYYY-MM'));

-- ── Row Level Security (RLS) ──────────────────────────────────
-- Habilitar RLS en todas las tablas
ALTER TABLE usuarios    ENABLE ROW LEVEL SECURITY;
ALTER TABLE conductores ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturas    ENABLE ROW LEVEL SECURITY;
ALTER TABLE gps         ENABLE ROW LEVEL SECURITY;
ALTER TABLE bodegas     ENABLE ROW LEVEL SECURITY;

-- Política: solo el service_role (backend) puede leer/escribir todo
-- El frontend llama al backend Flask, que usa el service_role key.
CREATE POLICY "service_role_all" ON usuarios    FOR ALL USING (true);
CREATE POLICY "service_role_all" ON conductores FOR ALL USING (true);
CREATE POLICY "service_role_all" ON facturas    FOR ALL USING (true);
CREATE POLICY "service_role_all" ON gps         FOR ALL USING (true);
CREATE POLICY "service_role_all" ON bodegas     FOR ALL USING (true);

-- ── Vista de stats (equivalente al endpoint /api/stats) ───────
CREATE OR REPLACE VIEW v_stats_mes AS
SELECT
    cond_key,
    to_char(fec_entr, 'YYYY-MM')                                         AS mes,
    COUNT(*)                                                              AS total,
    SUM(CASE WHEN es_mt = 0 THEN 1 ELSE 0 END)                          AS pedidos,
    SUM(CASE WHEN es_mt = 1 THEN 1 ELSE 0 END)                          AS notas_traslado,
    SUM(CASE WHEN fec_entr IS NOT NULL AND es_mt = 0 THEN 1 ELSE 0 END) AS entregadas,
    SUM(CASE WHEN fec_entr IS NULL     AND es_mt = 0 THEN 1 ELSE 0 END) AS pendientes,
    SUM(CASE WHEN fec_entr IS NOT NULL AND es_mt = 0
             AND dif_dias <= 5 THEN 1 ELSE 0 END)                       AS a_tiempo,
    SUM(CASE
        WHEN es_mt = 1 OR fec_entr IS NULL THEN 0
        WHEN dif_dias <= 1  THEN  6000
        WHEN dif_dias <= 2  THEN  5000
        WHEN dif_dias <= 5  THEN  4000
        WHEN dif_dias <= 10 THEN  -400
        WHEN dif_dias <= 20 THEN  -800
        ELSE -2000
    END)                                                                  AS bono_c
FROM facturas
GROUP BY cond_key, to_char(fec_entr, 'YYYY-MM');
