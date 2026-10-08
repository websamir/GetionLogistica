"""
Base de datos — Gestión Logística INVESAKK SAS
NIT 802014471-6 · Barranquilla, Colombia

Soporta dos motores:
  - PostgreSQL (Supabase) cuando DATABASE_URL está definida  ← producción
  - SQLite                                                   ← desarrollo local
"""
import os, hashlib, re
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "")  # ej: postgresql://...

# ── Motor activo ──────────────────────────────────────────────
if DATABASE_URL:
    import psycopg2
    import psycopg2.extras
    USING_PG = True
else:
    import sqlite3
    USING_PG  = False
    DB_PATH   = Path(__file__).parent / "data" / "logistica.db"


# ── Conexión ──────────────────────────────────────────────────
def get_db():
    if USING_PG:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn


def ph(n=1):
    """Devuelve placeholders: %s para PG, ? para SQLite."""
    if USING_PG:
        return ", ".join(["%s"] * n)
    return ", ".join(["?"] * n)


def p():
    """Un solo placeholder."""
    return "%s" if USING_PG else "?"


def rows_to_dicts(rows):
    if USING_PG:
        return [dict(r) for r in rows]
    return [dict(r) for r in rows]


def fetchall(conn, sql, params=()):
    """Ejecuta SELECT y devuelve lista de dicts."""
    sql = _adapt_sql(sql)
    if USING_PG:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    else:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def fetchone(conn, sql, params=()):
    """Ejecuta SELECT y devuelve un dict o None."""
    sql = _adapt_sql(sql)
    if USING_PG:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            r = cur.fetchone()
            return dict(r) if r else None
    else:
        r = conn.execute(sql, params).fetchone()
        return dict(r) if r else None


def execute(conn, sql, params=()):
    """Ejecuta INSERT/UPDATE/DELETE."""
    sql = _adapt_sql(sql)
    if USING_PG:
        with conn.cursor() as cur:
            cur.execute(sql, params)
    else:
        conn.execute(sql, params)


def executemany(conn, sql, param_list):
    """Ejecuta INSERT masivo."""
    sql = _adapt_sql(sql)
    if USING_PG:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, param_list)
    else:
        conn.executemany(sql, param_list)


def commit(conn):
    conn.commit()


def close(conn):
    conn.close()


def _adapt_sql(sql):
    """Convierte ? → %s para PostgreSQL."""
    if USING_PG:
        return sql.replace("?", "%s")
    return sql


# ── Helpers ───────────────────────────────────────────────────
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()


