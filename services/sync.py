import json
import uuid
from datetime import datetime
from database.connection import db_query, db_execute
from logging_config import logger


def obtener_dispositivo_id() -> str:
    row = db_query("SELECT valor FROM config_app WHERE clave = 'dispositivo_id'", fetchall=False)
    if row:
        return row[0]
    new_id = uuid.uuid4().hex[:12].upper()
    db_execute("INSERT INTO config_app (clave, valor) VALUES ('dispositivo_id', ?) ON CONFLICT(clave) DO UPDATE SET valor = ?",
               (new_id, new_id))
    return new_id


def obtener_ultima_sincronizacion() -> str:
    row = db_query("SELECT valor FROM config_app WHERE clave = 'ultima_sync'", fetchall=False)
    return row[0] if row else ""


def guardar_ultima_sincronizacion(fecha: str) -> None:
    db_execute("INSERT INTO config_app (clave, valor) VALUES ('ultima_sync', ?) ON CONFLICT(clave) DO UPDATE SET valor = ?",
               (fecha, fecha))


def exportar_cambios() -> dict:
    ultima = obtener_ultima_sincronizacion()
    device_id = obtener_dispositivo_id()
    cambios = {
        "dispositivo": device_id,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "movimientos": [],
    }
    if ultima:
        rows = db_query(
            "SELECT id, nombre, material, sku, cantidad, tipo, fecha, stock_registro, dias, retorno, notas, ubicacion FROM movimientos WHERE id > (SELECT COALESCE(MAX(registro_id), 0) FROM sync_log WHERE tabla='movimientos' AND dispositivo_id != ?)",
            (device_id,)
        )
    else:
        rows = db_query(
            "SELECT id, nombre, material, sku, cantidad, tipo, fecha, stock_registro, dias, retorno, notas, ubicacion FROM movimientos ORDER BY id DESC LIMIT 500"
        )
    for r in rows:
        cambios["movimientos"].append({
            "id": r[0], "nombre": r[1], "material": r[2], "sku": r[3],
            "cantidad": r[4], "tipo": r[5], "fecha": r[6],
            "stock_registro": r[7], "dias": r[8], "retorno": r[9],
            "notas": r[10], "ubicacion": r[11]
        })
    return cambios


def importar_cambios(datos: dict) -> dict:
    if not datos or "movimientos" not in datos:
        return {"importados": 0, "omitidos": 0}

    device_origen = datos.get("dispositivo", "")
    device_local = obtener_dispositivo_id()
    if device_origen == device_local:
        return {"importados": 0, "omitidos": len(datos["movimientos"]), "motivo": "mismo dispositivo"}

    importados = 0
    omitidos = 0
    for mov in datos["movimientos"]:
        try:
            existe = db_query(
                "SELECT id FROM movimientos WHERE nombre=? AND material=? AND sku=? AND cantidad=? AND tipo=? AND fecha=?",
                (mov["nombre"], mov["material"], mov["sku"], mov["cantidad"], mov["tipo"], mov["fecha"]),
                fetchall=False
            )
            if existe:
                omitidos += 1
                continue

            from services.inventario import obtener_stock_material
            _, stock_actual = obtener_stock_material(mov["material"])
            nuevo_stock = round(stock_actual + (mov["cantidad"] if mov["tipo"] == "ENTRADA" else -mov["cantidad"]), 4)

            db_execute(
                "INSERT INTO movimientos (nombre, material, sku, cantidad, tipo, fecha, stock_registro, dias, retorno, notas, ubicacion, dispositivo_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (mov["nombre"], mov["material"], mov["sku"], mov["cantidad"], mov["tipo"], mov["fecha"],
                 nuevo_stock, mov["dias"], mov["retorno"], mov["notas"], mov["ubicacion"], device_origen)
            )
            importados += 1
        except Exception as e:
            logger.error("Error importando sync: %s", e)
            omitidos += 1

    if importados > 0:
        guardar_ultima_sincronizacion(datos.get("timestamp", ""))
        log_sync(device_origen, importados)

    return {"importados": importados, "omitidos": omitidos}


def log_sync(dispositivo: str, insertados: int) -> None:
    try:
        from services.auditoria import log_auditoria
        log_auditoria("SYNC", f"Desde {dispositivo}: +{insertados}")
    except Exception:
        pass
