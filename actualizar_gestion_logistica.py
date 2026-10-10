"""
Actualizador automático — Gestión Logística INVESAKK SAS
NIT 802014471-6 · Barranquilla, Colombia

Qué hace:
  1. Consulta SQL Server y obtiene las facturas de logística.
  2. Sube los datos a la API de GestionLogistica vía JWT.
  3. Registra todo en log.txt.

Requisitos (instalar una sola vez):
    pip install pyodbc pandas openpyxl requests

Credenciales — definir como variables de entorno (solo una vez):
    setx GL_USUARIO  "admin"
    setx GL_CLAVE    "admin2026"
    setx SQL_SERVER  "NOMBRE_O_IP_DEL_SERVIDOR"
    setx SQL_DB      "NOMBRE_BASE_DE_DATOS"
    setx SQL_USER    "usuario_sql"        (dejar vacío si usa Windows Auth)
    setx SQL_PASS    "clave_sql"          (dejar vacío si usa Windows Auth)

Programación: agregar en el Programador de tareas de Windows
con repetición cada 1 hora entre 7:00 y 19:00.
"""
import os
import sys
import logging
import tempfile
from datetime import datetime
from pathlib import Path

import pyodbc
import pandas as pd
import requests

# ─── CONFIGURACIÓN ──────────────────────────────────────────────────────────
CARPETA = Path(r"C:\Automatizaciones\gestion_logistica")

URL_BASE   = "https://getionlogistica.onrender.com"
GL_USUARIO = os.environ.get("GL_USUARIO", "admin")
GL_CLAVE   = os.environ.get("GL_CLAVE",   "admin2026")

SQL_SERVER = os.environ.get("SQL_SERVER", "")
SQL_DB     = os.environ.get("SQL_DB",     "")
SQL_USER   = os.environ.get("SQL_USER",   "")   # vacío = Windows Auth
SQL_PASS   = os.environ.get("SQL_PASS",   "")

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


# ─── CONEXIÓN SQL SERVER ─────────────────────────────────────────────────────
def get_connection():
    if SQL_USER:
        cs = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};DATABASE={SQL_DB};"
            f"UID={SQL_USER};PWD={SQL_PASS};"
            f"TrustServerCertificate=yes;"
        )
    else:
        cs = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};DATABASE={SQL_DB};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
    return pyodbc.connect(cs, timeout=30)


QUERY = """
SELECT
    conductores_sakk.nit_trans,
    terceros.nit_real                                                        AS cedula,
    conductores_sakk.nombre,
    conductores_sakk.meta_peso,
    conductores_sakk.meta_facs,
    documentos.tipo,
    tipo_transacciones.descripcion,
    documentos.numero,
    terceros_1.nit,
    terceros_1.nombres,
    documentos.valor_total                                                   AS total_trans,
    conductores_sakk.placa,
    ISNULL(v_facturas_pesos_items.peso_total, 0)                             AS peso_total,
    v_terceros_direcciones.ciudad,
    v_terceros_direcciones.dpto,
    documentos.fecha_hora                                                    AS fec_Factura,
    documentos.fecha_hora_entrega                                            AS fec_promesa_entrega,
    doc_cumplidos_docuware.fecha_entrega                                     AS fec_entrega_logistica,
    DATEDIFF(hour, documentos.fecha_hora_entrega,
             doc_cumplidos_docuware.fecha_entrega)                           AS diferencia_fecha_horas,
    DATEDIFF(day,  documentos.fecha_hora_entrega,
             doc_cumplidos_docuware.fecha_entrega)                           AS diferencia_fecha_dias,
    documentos.bodega
FROM doc_cumplidos_docuware
INNER JOIN documentos
    ON  doc_cumplidos_docuware.Numero_Factura = documentos.numero
    AND doc_cumplidos_docuware.Tipo_Factura   = documentos.tipo
INNER JOIN conductores_sakk
    ON  doc_cumplidos_docuware.conductor = conductores_sakk.nombre
INNER JOIN terceros
    ON  conductores_sakk.nit_trans = terceros.nit
INNER JOIN v_terceros_direcciones
    ON  documentos.nit              = v_terceros_direcciones.nit
    AND documentos.codigo_direccion = v_terceros_direcciones.codigo_direccion
INNER JOIN tipo_transacciones
    ON  documentos.tipo = tipo_transacciones.tipo
INNER JOIN terceros AS terceros_1
    ON  documentos.nit = terceros_1.nit
LEFT OUTER JOIN v_facturas_pesos_items
    ON  documentos.tipo   = v_facturas_pesos_items.tipo
    AND documentos.numero = v_facturas_pesos_items.numero
WHERE (documentos.concepto IN (2, 6, 5, 16))
  AND (conductores_sakk.unidad_despachos <> '999')
  AND (doc_cumplidos_docuware.fecha_entrega >= GETDATE() - 60)
  AND (documentos.sw IN ('1', '16'))
ORDER BY conductores_sakk.unidad_despachos, conductores_sakk.nombre
"""


def leer_facturas_sqlserver() -> pd.DataFrame:
    log.info("Conectando a SQL Server: %s / %s", SQL_SERVER, SQL_DB)
    conn = get_connection()
    df = pd.read_sql(QUERY, conn)
    conn.close()
    log.info("SQL Server devolvió %d filas.", len(df))
    if df.empty:
        raise RuntimeError("La consulta no devolvió filas.")
    return df


# ─── HELPERS API ─────────────────────────────────────────────────────────────
def obtener_token() -> str:
    r = requests.post(
        f"{URL_BASE}/api/auth/login",
        json={"usuario": GL_USUARIO, "password": GL_CLAVE},
        timeout=20,
    )
    r.raise_for_status()
    token = r.json().get("token")
    if not token:
        raise RuntimeError(f"Login fallido: {r.text}")
    log.info("Token obtenido OK")
    return token


def df_a_excel_tmp(df: pd.DataFrame) -> Path:
    tmp = Path(tempfile.mktemp(suffix=".xlsx", dir=CARPETA))
    with pd.ExcelWriter(tmp, engine="openpyxl", datetime_format="yyyy-mm-dd") as xw:
        df.to_excel(xw, sheet_name="Facturas", index=False)
    return tmp


def subir_excel(ruta: Path, token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    with open(ruta, "rb") as f:
        r = requests.post(
            f"{URL_BASE}/api/admin/upload/facturas",
            headers=headers,
            files={"file": (ruta.name, f,
                            "application/vnd.openxmlformats-officedocument"
                            ".spreadsheetml.sheet")},
            timeout=180,
        )
    r.raise_for_status()
    return r.json()


# ─── MAIN ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    hora = datetime.now().hour
    if not (HORA_INICIO <= hora < HORA_FIN):
        log.info("Fuera de horario (%02d:xx), sin acción.", hora)
        print(f"Fuera de horario ({hora:02d}:xx). Corre entre {HORA_INICIO}:00 y {HORA_FIN}:00.")
        sys.exit(0)

    print(f"=== Actualizador GestionLogistica — {datetime.now():%Y-%m-%d %H:%M} ===")
    tmp = None
    try:
        df = leer_facturas_sqlserver()
        token = obtener_token()
        tmp = df_a_excel_tmp(df)
        resultado = subir_excel(tmp, token)
        log.info("Carga OK: %s", resultado)
        print(f"  OK — {resultado}")
        log.info("Actualización completada.")
        print("Actualización completada correctamente.")

    except Exception as e:
        log.exception("ERROR: %s", e)
        print(f"ERROR: {e}")
        sys.exit(1)

    finally:
        if tmp and tmp.exists():
            tmp.unlink(missing_ok=True)
