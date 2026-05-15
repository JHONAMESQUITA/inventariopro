import os
import sys
import tempfile
import pytest


@pytest.fixture
def db_path():
    """Crea una base de datos temporal para cada test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    from database.models import init_db
    from database.connection import DatabaseConnection
    DatabaseConnection.close_all()
    init_db(db)
    yield db
    DatabaseConnection.close_path(db)
    try:
        os.unlink(db)
    except PermissionError:
        pass


@pytest.mark.order1
class TestDatabase:

    def test_init_db(self, db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in c.fetchall()]
        required = ["movimientos", "limpieza", "alertas_stock", "ubicaciones", "auditoria", "actualizaciones_correo"]
        for t in required:
            assert t in tables, f"Falta la tabla {t}"
        conn.close()

    def test_insert_movimiento(self, db_path):
        from database.connection import db_query, db_execute
        db_execute(
            "INSERT INTO movimientos (nombre,material,sku,cantidad,tipo,fecha,stock_registro,dias,retorno) VALUES (?,?,?,?,?,?,?,?,?)",
            ("TEST", "MATERIAL TEST", "SKU001", 10.0, "ENTRADA", "01/01/2025 10:00", 10.0, 0, "N/A"),
            db_path=db_path
        )
        rows = db_query("SELECT * FROM movimientos", db_path=db_path)
        assert len(rows) == 1
        assert rows[0][1] == "TEST"
        assert rows[0][2] == "MATERIAL TEST"
        assert rows[0][4] == 10.0

    def test_insert_limpieza(self, db_path):
        from database.connection import db_query, db_execute
        db_execute(
            "INSERT INTO limpieza (material,cantidad,estado,fecha) VALUES (?,?,?,?)",
            ("MAT_TEST", 5.0, "SUCIO", "01/01/2025"),
            db_path=db_path
        )
        rows = db_query("SELECT * FROM limpieza", db_path=db_path)
        assert len(rows) == 1
        assert rows[0][1] == "MAT_TEST"

    def test_insert_auditoria(self, db_path):
        from database.connection import db_query, db_execute
        db_execute(
            "INSERT INTO auditoria (accion,detalle,fecha) VALUES (?,?,?)",
            ("TEST_ACCION", "detalle test", "01/01/2025 10:00"),
            db_path=db_path
        )
        rows = db_query("SELECT * FROM auditoria", db_path=db_path)
        assert len(rows) == 1
        assert rows[0][1] == "TEST_ACCION"

    def test_indexes_exist(self, db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        indexes = [r[0] for r in c.fetchall()]
        expected = ["idx_movimientos_material", "idx_movimientos_nombre", "idx_movimientos_fecha"]
        for idx in expected:
            assert idx in indexes, f"Falta el indice {idx}"
        conn.close()