# ── Init (solo SQLite — en PG el schema se aplica con seed_supabase.sql) ──
def init_db():
    if USING_PG:
        return  # En producción el schema ya existe en Supabase

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        usuario   TEXT PRIMARY KEY,
        password  TEXT NOT NULL,
        role      TEXT NOT NULL,
        cond_key  TEXT,
        nombre    TEXT,
        cargo     TEXT,
        sede      TEXT,
        celular   TEXT
    );
    CREATE TABLE IF NOT EXISTS conductores (
        clave     TEXT PRIMARY KEY,
        nombre    TEXT,
        short     TEXT,
        placa     TEXT,
        pedidos   INTEGER DEFAULT 0,
        a_tiempo  INTEGER DEFAULT 0,
        h24       INTEGER DEFAULT 0,
        d2        INTEGER DEFAULT 0,
        bono_c    REAL DEFAULT 0,
        bono_a    REAL DEFAULT 0,
        meta_c    REAL DEFAULT 0,
        meta_a    REAL DEFAULT 0,
        meta_h24  INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS facturas (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        cond_key    TEXT NOT NULL,
        num         TEXT,
        tipo        TEXT,
        tip_desc    TEXT,
        cliente     TEXT,
        ciudad      TEXT,
        dpto        TEXT,
        placa       TEXT,
        valor       REAL,
        peso        REAL,
        fec_fact    TEXT,
        fec_promesa TEXT,
        fec_entr    TEXT,
        dif_dias    REAL,
        dif_horas   REAL,
        es_mt       INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS gps (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        placa     TEXT,
        conductor TEXT,
        vel       INTEGER DEFAULT 0,
        acc       INTEGER DEFAULT 0,
        brk       INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS bodegas (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        sede  TEXT,
        ped   INTEGER DEFAULT 0,
        nt    INTEGER DEFAULT 0
    );
    """)

    if not c.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
        _seed_usuarios(conn)
    if not c.execute("SELECT 1 FROM conductores LIMIT 1").fetchone():
        _seed_conductores(conn)
    if not c.execute("SELECT 1 FROM gps LIMIT 1").fetchone():
        _seed_gps(conn)
    if not c.execute("SELECT 1 FROM bodegas LIMIT 1").fetchone():
        _seed_bodegas(conn)

    conn.commit()
    conn.close()


def _seed_usuarios(conn):
    usuarios = [
        ('admin',          hash_pass('admin2026'),  'admin',     None,       'Administrador',       'Administrador del Sistema',  'Barranquilla', '300 000 0000'),
        ('jefe.logistica', hash_pass('jefe2026'),   'jefe',      None,       'Frank Hernández',     'Jefe de Logística',          'Barranquilla', '300 000 0001'),
        ('landero',        hash_pass('aux2026'),    'aux-jefe',  None,       'Landero Pérez',       'Auxiliar de Jefatura',       'Barranquilla', '300 000 0002'),
        ('roa.julio',      hash_pass('roa2026'),    'conductor', 'ROA',      'Julio Armando Roa',   'Conductor · WGX062',         'Barranquilla', '301 111 0001'),
        ('martinez.luis',  hash_pass('mart2026'),   'conductor', 'MARTINEZ', 'Luis Martínez',       'Conductor · WGX060',         'Barranquilla', '301 111 0002'),
        ('marin.jose',     hash_pass('marin2026'),  'conductor', 'MARIN',    'José Marín',          'Conductor · TDU-499',        'Barranquilla', '301 111 0003'),
        ('mendoza.luis',   hash_pass('mend2026'),   'conductor', 'MENDOZA',  'Luis Mendoza',        'Conductor · WGX061',         'Barranquilla', '301 111 0004'),
        ('nino.ademir',    hash_pass('nino2026'),   'conductor', 'NIÑO',     'Ademir Niño',         'Conductor · WGD149',         'Barranquilla', '301 111 0005'),
        ('ayud.roa',       hash_pass('ayud2026'),   'ayudante',  'ROA',      'Carlos Pérez',        'Ayudante · Ruta ROA',        'Barranquilla', '302 222 0001'),
        ('ayud.martinez',  hash_pass('ayud2026'),   'ayudante',  'MARTINEZ', 'Jhon Torres',         'Ayudante · Ruta MARTINEZ',   'Barranquilla', '302 222 0002'),
        ('ayud.marin',     hash_pass('ayud2026'),   'ayudante',  'MARIN',    'Edwin Ospino',        'Ayudante · Ruta MARÍN',      'Barranquilla', '302 222 0003'),
        ('ayud.mendoza',   hash_pass('ayud2026'),   'ayudante',  'MENDOZA',  'Ricardo Vargas',      'Ayudante · Ruta MENDOZA',    'Barranquilla', '302 222 0004'),
        ('ayud.nino',      hash_pass('ayud2026'),   'ayudante',  'NIÑO',     'Andrés Blanco',       'Ayudante · Ruta NIÑO',       'Barranquilla', '302 222 0005'),
    ]
    executemany(conn, "INSERT INTO usuarios VALUES (?,?,?,?,?,?,?,?)", usuarios)
    commit(conn)


def _seed_conductores(conn):
    conductores = [
        ('ROA',      'ROA — Julio Armando',  'ROA',   'WGX062',  170, 77, 0, 11,  264200,  132100, 1059600, 529800, 72),
        ('MARTINEZ', 'MARTINEZ — Luis',       'MART',  'WGX060',  147, 59, 0, 11,  201000,  100500,  965200, 482600, 62),
        ('MARIN',    'MARÍN — José',          'MARÍN', 'TDU-499',  70, 18, 1,  0,   35200,   17600,  646000, 323000, 30),
        ('MENDOZA',  'MENDOZA — Luis',        'MEND.', 'WGX061',  200, 14, 0,  1, -110600,  -55300, 1188000, 594000, 85),
        ('NIÑO',     'NIÑO — Ademir',         'NIÑO',  'WGD149',   66, 11, 0,  3,   -1400,    -700,  626000, 313000, 28),
    ]
    executemany(conn, "INSERT INTO conductores VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", conductores)
    commit(conn)


def _seed_gps(conn):
    gps = [
        ('WGX062', 'Julio Armando Roa', 2, 1, 3),
        ('WGX060', 'Luis Martínez',     1, 0, 2),
        ('TDU-499','José Marín',        0, 0, 1),
        ('WGX061', 'Luis Mendoza',      4, 2, 5),
        ('WGD149', 'Ademir Niño',       1, 1, 2),
    ]
    executemany(conn, "INSERT INTO gps (placa,conductor,vel,acc,brk) VALUES (?,?,?,?,?)", gps)
    commit(conn)


def _seed_bodegas(conn):
    bodegas = [
        ('Barranquilla Centro', 42, 8), ('Barranquilla Norte', 38, 5),
        ('Barranquilla Sur', 29, 3),    ('Soledad', 15, 2),
        ('Malambo', 11, 1),             ('Bogotá D.C.', 9, 0),
        ('Montería', 7, 0),             ('Valledupar', 6, 1),
        ('Cartagena', 5, 0),
    ]
    executemany(conn, "INSERT INTO bodegas (sede,ped,nt) VALUES (?,?,?)", bodegas)
    commit(conn)


# ── Queries de negocio ────────────────────────────────────────
def get_usuario(usuario):
    conn = get_db()
    row = fetchone(conn, "SELECT * FROM usuarios WHERE usuario=?", (usuario,))
    close(conn)
    return row


def get_conductores():
    conn = get_db()
    rows = fetchall(conn, "SELECT * FROM conductores ORDER BY clave")
    close(conn)
    return rows


def get_facturas(cond_key=None, mes=None):
    conn = get_db()
    sql  = "SELECT * FROM facturas WHERE 1=1"
    params = []
    if cond_key:
        sql += f" AND cond_key={p()}"
        params.append(cond_key)
    if mes:
        if USING_PG:
            sql += " AND to_char(fec_entr,'YYYY-MM')=%s"
        else:
            sql += " AND fec_entr LIKE ?"
            mes = mes + '%'
        params.append(mes)
    sql += " ORDER BY fec_entr"
    rows = fetchall(conn, sql, params)
    close(conn)
    return rows


def get_meses_disponibles(cond_key=None):
    conn = get_db()
    if USING_PG:
        sql = "SELECT DISTINCT to_char(fec_entr,'YYYY-MM') AS mes FROM facturas WHERE fec_entr IS NOT NULL"
    else:
        sql = "SELECT DISTINCT substr(fec_entr,1,7) AS mes FROM facturas WHERE fec_entr IS NOT NULL"
    params = []
    if cond_key:
        sql += f" AND cond_key={p()}"
        params.append(cond_key)
    sql += " ORDER BY mes DESC"
    rows = fetchall(conn, sql, params)
    close(conn)
    return [r['mes'] for r in rows if r['mes']]


def get_gps():
    conn = get_db()
    rows = fetchall(conn, "SELECT * FROM gps ORDER BY placa")
    close(conn)
    return rows


def get_bodegas():
    conn = get_db()
    rows = fetchall(conn, "SELECT * FROM bodegas ORDER BY sede")
    close(conn)
    return rows


def replace_conductores(rows_data):
    conn = get_db()
    for r in rows_data:
        if USING_PG:
            execute(conn, """
                INSERT INTO conductores (clave,nombre,short,placa,pedidos,a_tiempo,h24,d2,bono_c,bono_a,meta_c,meta_a,meta_h24)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (clave) DO UPDATE SET
                  nombre=EXCLUDED.nombre, short=EXCLUDED.short, placa=EXCLUDED.placa,
                  pedidos=EXCLUDED.pedidos, a_tiempo=EXCLUDED.a_tiempo, h24=EXCLUDED.h24,
                  d2=EXCLUDED.d2, bono_c=EXCLUDED.bono_c, bono_a=EXCLUDED.bono_a,
                  meta_c=EXCLUDED.meta_c, meta_a=EXCLUDED.meta_a, meta_h24=EXCLUDED.meta_h24
            """, (
                r.get('clave',''), r.get('nombre',''), r.get('short', r.get('clave','')[:5]),
                r.get('placa',''), r.get('pedidos',0), r.get('a_tiempo',0),
                r.get('h24',0), r.get('d2',0), r.get('bono_c',0), r.get('bono_a',0),
                r.get('meta_c',0), r.get('meta_a',0), r.get('meta_h24',0),
            ))
        else:
            execute(conn, """
                INSERT INTO conductores (clave,nombre,short,placa,pedidos,a_tiempo,h24,d2,bono_c,bono_a,meta_c,meta_a,meta_h24)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(clave) DO UPDATE SET
                  nombre=excluded.nombre, short=excluded.short, placa=excluded.placa,
                  pedidos=excluded.pedidos, a_tiempo=excluded.a_tiempo, h24=excluded.h24,
                  d2=excluded.d2, bono_c=excluded.bono_c, bono_a=excluded.bono_a,
                  meta_c=excluded.meta_c, meta_a=excluded.meta_a, meta_h24=excluded.meta_h24
            """, (
                r.get('clave',''), r.get('nombre',''), r.get('short', r.get('clave','')[:5]),
                r.get('placa',''), r.get('pedidos',0), r.get('a_tiempo',0),
                r.get('h24',0), r.get('d2',0), r.get('bono_c',0), r.get('bono_a',0),
                r.get('meta_c',0), r.get('meta_a',0), r.get('meta_h24',0),
            ))
    commit(conn)
    close(conn)


def replace_facturas(cond_keys, rows_data):
    conn = get_db()
    if cond_keys:
        placeholders = ', '.join([p()] * len(cond_keys))
        execute(conn, f"DELETE FROM facturas WHERE cond_key IN ({placeholders})", cond_keys)
    for r in rows_data:
        execute(conn, f"""
            INSERT INTO facturas
              (cond_key,num,tipo,tip_desc,cliente,ciudad,dpto,placa,valor,peso,
               fec_fact,fec_promesa,fec_entr,dif_dias,dif_horas,es_mt)
            VALUES ({ph(16)})
        """, (
            r['cond_key'], r.get('num',''), r.get('tipo',''), r.get('tip_desc',''),
            r.get('cliente',''), r.get('ciudad',''), r.get('dpto',''), r.get('placa',''),
            r.get('valor'), r.get('peso'),
            r.get('fec_fact'), r.get('fec_promesa'), r.get('fec_entr'),
            r.get('dif_dias'), r.get('dif_horas'),
            1 if r.get('es_mt') else 0,
        ))
    commit(conn)
    close(conn)


def replace_gps(rows_data):
    conn = get_db()
    execute(conn, "DELETE FROM gps", ())
    for r in rows_data:
        execute(conn, f"INSERT INTO gps (placa,conductor,vel,acc,brk) VALUES ({ph(5)})",
            (r.get('placa',''), r.get('conductor',''),
             r.get('vel',0), r.get('acc',0), r.get('brk',0)))
    commit(conn)
    close(conn)


def replace_bodegas(rows_data):
    conn = get_db()
    execute(conn, "DELETE FROM bodegas", ())
    for r in rows_data:
        execute(conn, f"INSERT INTO bodegas (sede,ped,nt) VALUES ({ph(3)})",
            (r.get('sede',''), r.get('ped',0), r.get('nt',0)))
    commit(conn)
    close(conn)
