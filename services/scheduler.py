import threading
from datetime import datetime, timedelta
from kivy.clock import Clock
from database.connection import db_query, db_execute
from services.excel_service import generar_excel, ruta_exportacion
from services.auditoria import log_auditoria
from logging_config import logger


def obtener_config(clave, default=""):
    row = db_query("SELECT valor FROM config_app WHERE clave = ?", (clave,), fetchall=False)
    return row[0] if row else default


def guardar_config(clave, valor):
    db_execute("INSERT INTO config_app (clave, valor) VALUES (?,?) ON CONFLICT(clave) DO UPDATE SET valor = ?",
               (clave, valor, valor))


class ProgramadorTareas:
    def __init__(self, app):
        self.app = app
        self._backup_interval = None

    def iniciar(self):
        self._programar_backup()
        self._programar_purga()
        self._programar_resumen_diario()

    def _programar_backup(self):
        intervalo = obtener_config("backup_interval_horas", "0")
        try:
            horas = int(intervalo)
        except ValueError:
            horas = 0
        if horas <= 0:
            return
        self._backup_interval = Clock.schedule_interval(
            lambda dt: self._ejecutar_backup(), horas * 3600
        )
        logger.info("Backup automatico cada %d horas", horas)

    def _ejecutar_backup(self):
        try:
            nombre = ruta_exportacion(
                f"backup_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            generar_excel(nombre)
            log_auditoria("BACKUP_AUTO", nombre)
        except Exception as e:
            logger.error("Error en backup automatico: %s", e)

    def _programar_purga(self):
        dias_str = obtener_config("purga_automatica_dias", "0")
        try:
            dias = int(dias_str)
        except ValueError:
            dias = 0
        if dias <= 0:
            return
        Clock.schedule_interval(lambda dt: self._ejecutar_purga(dias), 86400)

    def _ejecutar_purga(self, dias):
        try:
            limite = (datetime.now() - timedelta(days=dias)).strftime("%d/%m/%Y")
            db_execute("DELETE FROM movimientos WHERE fecha < ?", (limite,))
            log_auditoria("PURGA_AUTO", f"Registros anteriores a {limite}")
        except Exception as e:
            logger.error("Error en purga automatica: %s", e)

    def _programar_resumen_diario(self):
        hora_str = obtener_config("resumen_diario_hora", "")
        if not hora_str:
            return
        try:
            h, m = hora_str.split(":")
            ahora = datetime.now()
            objetivo = ahora.replace(hour=int(h), minute=int(m), second=0)
            if objetivo <= ahora:
                objetivo += timedelta(days=1)
            segundos = (objetivo - ahora).total_seconds()
            Clock.schedule_once(lambda dt: self._enviar_resumen(), segundos)
            Clock.schedule_interval(lambda dt: self._enviar_resumen(), 86400)
        except Exception as e:
            logger.error("Error programando resumen: %s", e)

    def _enviar_resumen(self):
        try:
            from services.correo import enviar_reporte_por_correo
            exito, msg = enviar_reporte_por_correo()
            if exito:
                log_auditoria("RESUMEN_DIARIO", "Enviado automaticamente")
        except Exception as e:
            logger.error("Error enviando resumen diario: %s", e)
