from datetime import datetime
from database.connection import db_execute


def log_auditoria(accion: str, detalle: str) -> None:
    try:
        db_execute(
            "INSERT INTO auditoria (accion, detalle, fecha) VALUES (?,?,?)",
            (accion, detalle, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        )
    except Exception:
        pass
