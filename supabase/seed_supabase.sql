-- ============================================================
-- INVESAKK SAS — Gestión Logística
-- NIT 802014471-6 · Barranquilla, Colombia
-- SEED COMPLETO: Schema + Usuarios + Datos iniciales
-- Ejecutar en: Supabase → SQL Editor → New query
-- ============================================================

-- ── Extensiones ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Limpiar tablas existentes ─────────────────────────────────
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

-- ── Índices ───────────────────────────────────────────────────
CREATE INDEX idx_facturas_cond_key ON facturas (cond_key);
CREATE INDEX idx_facturas_fec_entr ON facturas (fec_entr);

-- ── Row Level Security ────────────────────────────────────────
ALTER TABLE usuarios    ENABLE ROW LEVEL SECURITY;
ALTER TABLE conductores ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturas    ENABLE ROW LEVEL SECURITY;
ALTER TABLE gps         ENABLE ROW LEVEL SECURITY;
ALTER TABLE bodegas     ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all" ON usuarios    FOR ALL USING (true);
CREATE POLICY "service_role_all" ON conductores FOR ALL USING (true);
CREATE POLICY "service_role_all" ON facturas    FOR ALL USING (true);
CREATE POLICY "service_role_all" ON gps         FOR ALL USING (true);
CREATE POLICY "service_role_all" ON bodegas     FOR ALL USING (true);

-- ── USUARIOS (contraseñas en SHA-256) ────────────────────────
-- admin       / admin2026
-- jefe.logistica / jefe2026
-- landero     / aux2026
-- roa.julio   / roa2026
-- martinez.luis / mart2026
-- marin.jose  / marin2026
-- mendoza.luis / mend2026
-- nino.ademir / nino2026
-- ayud.*      / ayud2026

INSERT INTO usuarios (usuario, password, role, cond_key, nombre, cargo, sede, celular) VALUES
('admin',           '6051fc84a7a0d74c225fb18a496b09952da5642e60723ecae543298edd7d82d6', 'admin',     NULL,       'Administrador',       'Administrador del Sistema',  'Barranquilla', '300 000 0000'),
('jefe.logistica',  'cc0918e8b7f346f032f8e350a0886b8ed9a73afa83856d917726beac6a253404', 'jefe',      NULL,       'Frank Hernández',     'Jefe de Logística',          'Barranquilla', '300 000 0001'),
('landero',         'c07a8800cbdda585c54a1105571a9456647014ae02755f245a5d927e37387635', 'aux-jefe',  NULL,       'Landero Pérez',       'Auxiliar de Jefatura',       'Barranquilla', '300 000 0002'),
('roa.julio',       '866acb3c4c6010da80ab4f91d1a72ece2a071a531ee17dde8ea3e7daeeca43f1', 'conductor', 'ROA',      'Julio Armando Roa',   'Conductor · WGX062',         'Barranquilla', '301 111 0001'),
('martinez.luis',   '0252f3efcc48fd2a1c16826a0aefd980597a657ab69cfe7215cecbbd35b5a63d', 'conductor', 'MARTINEZ', 'Luis Martínez',       'Conductor · WGX060',         'Barranquilla', '301 111 0002'),
('marin.jose',      '6d3c6cf2a724bc6a9db3957bb022df22946d1860f32bd5ae98bf77a2b4fbf14d', 'conductor', 'MARIN',    'José Marín',          'Conductor · TDU-499',        'Barranquilla', '301 111 0003'),
('mendoza.luis',    '9954489f0dc65e3f16aebd6e6e3d60dddafb107c3d0bb71fce667e6e2ccf4532', 'conductor', 'MENDOZA',  'Luis Mendoza',        'Conductor · WGX061',         'Barranquilla', '301 111 0004'),
('nino.ademir',     '7ffdab54c5cc8adfa47232ef51a5d2deb8907e9836ebdb053a42107234b6fb19', 'conductor', 'NIÑO',     'Ademir Niño',         'Conductor · WGD149',         'Barranquilla', '301 111 0005'),
('ayud.roa',        '9ce11c80b45e5a07eb5dd24d4c5e2825d18fe533f4b8a81ce8c50efda02b3707', 'ayudante',  'ROA',      'Carlos Pérez',        'Ayudante · Ruta ROA',        'Barranquilla', '302 222 0001'),
('ayud.martinez',   '9ce11c80b45e5a07eb5dd24d4c5e2825d18fe533f4b8a81ce8c50efda02b3707', 'ayudante',  'MARTINEZ', 'Jhon Torres',         'Ayudante · Ruta MARTINEZ',   'Barranquilla', '302 222 0002'),
('ayud.marin',      '9ce11c80b45e5a07eb5dd24d4c5e2825d18fe533f4b8a81ce8c50efda02b3707', 'ayudante',  'MARIN',    'Edwin Ospino',        'Ayudante · Ruta MARÍN',      'Barranquilla', '302 222 0003'),
('ayud.mendoza',    '9ce11c80b45e5a07eb5dd24d4c5e2825d18fe533f4b8a81ce8c50efda02b3707', 'ayudante',  'MENDOZA',  'Ricardo Vargas',      'Ayudante · Ruta MENDOZA',    'Barranquilla', '302 222 0004'),
('ayud.nino',       '9ce11c80b45e5a07eb5dd24d4c5e2825d18fe533f4b8a81ce8c50efda02b3707', 'ayudante',  'NIÑO',     'Andrés Blanco',       'Ayudante · Ruta NIÑO',       'Barranquilla', '302 222 0005');

