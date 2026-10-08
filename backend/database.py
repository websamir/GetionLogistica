"""
Base de datos SQLite — Gestión Logística INVESAKK SAS
NIT 802014471-6 · Barranquilla, Colombia
"""
import sqlite3, os, hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'logistica.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    # ── Tablas ────────────────────────────────────────────────
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

    # ── Datos iniciales (solo si las tablas están vacías) ─────
    if not c.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
        _seed_usuarios(c)

    if not c.execute("SELECT 1 FROM conductores LIMIT 1").fetchone():
        _seed_conductores(c)

    if not c.execute("SELECT 1 FROM gps LIMIT 1").fetchone():
        _seed_gps(c)

    if not c.execute("SELECT 1 FROM bodegas LIMIT 1").fetchone():
        _seed_bodegas(c)

    conn.commit()
    conn.close()


def _seed_usuarios(c):
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
    c.executemany(
        "INSERT INTO usuarios VALUES (?,?,?,?,?,?,?,?)", usuarios
    )


def _seed_conductores(c):
    conductores = [
        ('ROA',      'ROA — Julio Armando',  'ROA',   'WGX062', 170, 77,  0, 11,  264200,  132100, 1059600, 529800, 72),
        ('MARTINEZ', 'MARTINEZ — Luis',       'MART',  'WGX060', 147, 59,  0, 11,  201000,  100500,  965200, 482600, 62),
        ('MARIN',    'MARÍN — José',          'MARÍN', 'TDU-499',  70, 18,  1,  0,   35200,   17600,  646000, 323000, 30),
        ('MENDOZA',  'MENDOZA — Luis',        'MEND.', 'WGX061', 200, 14,  0,  1, -110600,  -55300, 1188000, 594000, 85),
        ('NIÑO',     'NIÑO — Ademir',         'NIÑO',  'WGD149',  66, 11,  0,  3,   -1400,    -700,  626000, 313000, 28),
    ]
    c.executemany(
        "INSERT INTO conductores VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", conductores
    )


def _seed_gps(c):
    gps = [
        ('WGX062', 'Julio Armando Roa', 2, 1, 3),
        ('WGX060', 'Luis Martínez',     1, 0, 2),
        ('TDU-499','José Marín',        0, 0, 1),
        ('WGX061', 'Luis Mendoza',      4, 2, 5),
        ('WGD149', 'Ademir Niño',       1, 1, 2),
    ]
    c.executemany("INSERT INTO gps (placa,conductor,vel,acc,brk) VALUES (?,?,?,?,?)", gps)


def _seed_bodegas(c):
    bodegas = [
        ('Barranquilla Centro', 42, 8),
        ('Barranquilla Norte',  38, 5),
        ('Barranquilla Sur',    29, 3),
        ('Soledad',             15, 2),
        ('Malambo',             11, 1),
        ('Bogotá D.C.',          9, 0),
        ('Montería',             7, 0),
        ('Valledupar',           6, 1),
        ('Cartagena',            5, 0),
    ]
    c.executemany("INSERT INTO bodegas (sede,ped,nt) VALUES (?,?,?)", bodegas)


# ── Queries de negocio ─────────────────────────────────────────

def get_usuario(usuario):
    conn = get_db()
    row = conn.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_conductores():
    conn = get_db()
    rows = conn.execute("SELECT * FROM conductores ORDER BY clave").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_facturas(cond_key=None, mes=None):
    conn = get_db()
    sql  = "SELECT * FROM facturas WHERE 1=1"
    params = []
    if cond_key:
        sql += " AND cond_key=?"
        params.append(cond_key)
    if mes:                         # mes = YYYY-MM  → filtra por fecha de entrega
        sql += " AND fec_entr LIKE ?"
        params.append(mes + '%')
    sql += " ORDER BY fec_entr"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_meses_disponibles(cond_key=None):
    conn = get_db()
    sql = "SELECT DISTINCT substr(fec_entr,1,7) AS mes FROM facturas WHERE fec_entr IS NOT NULL"
    params = []
    if cond_key:
        sql += " AND cond_key=?"
        params.append(cond_key)
    sql += " ORDER BY mes DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [r['mes'] for r in rows if r['mes']]


def get_gps():
    conn = get_db()
    rows = conn.execute("SELECT * FROM gps ORDER BY placa").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bodegas():
    conn = get_db()
    rows = conn.execute("SELECT * FROM bodegas ORDER BY sede").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def replace_conductores(rows_data):
    conn = get_db()
    for r in rows_data:
        conn.execute("""
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
    conn.commit()
    conn.close()


def replace_facturas(cond_keys, rows_data):
    """Reemplaza facturas de los conductores afectados."""
    conn = get_db()
    if cond_keys:
        placeholders = ','.join('?' * len(cond_keys))
        conn.execute(f"DELETE FROM facturas WHERE cond_key IN ({placeholders})", cond_keys)
    for r in rows_data:
        conn.execute("""
            INSERT INTO facturas
              (cond_key,num,tipo,tip_desc,cliente,ciudad,dpto,placa,valor,peso,
               fec_fact,fec_promesa,fec_entr,dif_dias,dif_horas,es_mt)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            r['cond_key'], r.get('num',''), r.get('tipo',''), r.get('tip_desc',''),
            r.get('cliente',''), r.get('ciudad',''), r.get('dpto',''), r.get('placa',''),
            r.get('valor'), r.get('peso'),
            r.get('fec_fact'), r.get('fec_promesa'), r.get('fec_entr'),
            r.get('dif_dias'), r.get('dif_horas'),
            1 if r.get('es_mt') else 0,
        ))
    conn.commit()
    conn.close()


def replace_gps(rows_data):
    conn = get_db()
    conn.execute("DELETE FROM gps")
    for r in rows_data:
        conn.execute(
            "INSERT INTO gps (placa,conductor,vel,acc,brk) VALUES (?,?,?,?,?)",
            (r.get('placa',''), r.get('conductor',''),
             r.get('vel',0), r.get('acc',0), r.get('brk',0))
        )
    conn.commit()
    conn.close()


def replace_bodegas(rows_data):
    conn = get_db()
    conn.execute("DELETE FROM bodegas")
    for r in rows_data:
        conn.execute(
            "INSERT INTO bodegas (sede,ped,nt) VALUES (?,?,?)",
            (r.get('sede',''), r.get('ped',0), r.get('nt',0))
        )
    conn.commit()
    conn.close()
