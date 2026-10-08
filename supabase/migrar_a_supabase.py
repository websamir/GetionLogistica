"""
Migra los datos de la BD SQLite local a Supabase (PostgreSQL).

Requisitos (instalar una sola vez):
    pip install psycopg2-binary

Configura la URL de conexión como variable de entorno ANTES de correr:
    setx SUPABASE_DB_URL "postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres"

La URL la encuentras en Supabase → Settings → Database → Connection string → URI
"""
import os
import sys
import sqlite3
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Instala psycopg2:  pip install psycopg2-binary")
    sys.exit(1)

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────
SQLITE_PATH = Path(__file__).parent.parent / "backend" / "data" / "logistica.db"
SUPABASE_URL = os.environ.get("SUPABASE_DB_URL", "")

if not SUPABASE_URL:
    print("ERROR: define la variable de entorno SUPABASE_DB_URL")
    print('  setx SUPABASE_DB_URL "postgresql://postgres:<pass>@db.<project>.supabase.co:5432/postgres"')
    sys.exit(1)


# ─── HELPERS ────────────────────────────────────────────────────────────────
def sqlite_rows(query: str) -> list[dict]:
    with sqlite3.connect(SQLITE_PATH) as cn:
        cn.row_factory = sqlite3.Row
        return [dict(r) for r in cn.execute(query).fetchall()]


def upsert(pg, table: str, rows: list[dict], conflict_col: str):
    if not rows:
        print(f"  {table}: sin datos, omitido.")
        return
    cols = list(rows[0].keys())
    placeholders = ", ".join([f"%s"] * len(cols))
    col_list     = ", ".join(cols)
    updates      = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != conflict_col)
    sql = (
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT ({conflict_col}) DO UPDATE SET {updates}"
    )
    with pg.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, [list(r.values()) for r in rows])
    pg.commit()
    print(f"  {table}: {len(rows)} filas migradas OK")


def insert_all(pg, table: str, rows: list[dict]):
    """Borra y re-inserta (para tablas sin clave natural como facturas)."""
    if not rows:
        print(f"  {table}: sin datos, omitido.")
        return
    cols = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(cols))
    col_list     = ", ".join(cols)
    with pg.cursor() as cur:
        cur.execute(f"TRUNCATE {table} RESTART IDENTITY CASCADE")
        psycopg2.extras.execute_batch(
            cur,
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
            [list(r.values()) for r in rows],
        )
    pg.commit()
    print(f"  {table}: {len(rows)} filas migradas OK")


# ─── MIGRACIÓN ──────────────────────────────────────────────────────────────
def main():
    if not SQLITE_PATH.exists():
        print(f"ERROR: no se encontró la BD SQLite en {SQLITE_PATH}")
        sys.exit(1)

    print(f"Conectando a Supabase...")
    pg = psycopg2.connect(SUPABASE_URL, connect_timeout=15)
    print("Conexión OK\n")

    print("Migrando tablas...")

    # Orden respeta FK: conductores antes que facturas
    upsert(pg, "usuarios",    sqlite_rows("SELECT * FROM usuarios"),    "usuario")
    upsert(pg, "conductores", sqlite_rows("SELECT * FROM conductores"), "clave")

    # facturas: excluir id (autoincrement en Postgres)
    fact_rows = sqlite_rows(
        "SELECT cond_key,num,tipo,tip_desc,cliente,ciudad,dpto,placa,"
        "       valor,peso,fec_fact,fec_promesa,fec_entr,dif_dias,dif_horas,es_mt "
        "FROM facturas"
    )
    insert_all(pg, "facturas", fact_rows)

    gps_rows = sqlite_rows("SELECT placa,conductor,vel,acc,brk FROM gps")
    insert_all(pg, "gps", gps_rows)

    bod_rows = sqlite_rows("SELECT sede,ped,nt FROM bodegas")
    insert_all(pg, "bodegas", bod_rows)

    pg.close()
    print("\nMigración completada.")


if __name__ == "__main__":
    main()
