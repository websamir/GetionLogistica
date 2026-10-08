"""
Inserta facturas de ejemplo — últimos 60 días (hoy hacia atrás).
Ejecutar: python seed_facturas.py
"""
import database as db
import random, datetime

random.seed(77)

HOY      = datetime.date.today()
DESDE    = HOY - datetime.timedelta(days=60)   # 60 días atrás

CONDS = {
    'ROA':      'WGX062',
    'MARTINEZ': 'WGX060',
    'MARIN':    'TDU-499',
    'MENDOZA':  'WGX061',
    'NIÑO':     'WGD149',
}

CIUDADES = [
    ('Barranquilla', 'Atlántico'),
    ('Malambo',      'Atlántico'),
    ('Soledad',      'Atlántico'),
    ('Puerto Colombia','Atlántico'),
    ('Galapa',       'Atlántico'),
    ('Sabanalarga',  'Atlántico'),
    ('Baranoa',      'Atlántico'),
]

CLIENTES = [
    'FERRETERÍA EL PROGRESO SAS',
    'MATERIALES DE CONSTRUCCIÓN ABC',
    'INVERSIONES CARIBE SAS',
    'ALMACENES BLOCK LTDA',
    'CONSTRUCTORA DEL NORTE SAS',
    'GRUPO FERRETERO DEL CARIBE',
    'DISTRIBUIDORA EL MAESTRO',
    'CERÁMICA Y ACABADOS SAS',
    'FERROMUNDO LTDA',
    'PINTURAS DEL ATLÁNTICO SAS',
    'SUMINISTROS INDUSTRIALES DEL CARIBE',
    'CONSTRUMAX BARRANQUILLA',
    'TECHOS Y ACABADOS SAS',
    'TUBERÍA Y PVC DEL NORTE',
    'PINTUCO DISTRIBUCIONES',
]

TIPOS_REAL = [('FEPA','Factura Electrónica'), ('G1AG','Fac Convenios')]
TIPOS_NT   = [('NT20','NT Licitaciones'), ('NT10','NT Caribe Verde'), ('NT6','NT Bodemayor')]

# Pedidos diarios aproximados por conductor (promedio)
PEDIDOS_DIA = {'ROA': 2.8, 'MARTINEZ': 2.3, 'MARIN': 1.1, 'MENDOZA': 3.2, 'NIÑO': 1.0}

conn = db.get_db()
conn.execute("DELETE FROM facturas WHERE fec_fact >= ?", (DESDE.strftime('%Y-%m-%d'),))

rows = []
dia = DESDE
while dia <= HOY:
    # Sin domingos
    if dia.weekday() == 6:
        dia += datetime.timedelta(days=1)
        continue

    for cond_key, placa in CONDS.items():
        # Número de pedidos ese día (poisson-like)
        n = max(0, int(random.gauss(PEDIDOS_DIA[cond_key], 1.2)))
        for _ in range(n):
            # 28% son notas de traslado
            es_mt = random.random() < 0.28
            if es_mt:
                tipo, tipdesc = random.choice(TIPOS_NT)
            else:
                tipo, tipdesc = random.choice(TIPOS_REAL)

            ciudad, dpto = random.choice(CIUDADES)
            cliente      = random.choice(CLIENTES)
            valor        = random.randint(80, 2500) * 1000
            peso         = round(random.uniform(30, 1200), 1)
            fec_fact     = dia
            fec_prom     = fec_fact + datetime.timedelta(days=random.randint(0, 2))

            if es_mt:
                dif_dias = None; fec_entr = None; dif_horas = None
            else:
                # Pedidos recientes (últimos 5 días hábiles): mayor % pendiente
                dias_desde_hoy = (HOY - dia).days
                prob_entrega = 0.90 if dias_desde_hoy > 7 else 0.45
                if random.random() < prob_entrega:
                    dif_dias  = random.choice([0,0,1,1,1,2,2,3,4,5,6,8,10,15,22,30])
                    dif_horas = dif_dias * 24 + random.randint(0, 23)
                    fec_entr  = fec_prom + datetime.timedelta(days=dif_dias)
                    # No entregar en el futuro
                    if fec_entr > HOY:
                        fec_entr = None; dif_dias = None; dif_horas = None
                else:
                    dif_dias = None; fec_entr = None; dif_horas = None

            num = f"FAC-{random.randint(10000,99999)}"

            rows.append((
                cond_key, num, tipo, tipdesc, cliente, ciudad, dpto, placa,
                valor, peso,
                fec_fact.strftime('%Y-%m-%d'),
                fec_prom.strftime('%Y-%m-%d'),
                fec_entr.strftime('%Y-%m-%d') if fec_entr else None,
                dif_dias, dif_horas,
                1 if es_mt else 0,
            ))

    dia += datetime.timedelta(days=1)

conn.executemany("""
    INSERT INTO facturas
      (cond_key,num,tipo,tip_desc,cliente,ciudad,dpto,placa,valor,peso,
       fec_fact,fec_promesa,fec_entr,dif_dias,dif_horas,es_mt)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", rows)
conn.commit()
conn.close()

# Resumen
print(f"Período: {DESDE} → {HOY} ({(HOY-DESDE).days} días)")
print(f"Total facturas insertadas: {len(rows)}\n")

meses = {}
for r in rows:
    m = r[10][:7]
    meses.setdefault(m, {'total':0,'ent':0,'pend':0,'nt':0})
    meses[m]['total'] += 1
    if r[15]: meses[m]['nt'] += 1
    elif r[12]: meses[m]['ent'] += 1
    else: meses[m]['pend'] += 1

for m in sorted(meses):
    d = meses[m]
    print(f"  {m}: {d['total']:4d} total | {d['ent']:3d} entregadas | {d['pend']:3d} pendientes | {d['nt']:3d} NT")

print()
for k in CONDS:
    r = [x for x in rows if x[0]==k]
    print(f"  {k:10s}: {len(r):4d} facturas")
