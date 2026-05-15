import sqlite3
from typing import Optional
from database.connection import DatabaseConnection


def init_db(db_path: str) -> None:
    conn = DatabaseConnection.get_instance(db_path).get_connection()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS movimientos (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre         TEXT,
        material       TEXT,
        sku            TEXT,
        cantidad       REAL,
        tipo           TEXT,
        fecha          TEXT,
        stock_registro REAL,
        dias           INTEGER,
        retorno        TEXT DEFAULT "N/A",
        notas          TEXT DEFAULT "",
        ubicacion      TEXT DEFAULT ""
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS limpieza (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        material TEXT,
        cantidad REAL,
        estado   TEXT,
        fecha    TEXT,
        notas    TEXT DEFAULT ""
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS alertas_stock (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        material     TEXT UNIQUE,
        stock_minimo REAL DEFAULT 5
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS ubicaciones (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS auditoria (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        accion    TEXT,
        detalle   TEXT,
        fecha     TEXT,
        usuario   TEXT DEFAULT "sistema"
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS actualizaciones_correo (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha        TEXT,
        remitente    TEXT,
        asunto       TEXT,
        archivo      TEXT,
        insertados   INTEGER,
        omitidos     INTEGER,
        errores      INTEGER
    )''')

    # Fase 0: Nuevas tablas
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        username        TEXT UNIQUE NOT NULL,
        password_hash   TEXT NOT NULL,
        rol             TEXT NOT NULL DEFAULT 'editor',
        nombre_completo TEXT NOT NULL DEFAULT '',
        email           TEXT DEFAULT '',
        ultimo_acceso   TEXT,
        creado_en       TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS categorias (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre      TEXT UNIQUE NOT NULL,
        descripcion TEXT DEFAULT '',
        color_hex   TEXT DEFAULT '#38BDF8'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS categoria_items (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria_id INTEGER NOT NULL REFERENCES categorias(id),
        nombre       TEXT NOT NULL,
        UNIQUE(categoria_id, nombre)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sync_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        dispositivo_id  TEXT NOT NULL,
        accion          TEXT NOT NULL,
        tabla           TEXT NOT NULL,
        registro_id     INTEGER,
        datos_json      TEXT,
        timestamp       TEXT NOT NULL,
        estado          TEXT DEFAULT 'pendiente'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS notificaciones (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo    TEXT NOT NULL,
        titulo  TEXT NOT NULL,
        mensaje TEXT,
        leida   INTEGER DEFAULT 0,
        fecha   TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS config_app (
        clave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    )''')

    _migrate_columns(c)
    _create_indexes(c)
    conn.commit()


def _migrate_columns(c: sqlite3.Cursor) -> None:
    for tabla, columna, definicion in [
        ("movimientos", "notas",    "TEXT DEFAULT ''"),
        ("movimientos", "ubicacion","TEXT DEFAULT ''"),
        ("movimientos", "usuario_id",      "INTEGER DEFAULT NULL"),
        ("movimientos", "categoria_id",    "INTEGER DEFAULT NULL"),
        ("movimientos", "costo_unitario",  "REAL DEFAULT 0"),
        ("movimientos", "precio_venta",    "REAL DEFAULT 0"),
        ("movimientos", "dispositivo_id",  "TEXT DEFAULT ''"),
        ("movimientos", "ultima_sincronizacion", "TEXT DEFAULT ''"),
        ("limpieza",    "notas",    "TEXT DEFAULT ''"),
    ]:
        try:
            c.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
        except sqlite3.OperationalError:
            pass


def _create_indexes(c: sqlite3.Cursor) -> None:
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_movimientos_material ON movimientos(material)",
        "CREATE INDEX IF NOT EXISTS idx_movimientos_nombre ON movimientos(nombre)",
        "CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha)",
        "CREATE INDEX IF NOT EXISTS idx_movimientos_tipo ON movimientos(tipo)",
        "CREATE INDEX IF NOT EXISTS idx_movimientos_mat_nom ON movimientos(material, nombre)",
        "CREATE INDEX IF NOT EXISTS idx_limpieza_material ON limpieza(material)",
        "CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria(fecha)",
        "CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username)",
        "CREATE INDEX IF NOT EXISTS idx_notificaciones_leida ON notificaciones(leida)",
        "CREATE INDEX IF NOT EXISTS idx_sync_log_estado ON sync_log(estado)",
    ]
    for idx in indexes:
        try:
            c.execute(idx)
        except sqlite3.OperationalError:
            pass
