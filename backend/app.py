"""
Gestión Logística — INVESAKK SAS
NIT 802014471-6 · Barranquilla, Colombia
Backend Flask + SQLite
"""
import os, hashlib, uuid
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_cors import CORS
from datetime import timedelta

import database as db
import excel_parser as ep

# ── App ───────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder='../frontend',
    static_folder='static'
)
app.config['JWT_SECRET_KEY']          = 'INVESAKK-LogSecretKey-802014471'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=10)
app.config['MAX_CONTENT_LENGTH']       = 32 * 1024 * 1024  # 32 MB

CORS(app, resources={r"/api/*": {"origins": "*"}})
jwt = JWTManager(app)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Inicializar BD ────────────────────────────────────────────
db.init_db()

# ── Helpers ───────────────────────────────────────────────────
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()


def current_user():
    usuario = get_jwt_identity()
    return db.get_usuario(usuario)


def require_roles(*roles):
    u = current_user()
    if not u or u['role'] not in roles:
        return jsonify(error='Sin permisos'), 403
    return None


# ════════════════════════════════════════════════════════════════
# RUTAS FRONTEND
# ════════════════════════════════════════════════════════════════
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


# ════════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════════
@app.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json() or {}
    usuario  = str(data.get('usuario', '')).strip().lower()
    password = str(data.get('password', '')).strip()

    if not usuario or not password:
        return jsonify(error='Usuario y contraseña requeridos'), 400

    try:
        user = db.get_usuario(usuario)
    except Exception as e:
        import traceback
        return jsonify(error='DB error', detail=traceback.format_exc()), 500

    if not user or user['password'] != hash_pass(password):
        return jsonify(error='Credenciales incorrectas'), 401

    token = create_access_token(identity=usuario)
    return jsonify(
        token=token,
        user={
            'usuario':  usuario,
            'nombre':   user['nombre'],
            'cargo':    user['cargo'],
            'role':     user['role'],
            'cond_key': user['cond_key'],
            'sede':     user['sede'],
            'celular':  user['celular'],
        }
    )


@app.route('/api/auth/me')
@jwt_required()
def me():
    user = current_user()
    if not user:
        return jsonify(error='Usuario no encontrado'), 404
    return jsonify(
        usuario=get_jwt_identity(),
        nombre=user['nombre'],
        cargo=user['cargo'],
        role=user['role'],
        cond_key=user['cond_key'],
        sede=user['sede'],
        celular=user['celular'],
    )


# ════════════════════════════════════════════════════════════════
# CONDUCTORES
# ════════════════════════════════════════════════════════════════
@app.route('/api/conductores')
@jwt_required()
def get_conductores():
    return jsonify(db.get_conductores())


# ════════════════════════════════════════════════════════════════
# STATS CALCULADAS DESDE FACTURAS (por mes)
# ════════════════════════════════════════════════════════════════
@app.route('/api/stats')
@jwt_required()
def get_stats():
    mes = request.args.get('mes', '')   # YYYY-MM; '' = todos

    conn = db.get_db()

    # Esquema de bono en SQL (días → valor)
    bono_sql = """
        CASE
            WHEN es_mt = 1 OR fec_entr IS NULL THEN 0
            WHEN dif_dias <= 0  THEN  6000
            WHEN dif_dias <= 1  THEN  6000
            WHEN dif_dias <= 2  THEN  5000
            WHEN dif_dias <= 5  THEN  4000
            WHEN dif_dias <= 10 THEN  -400
            WHEN dif_dias <= 20 THEN  -800
            ELSE -2000
        END
    """

    mes_filter = "AND fec_entr LIKE ?" if mes else ""
    params = [mes + '%'] if mes else []

    rows = conn.execute(f"""
        SELECT
            cond_key,
            COUNT(*) AS total,
            SUM(CASE WHEN es_mt = 0 THEN 1 ELSE 0 END) AS pedidos,
            SUM(CASE WHEN es_mt = 1 THEN 1 ELSE 0 END) AS notas_traslado,
            SUM(CASE WHEN fec_entr IS NOT NULL AND es_mt = 0 THEN 1 ELSE 0 END) AS entregadas,
            SUM(CASE WHEN fec_entr IS NULL AND es_mt = 0 THEN 1 ELSE 0 END) AS pendientes,
            SUM(CASE WHEN fec_entr IS NOT NULL AND es_mt = 0 AND dif_dias <= 5 THEN 1 ELSE 0 END) AS a_tiempo,
            SUM(CASE WHEN fec_entr IS NOT NULL AND es_mt = 0 AND dif_dias <= 1 THEN 1 ELSE 0 END) AS h24,
            SUM(CASE WHEN fec_entr IS NOT NULL AND es_mt = 0 AND dif_dias <= 2 THEN 1 ELSE 0 END) AS d2,
            SUM({bono_sql}) AS bono_c,
            SUM({bono_sql}) / 2.0 AS bono_a
        FROM facturas
        WHERE 1=1 {mes_filter}
        GROUP BY cond_key
    """, params).fetchall()

    conn.close()

    stats = {}
    for r in rows:
        ped = r['pedidos'] or 0
        ent = r['entregadas'] or 0
        pct_tiempo = round(r['a_tiempo'] / ent * 100) if ent > 0 else 0
        stats[r['cond_key']] = {
            'cond_key':       r['cond_key'],
            'total':          r['total'],
            'pedidos':        ped,
            'notas_traslado': r['notas_traslado'],
            'entregadas':     ent,
            'pendientes':     r['pendientes'],
            'a_tiempo':       r['a_tiempo'],
            'pct_tiempo':     pct_tiempo,
            'h24':            r['h24'],
            'd2':             r['d2'],
            'bono_c':         round(r['bono_c'] or 0),
            'bono_a':         round(r['bono_a'] or 0),
        }

    return jsonify(stats)


