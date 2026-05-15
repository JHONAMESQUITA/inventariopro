import csv
import threading
from datetime import datetime, timedelta
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from database.connection import db_query, db_execute
from services.auditoria import log_auditoria
from services.excel_service import ruta_exportacion, generar_excel
from services.scheduler import obtener_config, guardar_config
from config import EMAIL_CONFIG, EXPORT_DIR
from logging_config import logger


class AjustesScreen(Screen):
    def on_enter(self):
        self.actualizar_spinner_alertas()
        try:
            self.ids.lbl_carpeta_export.text = f"Carpeta: {EXPORT_DIR}"
            self.ids.filtro_asunto.text    = EMAIL_CONFIG.get("asunto_filtro", "") or obtener_config("filtro_asunto", "")
            self.ids.filtro_remitente.text = EMAIL_CONFIG.get("remitente_filtro", "") or obtener_config("filtro_remitente", "")
            self.ids.backup_interval.text  = obtener_config("backup_interval_horas", "0")
        except Exception as e:
            logger.error("Error en on_enter ajustes: %s", e)

    def actualizar_spinner_alertas(self) -> None:
        try:
            mats = sorted({str(r[0]).upper() for r in db_query("SELECT DISTINCT material FROM movimientos") if r[0]})
            self.ids.alerta_material_spinner.values = mats
        except Exception as e:
            logger.error("Error actualizando spinner alertas: %s", e)

    def guardar_alerta(self) -> None:
        mat    = (self.ids.alerta_material_spinner.text
                  if self.ids.alerta_material_spinner.text != "SELECCIONAR MATERIAL" else "")
        minimo = self.ids.stock_minimo_input.text.strip()
        if not mat or not minimo:
            self.ids.info_alerta.text = "Selecciona material y escribe minimo"
            return
        try:
            db_execute(
                "INSERT INTO alertas_stock (material,stock_minimo) VALUES (?,?) "
                "ON CONFLICT(material) DO UPDATE SET stock_minimo=excluded.stock_minimo",
                (mat.upper(), float(minimo))
            )
            self.ids.info_alerta.text = f"Alerta guardada: {mat} -> min {minimo}"
            self.ids.stock_minimo_input.text = ""
        except Exception as e:
            logger.error("Error guardando alerta: %s", e)
            self.ids.info_alerta.text = f"Error: {e}"

    def guardar_filtros_correo(self) -> None:
        EMAIL_CONFIG["asunto_filtro"]    = self.ids.filtro_asunto.text.strip()
        EMAIL_CONFIG["remitente_filtro"] = self.ids.filtro_remitente.text.strip()
        guardar_config("filtro_asunto", EMAIL_CONFIG["asunto_filtro"])
        guardar_config("filtro_remitente", EMAIL_CONFIG["remitente_filtro"])
        self.ids.info_ajustes.text = "Filtros de correo guardados"

    def exportar_csv(self) -> None:
        self.ids.info_ajustes.text = "Exportando CSV..."
        threading.Thread(target=self._exportar_csv_worker, daemon=True).start()

    def _exportar_csv_worker(self) -> None:
        nombre = ruta_exportacion(f"inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        try:
            rows   = db_query("SELECT nombre,material,sku,cantidad,tipo,fecha,stock_registro,dias,retorno,notas,ubicacion FROM movimientos")
            with open(nombre, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(["Responsable","Material","SKU","Cantidad","Tipo","Fecha",
                             "Stock","Dias","Retorno","Notas","Ubicacion"])
                w.writerows(rows)
            log_auditoria("EXPORT_CSV", nombre)
            Clock.schedule_once(lambda dt, n=nombre: self._set_exportado(f"CSV guardado en:\n{n}"))
        except Exception as ex:
            logger.error("Error exportando CSV: %s", ex)
            err = str(ex)
            Clock.schedule_once(lambda dt, e=err: self._set_exportado(f"Error: {e}"))

    def exportar_excel_local(self) -> None:
        self.ids.info_ajustes.text = "Exportando Excel..."
        threading.Thread(target=self._exportar_excel_worker, daemon=True).start()

    def _exportar_excel_worker(self) -> None:
        nombre = ruta_exportacion(f"inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        try:
            generar_excel(nombre)
            log_auditoria("EXPORT_XLSX", nombre)
            Clock.schedule_once(lambda dt, n=nombre: self._set_exportado(f"Excel guardado en:\n{n}"))
        except Exception as ex:
            logger.error("Error exportando Excel: %s", ex)
            err = str(ex)
            Clock.schedule_once(lambda dt, e=err: self._set_exportado(f"Error: {e}"))

    def _set_exportado(self, texto):
        self.ids.info_ajustes.text = texto
        try:
            App.get_running_app().root.get_screen('inventario')._actualizar_dashboard()
        except Exception:
            pass

    def confirmar_purga(self) -> None:
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        pop = Popup(title="Confirmar Purga", content=content, size_hint=(0.88, 0.42))
        content.add_widget(Label(
            text="Eliminar movimientos de mas de\n[b]90 dias[/b]?\nEsta accion [b]NO[/b] se puede deshacer.",
            markup=True, halign='center'
        ))
        btn = Button(text="SI, PURGAR",
                     background_color=get_color_from_hex('#991B1B'),
                     size_hint_y=None, height=dp(45))
        btn.bind(on_release=lambda x: self._ejecutar_purga(pop))
        content.add_widget(btn)
        content.add_widget(Button(text="Cancelar", size_hint_y=None, height=dp(40),
                                   background_color=get_color_from_hex('#334155'),
                                   on_release=pop.dismiss))
        pop.open()

    def guardar_backup_config(self) -> None:
        horas = self.ids.backup_interval.text.strip()
        guardar_config("backup_interval_horas", horas)
        self.ids.info_ajustes.text = f"Backup automatico: cada {horas}h" if horas != "0" else "Backup automatico desactivado"

    def _ejecutar_purga(self, pop) -> None:
        try:
            limite = (datetime.now() - timedelta(days=90)).strftime("%d/%m/%Y")
            db_execute("DELETE FROM movimientos WHERE fecha < ?", (limite,))
            eliminados = db_query(
                "SELECT COUNT(*) FROM movimientos WHERE fecha < ?",
                (limite,), fetchall=False
            )[0] or 0
            log_auditoria("PURGA", f"{eliminados} registros eliminados")
            pop.dismiss()
            self.ids.info_ajustes.text = f"{eliminados} registros eliminados"
        except Exception as e:
            pop.dismiss()
            logger.error("Error purgando: %s", e)
            self.ids.info_ajustes.text = f"Error: {e}"
