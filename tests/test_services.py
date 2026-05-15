import os
import sys
import tempfile
import pytest


@pytest.fixture
def db_path():
    """Crea BD temporal y la configura como DB_PATH."""
    import config
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    config.DB_PATH = db
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


def setup_movimiento(nombre, material, sku, cantidad, tipo, fecha=None, db_path=None):
    from database.connection import db_execute
    if fecha is None:
        fecha = __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M")
    db_execute(
        "INSERT INTO movimientos (nombre,material,sku,cantidad,tipo,fecha,stock_registro,dias,retorno) VALUES (?,?,?,?,?,?,?,?,?)",
        (nombre, material, sku, cantidad, tipo, fecha, cantidad, 0, "N/A"),
        db_path=db_path
    )


class TestObtenerStock:
    def test_stock_inicial_cero(self, db_path):
        from services.inventario import obtener_stock_material
        total, disponible = obtener_stock_material("MATERIAL_TEST")
        assert total == 0.0
        assert disponible == 0.0

    def test_stock_despues_entrada(self, db_path):
        from services.inventario import obtener_stock_material
        setup_movimiento("INVENTARIO", "MATERIAL_A", "SKU01", 10.0, "ENTRADA", db_path=db_path)
        total, disponible = obtener_stock_material("MATERIAL_A")
        assert total == 10.0
        assert disponible == 10.0

    def test_stock_con_prestamo(self, db_path):
        from services.inventario import obtener_stock_material
        setup_movimiento("INVENTARIO", "MATERIAL_B", "SKU02", 10.0, "ENTRADA", db_path=db_path)
        setup_movimiento("JUAN", "MATERIAL_B", "SKU02", 3.0, "SALIDA", db_path=db_path)
        total, disponible = obtener_stock_material("MATERIAL_B")
        assert total == 10.0
        assert disponible == 7.0


class TestObtenerEquiposEnPrestamo:
    def test_sin_prestamos(self, db_path):
        from services.alertas import obtener_equipos_en_prestamo
        resultado = obtener_equipos_en_prestamo()
        assert resultado == []

    def test_con_prestamo_simple(self, db_path):
        from services.alertas import obtener_equipos_en_prestamo
        setup_movimiento("JUAN", "MATERIAL_C", "SKU03", 5.0, "SALIDA", db_path=db_path)
        resultado = obtener_equipos_en_prestamo()
        assert len(resultado) == 1
        assert resultado[0]["responsable"] == "JUAN"
        assert resultado[0]["material"] == "MATERIAL_C"
        assert resultado[0]["cantidad"] == 5.0

    def test_con_retorno(self, db_path):
        from services.alertas import obtener_equipos_en_prestamo
        setup_movimiento("PEDRO", "MATERIAL_D", "SKU04", 10.0, "SALIDA", db_path=db_path)
        setup_movimiento("PEDRO", "MATERIAL_D", "SKU04", 10.0, "ENTRADA", db_path=db_path)
        resultado = obtener_equipos_en_prestamo()
        assert len(resultado) == 0


class TestAlertasActivas:
    def test_sin_alertas(self, db_path):
        from services.inventario import obtener_alertas_activas
        assert obtener_alertas_activas() == []

    def test_con_stock_bajo(self, db_path):
        from services.inventario import obtener_alertas_activas
        setup_movimiento("INVENTARIO", "MATERIAL_E", "SKU05", 3.0, "ENTRADA", db_path=db_path)
        from database.connection import db_execute
        db_execute(
            "INSERT INTO alertas_stock (material,stock_minimo) VALUES (?,?)",
            ("MATERIAL_E", 5.0),
            db_path=db_path
        )
        alertas = obtener_alertas_activas()
        assert len(alertas) == 1
        assert alertas[0][0] == "MATERIAL_E"
        assert alertas[0][1] == 3.0


class TestReporteEstadisticas:
    def test_vacio(self, db_path):
        from services.inventario import obtener_reporte_estadisticas
        stats = obtener_reporte_estadisticas()
        assert stats["total_movimientos"] == 0
        assert stats["materiales"] == 0

    def test_con_datos(self, db_path):
        from services.inventario import obtener_reporte_estadisticas
        setup_movimiento("INVENTARIO", "MATERIAL_F", "SKU06", 10.0, "ENTRADA", db_path=db_path)
        setup_movimiento("MARIA", "MATERIAL_F", "SKU06", 3.0, "SALIDA", db_path=db_path)
        stats = obtener_reporte_estadisticas()
        assert stats["total_movimientos"] == 2
        assert stats["entradas"] == 1
        assert stats["salidas"] == 1
        assert stats["materiales"] == 1
        assert stats["responsables"] == 1