# ════════════════════════════════════════════════════════════════
# FACTURAS
# ════════════════════════════════════════════════════════════════
@app.route('/api/facturas')
@jwt_required()
def get_facturas():
    user     = current_user()
    mes      = request.args.get('mes')       # YYYY-MM
    cond_key = request.args.get('conductor') # ROA | MARTINEZ | …

    # Conductor solo ve sus propias facturas
    if user['role'] in ('conductor', 'ayudante'):
        cond_key = user['cond_key']

    facturas = db.get_facturas(cond_key=cond_key, mes=mes)
    meses    = db.get_meses_disponibles(cond_key=cond_key if user['role'] in ('conductor','ayudante') else None)
    return jsonify(facturas=facturas, meses=meses)


# ════════════════════════════════════════════════════════════════
# GPS
# ════════════════════════════════════════════════════════════════
@app.route('/api/gps')
@jwt_required()
def get_gps():
    return jsonify(db.get_gps())


# ════════════════════════════════════════════════════════════════
# BODEGAS
# ════════════════════════════════════════════════════════════════
@app.route('/api/bodegas')
@jwt_required()
def get_bodegas():
    return jsonify(db.get_bodegas())


# ════════════════════════════════════════════════════════════════
# ADMIN — CARGA DE DATOS
# ════════════════════════════════════════════════════════════════
@app.route('/api/admin/upload/<tipo>', methods=['POST'])
@jwt_required()
def upload(tipo):
    err = require_roles('admin', 'jefe')
    if err:
        return err

    if tipo not in ('facturas', 'conductores', 'gps', 'bodegas'):
        return jsonify(error='Tipo no válido'), 400

    if 'file' not in request.files:
        return jsonify(error='No se recibió archivo'), 400

    file = request.files['file']
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        return jsonify(error='Solo se aceptan archivos .xlsx / .xls'), 400

    # Guardar temporalmente
    tmp_name = f"{uuid.uuid4()}_{file.filename}"
    tmp_path = os.path.join(UPLOAD_DIR, tmp_name)
    file.save(tmp_path)

    try:
        rows, parse_err = ep.parse_excel(tmp_path, tipo)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    if parse_err:
        return jsonify(error=parse_err), 422

    if not rows:
        return jsonify(error='El archivo no contiene datos reconocibles'), 422

    # Guardar en BD
    if tipo == 'facturas':
        affected_keys = list({r['cond_key'] for r in rows})
        db.replace_facturas(affected_keys, rows)
        return jsonify(ok=True, registros=len(rows), conductores=affected_keys)

    elif tipo == 'conductores':
        db.replace_conductores(rows)
        return jsonify(ok=True, registros=len(rows))

    elif tipo == 'gps':
        db.replace_gps(rows)
        return jsonify(ok=True, registros=len(rows))

    elif tipo == 'bodegas':
        db.replace_bodegas(rows)
        return jsonify(ok=True, registros=len(rows))


# ════════════════════════════════════════════════════════════════
# ADMIN — PREVIEW (primeras 10 filas sin guardar)
# ════════════════════════════════════════════════════════════════
@app.route('/api/admin/preview/<tipo>', methods=['POST'])
@jwt_required()
def preview(tipo):
    err = require_roles('admin', 'jefe')
    if err:
        return err

    if 'file' not in request.files:
        return jsonify(error='No se recibió archivo'), 400

    file     = request.files['file']
    tmp_name = f"{uuid.uuid4()}_{file.filename}"
    tmp_path = os.path.join(UPLOAD_DIR, tmp_name)
    file.save(tmp_path)

    try:
        rows, parse_err = ep.parse_excel(tmp_path, tipo)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    if parse_err:
        return jsonify(error=parse_err), 422

    return jsonify(total=len(rows), preview=rows[:10])


# ════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("=" * 55)
    print("  INVESAKK SAS — Gestión Logística")
    print("  NIT 802014471-6 · Barranquilla, Colombia")
    print("=" * 55)
    print("  URL: http://localhost:5000")
    print("  Admin:  admin / admin2026")
    print("  Jefe:   jefe.logistica / jefe2026")
    print("=" * 55)
    app.run(debug=True, host='0.0.0.0', port=5000)
