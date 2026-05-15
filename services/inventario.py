import os
import csv
from datetime import datetime, timedelta
from database.connection import db_query, db_execute
from services.auditoria import log_auditoria
from config import EXPORT_DIR


def ruta_exportacion(nombre_archivo: str) -> str:
    try:
        os.makedirs(EXPORT_DIR, exist_ok=True)
    except Exception:
        pass
    return os.path.join(EXPORT_DIR, nombre_archivo)


def obtener_stock_material(material: str) -> tuple:
    material = material.strip().upper()
    row = db_query(
        "SELECT SUM(cantidad) FROM movimientos WHERE UPPER(material)=? AND UPPER(nombre)='INVENTARIO' AND tipo='ENTRADA'",
        (material,), fetchall=False
    )
    stock_inv = float(row[0] or 0.0)
    movs = db_query(
        "SELECT tipo, cantidad FROM movimientos WHERE UPPER(material)=? AND UPPER(nombre)!='INVENTARIO'",
        (material,)
    )
    delta = sum(float(c) if t == "ENTRADA" else -float(c) for t, c in movs)
    return stock_inv, round(stock_inv + delta, 4)


def obtener_alertas_activas() -> list:
    alertas = db_query("SELECT material, stock_minimo FROM alertas_stock")
    resultado = []
    for mat, minimo in alertas:
        _, disponible = obtener_stock_material(mat)
        if disponible <= minimo:
            resultado.append((mat, disponible, minimo))
    return resultado


def obtener_reporte_estadisticas() -> dict:
    hoy = datetime.now().strftime("%d/%m/%Y")
    hace_7_dias  = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
    hace_30_dias = (datetime.now() - timedelta(days=30)).strftime("%d/%m/%Y")

    total_movs          = int(db_query("SELECT COUNT(*) FROM movimientos", fetchall=False)[0] or 0)
    total_entradas      = int(db_query("SELECT COUNT(*) FROM movimientos WHERE tipo='ENTRADA'", fetchall=False)[0] or 0)
    total_salidas       = int(db_query("SELECT COUNT(*) FROM movimientos WHERE tipo='SALIDA'", fetchall=False)[0] or 0)
    materiales_unicos   = int(db_query("SELECT COUNT(DISTINCT material) FROM movimientos", fetchall=False)[0] or 0)
    responsables_unicos = int(db_query(
        "SELECT COUNT(DISTINCT nombre) FROM movimientos WHERE UPPER(nombre)!='INVENTARIO'",
        fetchall=False
    )[0] or 0)
    top_mat = db_query(
        "SELECT material, COUNT(*) as cnt FROM movimientos GROUP BY UPPER(material) ORDER BY cnt DESC LIMIT 1",
        fetchall=False
    )
    material_top = str(top_mat[0]) if top_mat else "N/A"

    movs_recientes = int(db_query(
        "SELECT COUNT(*) FROM movimientos WHERE fecha >= ?",
        (hace_7_dias,), fetchall=False
    )[0] or 0)
    movs_30dias = int(db_query(
        "SELECT COUNT(*) FROM movimientos WHERE fecha >= ?",
        (hace_30_dias,), fetchall=False
    )[0] or 0)
    ent_7d = int(db_query(
        "SELECT COUNT(*) FROM movimientos WHERE tipo='ENTRADA' AND fecha >= ?",
        (hace_7_dias,), fetchall=False
    )[0] or 0)
    sal_7d = int(db_query(
        "SELECT COUNT(*) FROM movimientos WHERE tipo='SALIDA' AND fecha >= ?",
        (hace_7_dias,), fetchall=False
    )[0] or 0)
    vol_entradas = float(db_query(
        "SELECT COALESCE(SUM(cantidad), 0) FROM movimientos WHERE tipo='ENTRADA'",
        fetchall=False
    )[0] or 0)
    vol_salidas = float(db_query(
        "SELECT COALESCE(SUM(cantidad), 0) FROM movimientos WHERE tipo='SALIDA'",
        fetchall=False
    )[0] or 0)
    prom_cant = float(db_query(
        "SELECT COALESCE(AVG(cantidad), 0) FROM movimientos",
        fetchall=False
    )[0] or 0)

    top5_materiales = db_query(
        "SELECT UPPER(material), COUNT(*) as cnt FROM movimientos "
        "GROUP BY UPPER(material) ORDER BY cnt DESC LIMIT 5"
    )
    top5_responsables = db_query(
        "SELECT UPPER(nombre), COUNT(*) as cnt FROM movimientos "
        "WHERE UPPER(nombre)!='INVENTARIO' GROUP BY UPPER(nombre) ORDER BY cnt DESC LIMIT 5"
    )

    todos_mats = [r[0] for r in db_query("SELECT DISTINCT UPPER(material) FROM movimientos")]
    mats_recientes = {r[0] for r in db_query(
        "SELECT DISTINCT UPPER(material) FROM movimientos WHERE fecha >= ?",
        (hace_30_dias,)
    )}
    mats_inactivos = [m for m in todos_mats if m not in mats_recientes]

    total_limpieza = int(db_query("SELECT COUNT(*) FROM limpieza", fetchall=False)[0] or 0)
    limpios = int(db_query("SELECT COUNT(*) FROM limpieza WHERE UPPER(estado)='LIMPIO'", fetchall=False)[0] or 0)
    sucios  = int(db_query("SELECT COUNT(*) FROM limpieza WHERE UPPER(estado)='SUCIO'", fetchall=False)[0] or 0)

    primer_mov = db_query("SELECT fecha FROM movimientos ORDER BY id ASC LIMIT 1", fetchall=False)
    ultimo_mov = db_query("SELECT fecha FROM movimientos ORDER BY id DESC LIMIT 1", fetchall=False)

    return {
        "total_movimientos": total_movs,
        "entradas":          total_entradas,
        "salidas":           total_salidas,
        "materiales":        materiales_unicos,
        "responsables":      responsables_unicos,
        "material_top":      material_top,
        "movs_7dias":        movs_recientes,
        "movs_30dias":       movs_30dias,
        "ent_7d":            ent_7d,
        "sal_7d":            sal_7d,
        "vol_entradas":      round(vol_entradas, 2),
        "vol_salidas":       round(vol_salidas, 2),
        "prom_cant":         round(prom_cant, 2),
        "top5_materiales":   top5_materiales,
        "top5_responsables": top5_responsables,
        "mats_inactivos":    mats_inactivos[:10],
        "total_limpieza":    total_limpieza,
        "limpios":           limpios,
        "sucios":            sucios,
        "primer_mov":        str(primer_mov[0]) if primer_mov else "N/A",
        "ultimo_mov":        str(ultimo_mov[0]) if ultimo_mov else "N/A",
    }