-- ── CONDUCTORES ───────────────────────────────────────────────
INSERT INTO conductores (clave, nombre, short, placa, pedidos, a_tiempo, h24, d2, bono_c, bono_a, meta_c, meta_a, meta_h24) VALUES
('ROA',      'ROA — Julio Armando',  'ROA',   'WGX062',  170, 77, 0, 11,  264200,  132100, 1059600, 529800, 72),
('MARTINEZ', 'MARTINEZ — Luis',       'MART',  'WGX060',  147, 59, 0, 11,  201000,  100500,  965200, 482600, 62),
('MARIN',    'MARÍN — José',          'MARÍN', 'TDU-499',  70, 18, 1,  0,   35200,   17600,  646000, 323000, 30),
('MENDOZA',  'MENDOZA — Luis',        'MEND.', 'WGX061',  200, 14, 0,  1, -110600,  -55300, 1188000, 594000, 85),
('NIÑO',     'NIÑO — Ademir',         'NIÑO',  'WGD149',   66, 11, 0,  3,   -1400,    -700,  626000, 313000, 28);

-- ── GPS ───────────────────────────────────────────────────────
INSERT INTO gps (placa, conductor, vel, acc, brk) VALUES
('WGX062',  'Julio Armando Roa', 2, 1, 3),
('WGX060',  'Luis Martínez',     1, 0, 2),
('TDU-499', 'José Marín',        0, 0, 1),
('WGX061',  'Luis Mendoza',      4, 2, 5),
('WGD149',  'Ademir Niño',       1, 1, 2);

-- ── BODEGAS ───────────────────────────────────────────────────
INSERT INTO bodegas (sede, ped, nt) VALUES
('Barranquilla Centro', 42, 8),
('Barranquilla Norte',  38, 5),
('Barranquilla Sur',    29, 3),
('Soledad',             15, 2),
('Malambo',             11, 1),
('Bogotá D.C.',          9, 0),
('Montería',             7, 0),
('Valledupar',           6, 1),
('Cartagena',            5, 0);

-- ── Vista stats ───────────────────────────────────────────────
CREATE OR REPLACE VIEW v_stats_mes AS
SELECT
    cond_key,
    to_char(fec_entr, 'YYYY-MM') AS mes,
    COUNT(*) AS total,
    SUM(CASE WHEN es_mt = 0 THEN 1 ELSE 0 END) AS pedidos,
    SUM(CASE WHEN es_mt = 1 THEN 1 ELSE 0 END) AS notas_traslado,
    SUM(CASE WHEN fec_entr IS NOT NULL AND es_mt = 0 THEN 1 ELSE 0 END) AS entregadas,
    SUM(CASE WHEN fec_entr IS NULL     AND es_mt = 0 THEN 1 ELSE 0 END) AS pendientes,
    SUM(CASE WHEN fec_entr IS NOT NULL AND es_mt = 0 AND dif_dias <= 5 THEN 1 ELSE 0 END) AS a_tiempo,
    SUM(CASE
        WHEN es_mt = 1 OR fec_entr IS NULL THEN 0
        WHEN dif_dias <= 1  THEN  6000
        WHEN dif_dias <= 2  THEN  5000
        WHEN dif_dias <= 5  THEN  4000
        WHEN dif_dias <= 10 THEN  -400
        WHEN dif_dias <= 20 THEN  -800
        ELSE -2000
    END) AS bono_c
FROM facturas
GROUP BY cond_key, to_char(fec_entr, 'YYYY-MM');

-- ============================================================
-- FIN DEL SCRIPT
-- Credenciales de acceso:
--   admin          / admin2026
--   jefe.logistica / jefe2026
--   landero        / aux2026
--   roa.julio      / roa2026
--   martinez.luis  / mart2026
--   marin.jose     / marin2026
--   mendoza.luis   / mend2026
--   nino.ademir    / nino2026
--   ayud.*         / ayud2026
-- ============================================================
