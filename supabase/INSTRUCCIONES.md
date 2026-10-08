# Migración a Supabase — GestionLogistica INVESAKK SAS

## Pasos

### 1. Crear el schema en Supabase
1. Ve a https://supabase.com → tu proyecto → **SQL Editor**
2. Abre `schema.sql` y pega todo el contenido
3. Clic en **Run**

### 2. Obtener la URL de conexión
En Supabase → **Settings** → **Database** → **Connection string** → pestaña **URI**

Copia la URL. Tiene este formato:
```
postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

### 3. Configurar la variable de entorno
```bat
setx SUPABASE_DB_URL "postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres"
```
Cierra y abre la terminal para que tome efecto.

### 4. Instalar dependencias
```bat
pip install psycopg2-binary
```

### 5. Ejecutar la migración
```bat
cd D:\Users\lgamarra\Desktop\hub\GestionLogistica\supabase
python migrar_a_supabase.py
```

Salida esperada:
```
Conectando a Supabase...
Conexión OK

Migrando tablas...
  usuarios: 13 filas migradas OK
  conductores: 5 filas migradas OK
  facturas: 484 filas migradas OK
  gps: 5 filas migradas OK
  bodegas: 9 filas migradas OK

Migración completada.
```

### 6. Conectar el backend Flask a Supabase (producción)
Agrega la variable de entorno al servidor donde corra Flask:
```
setx SUPABASE_DB_URL "postgresql://..."
```
El backend detecta automáticamente la variable y usa PostgreSQL en lugar de SQLite.

---

## Estructura de archivos
```
supabase/
  schema.sql            ← DDL para ejecutar en Supabase SQL Editor
  migrar_a_supabase.py  ← Script de migración SQLite → Supabase
  INSTRUCCIONES.md      ← Este archivo
```
