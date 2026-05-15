from datetime import datetime, timedelta
from database.connection import db_query, db_execute
from services.inventario import obtener_stock_material
from services.auditoria import log_auditoria


def validar_movimiento(responsable: str, material: str, cantidad_str: str) -> tuple:
    resp = (responsable or "").strip().upper()
    mat  = (material or "").strip().upper()
    cant_str = (cantidad_str or "").strip().replace(",", ".")

    if not resp:
        return False, "El responsable es obligatorio.", 0.0
    if len(resp) < 2:
        return False, "El nombre del responsable es demasiado corto.", 0.0
    if not mat:
        return False, "El equipo/material es obligatorio.", 0.0
    if len(mat) < 2:
        return False, "El nombre del equipo es demasiado corto.", 0.0
    if not cant_str:
        return False, "La cantidad es obligatoria.", 0.0
    try:
        cant = float(cant_str)
    except ValueError:
        return False, f"Cantidad invalida: '{cant_str}'. Usa numeros (ej. 2 o 1.5).", 0.0
    if cant <= 0:
        return False, "La cantidad debe ser mayor a 0.", 0.0
    if cant > 9999:
        return False, "Cantidad fuera de rango maximo (9999).", 0.0
    return True, "OK", round(cant, 4)


def obtener_equipos_en_prestamo() -> list:
    rows = db_query(
        "SELECT nombre, material, sku, cantidad, tipo, fecha, dias, notas "
        "FROM movimientos WHERE UPPER(nombre) != 'INVENTARIO' ORDER BY id ASC"
    )
    prestamos = {}
    for n, m, s, c, t, f, d, notas in rows:
        key = f"{str(n).upper()}|{str(m).upper()}"
        if t == "SALIDA":
            if key not in prestamos:
                prestamos[key] = {
                    "responsable":    str(n).upper(),
                    "material":       str(m).upper(),
                    "sku":            str(s or ""),
                    "cantidad":       float(c),
                    "fecha_salida":   str(f),
                    "dias_acordados": int(d or 0),
                    "notas":          str(notas or ""),
                }
            else:
                prestamos[key]["cantidad"] += float(c)
        elif t == "ENTRADA" and key in prestamos:
            prestamos[key]["cantidad"] -= float(c)
            if prestamos[key]["cantidad"] <= 0:
                del prestamos[key]

    resultado = []
    ahora = datetime.now()
    for item in prestamos.values():
        if item["cantidad"] <= 0:
            continue
        try:
            fecha_dt = datetime.strptime(item["fecha_salida"][:16], "%d/%m/%Y %H:%M")
            dias_fuera = (ahora - fecha_dt).days
        except Exception:
            dias_fuera = 0

        dias_acordados = item["dias_acordados"]
        if dias_acordados > 0 and dias_fuera > dias_acordados:
            estado = "VENCIDO"
        elif dias_acordados > 0 and dias_fuera >= dias_acordados - 1:
            estado = "POR_VENCER"
        else:
            estado = "EN_TIEMPO"

        resultado.append({**item, "dias_fuera": dias_fuera, "estado": estado})

    orden = {"VENCIDO": 0, "POR_VENCER": 1, "EN_TIEMPO": 2}
    resultado.sort(key=lambda x: (orden[x["estado"]], -x["dias_fuera"]))
    return resultado


def obtener_vencimientos(dias_alerta: int = 1) -> dict:
    prestamos = obtener_equipos_en_prestamo()
    vencidos    = [p for p in prestamos if p["estado"] == "VENCIDO"]
    por_vencer  = [p for p in prestamos if p["estado"] == "POR_VENCER"]
    return {"vencidos": vencidos, "por_vencer": por_vencer}


def consultar_disponibilidad(material: str) -> dict:
    material = material.strip().upper()
    _, stock_disponible = obtener_stock_material(material)
    prestamos_equipo = [
        p for p in obtener_equipos_en_prestamo()
        if p["material"] == material
    ]
    total_fuera = sum(p["cantidad"] for p in prestamos_equipo)
    return {
        "material":          material,
        "stock_total":       stock_disponible + total_fuera,
        "stock_disponible":  round(stock_disponible, 4),
        "total_en_prestamo": round(total_fuera, 4),
        "disponible":        stock_disponible > 0,
        "prestamos":         prestamos_equipo,
    }


def limpiar_duplicados() -> int:
    conn = DatabaseConnection.get_instance(DB_PATH).get_connection()
    try:
        c = conn.cursor()
        c.execute("""
            DELETE FROM movimientos
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM movimientos
                GROUP BY nombre, material, sku, cantidad, tipo, fecha
            )
        """)
        eliminados = c.rowcount
        conn.commit()
        if eliminados:
            log_auditoria("LIMPIAR_DUPLICADOS", f"{eliminados} duplicados eliminados")
        return eliminados
    except Exception:
        return 0


def generar_resumen_diario() -> str:
    hoy = datetime.now().strftime("%d/%m/%Y")
    movs_hoy = int(db_query(
        "SELECT COUNT(*) FROM movimientos WHERE fecha LIKE ? || '%'",
        (hoy,), fetchall=False
    )[0] or 0)
    ent_hoy = int(db_query(
        "SELECT COUNT(*) FROM movimientos WHERE tipo='ENTRADA' AND fecha LIKE ? || '%'",
        (hoy,), fetchall=False
    )[0] or 0)
    sal_hoy = int(db_query(
        "SELECT COUNT(*) FROM movimientos WHERE tipo='SALIDA' AND fecha LIKE ? || '%'",
        (hoy,), fetchall=False
    )[0] or 0)

    prestamos = obtener_equipos_en_prestamo()
    vencidos   = [p for p in prestamos if p["estado"] == "VENCIDO"]
    por_vencer = [p for p in prestamos if p["estado"] == "POR_VENCER"]
    alertas    = obtener_alertas_activas()

    from config import VERSION_ACTUAL
    lineas = [
        f"=== RESUMEN DIARIO - {hoy} ===",
        "",
        "ACTIVIDAD HOY:",
        f"  * Movimientos totales : {movs_hoy}",
        f"  * Salidas (alquileres): {sal_hoy}",
        f"  * Retornos            : {ent_hoy}",
        "",
        "ESTADO DE PRESTAMOS:",
        f"  * Equipos en prestamo : {len(prestamos)}",
        f"  * Vencidos            : {len(vencidos)}",
        f"  * Proximos a vencer   : {len(por_vencer)}",
        "",
    ]
    if vencidos:
        lineas.append("VENCIDOS (requieren atencion):")
        for p in vencidos:
            lineas.append(
                f"  ! {p['material']} - {p['responsable']} "
                f"({p['dias_fuera']} dias fuera, acordado: {p['dias_acordados']})"
            )
        lineas.append("")
    if alertas:
        lineas.append("ALERTAS DE STOCK BAJO:")
        for mat, disp, minimo in alertas:
            lineas.append(f"  ! {mat}: {disp} disponibles (minimo: {minimo})")
        lineas.append("")
    lineas.append(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    lineas.append(f"- INVENTARIO PRO v{VERSION_ACTUAL}")
    return "\n".join(lineas)


