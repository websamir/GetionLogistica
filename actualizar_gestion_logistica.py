"""
Actualizador automático — Gestión Logística INVESAKK SAS
NIT 802014471-6 · Barranquilla, Colombia

Qué hace:
  1. Consulta SQL Server y genera un Excel de facturas (y opcionalmente conductores).
  2. Sube los datos directamente a la API de GestionLogistica vía JWT.
  3. Registra todo en log.txt.

Requisitos (instalar una sola vez):
    pip install pandas openpyxl pyodbc requests

Credenciales: NO van en el código. Defínalas como variables de entorno:
    setx GL_USUARIO "admin"
    setx GL_CLAVE   "admin2026"

Horario: programa este script en el Programador de tareas de Windows
con repetición cada 1 hora. El código ignora ejecuciones fuera de horario.
"""
import os
import sys
import logging
import tempfile
from datetime import datetime
from pathlib import Path

import sqlite3
import pandas as pd
import requests

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────
CARPETA  = Path(r"C:\Automatizaciones\gestion_logistica")
DB_PATH  = Path(__file__).parent / "backend" / "data" / "logistica.db"

# URL base de la app (sin barra final)
URL_BASE   = "https://getionlogistica.onrender.com"
GL_USUARIO = os.environ.get("GL_USUARIO", "admin")
GL_CLAVE   = os.environ.get("GL_CLAVE",   "admin2026")

HORA_INICIO = 7    # 7 AM inclusive
HORA_FIN    = 19   # 7 PM exclusive

# ─── LOGGING ────────────────────────────────────────────────────────────────
CARPETA.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=CARPETA / "log.txt",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger()


# ─── HELPERS ────────────────────────────────────────────────────────────────
def obtener_token() -> str:
    """Autentica en la API y devuelve el JWT."""
    r = requests.post(
        f"{URL_BASE}/api/auth/login",
        json={"usuario": GL_USUARIO, "password": GL_CLAVE},
        timeout=15,
    )
    r.raise_for_status()
    token = r.json().get("token")
    if not token:
        raise RuntimeError(f"Login fallido: {r.text}")
    log.info("Token obtenido OK (usuario: %s)", GL_USUARIO)
    return token


def leer_facturas_sqlite() -> pd.DataFrame:
    """Lee facturas desde la BD SQLite local y las devuelve en el formato
    que espera el parser de la API."""
    if not DB_PATH.exists():
        raise RuntimeError(f"No se encontró la BD: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as cn:
        cn.row_factory = sqlite3.Row
        rows = cn.execute("""
            SELECT
                c.nombre        AS nombre,
                f.placa,
                f.tipo,
                f.tip_desc      AS descripcion,
                f.num           AS numero,
                f.cliente       AS nombres,
                f.ciudad,
                f.dpto,
                f.valor         AS total_trans,
                f.peso          AS peso_total,
                f.fec_fact      AS fec_factura,
                f.fec_promesa   AS fec_promesa_entrega,
                f.fec_entr      AS fec_entrega_logistica,
                f.dif_dias      AS diferencia_fecha_dias,
                f.dif_horas     AS diferencia_fecha_horas
            FROM facturas f
            JOIN conductores c ON c.clave = f.cond_key
            ORDER BY f.fec_entr
        """).fetchall()
    if not rows:
        raise RuntimeError("La tabla facturas está vacía.")
    df = pd.DataFrame([dict(r) for r in rows])
    log.info("SQLite devolvió %d filas.", len(df))
    return df


def leer_conductores_sqlite() -> pd.DataFrame:
    """Lee conductores desde la BD SQLite local."""
    with sqlite3.connect(DB_PATH) as cn:
        df = pd.read_sql("SELECT * FROM conductores ORDER BY clave", cn)
    log.info("SQLite conductores: %d filas.", len(df))
    return df


def df_a_excel_tmp(df: pd.DataFrame, hoja: str) -> Path:
    """Guarda el DataFrame en un Excel temporal y devuelve la ruta."""
    tmp = Path(tempfile.mktemp(suffix=".xlsx", dir=CARPETA))
    with pd.ExcelWriter(tmp, engine="openpyxl",
                        datetime_format="yyyy-mm-dd") as xw:
        df.to_excel(xw, sheet_name=hoja, index=False)
    return tmp


def subir_excel(ruta: Path, tipo: str, token: str) -> dict:
    """Sube el Excel al endpoint /api/admin/upload/<tipo>."""
    headers = {"Authorization": f"Bearer {token}"}
    with open(ruta, "rb") as f:
        r = requests.post(
            f"{URL_BASE}/api/admin/upload/{tipo}",
            headers=headers,
            files={"file": (ruta.name, f,
                            "application/vnd.openxmlformats-officedocument"
                            ".spreadsheetml.sheet")},
            timeout=120,
        )
    r.raise_for_status()
    return r.json()


def cargar(tipo: str, df: pd.DataFrame, hoja: str, token: str):
    """Flujo completo: DataFrame → Excel temporal → API."""
    log.info("=== Iniciando carga: %s ===", tipo)
    tmp = df_a_excel_tmp(df, hoja)
    try:
        resultado = subir_excel(tmp, tipo, token)
        log.info("Carga %s OK: %s", tipo, resultado)
        print(f"  [{tipo}] OK — {resultado}")
    finally:
        tmp.unlink(missing_ok=True)


# ─── MAIN ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    hora = datetime.now().hour
    if not (HORA_INICIO <= hora < HORA_FIN):
        log.info("Fuera de horario (%02d:xx), sin acción.", hora)
        print(f"Fuera de horario ({hora:02d}:xx). El script corre entre {HORA_INICIO}:00 y {HORA_FIN}:00.")
        sys.exit(0)

    print(f"=== Actualizador GestionLogistica — {datetime.now():%Y-%m-%d %H:%M} ===")
    try:
        token = obtener_token()

        df_fact = leer_facturas_sqlite()
        cargar("facturas", df_fact, "Facturas", token)

        df_cond = leer_conductores_sqlite()
        cargar("conductores", df_cond, "Conductores", token)

        log.info("Actualización completada.")
        print("Actualización completada correctamente.")

    except Exception as e:
        log.exception("ERROR: %s", e)
        print(f"ERROR: {e}")
        sys.exit(1)
