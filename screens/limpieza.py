from datetime import datetime
from collections import defaultdict
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from database.connection import db_query, db_execute
from widgets.tarjeta import crear_tarjeta
from logging_config import logger


class LimpiezaScreen(Screen):
    def on_enter(self):
        self.actualizar_spinner_limpieza()
        self.consultar_historial()

    def actualizar_spinner_limpieza(self) -> None:
        try:
            mats = sorted({str(r[0]).upper() for r in db_query("SELECT DISTINCT material FROM limpieza") if r[0]})
            self.ids.limpieza_spinner.values = mats
        except Exception as e:
            logger.error("Error actualizando spinner limpieza: %s", e)

    def registrar_limpieza(self, estado: str) -> None:
        mat   = (self.ids.m_n.text.strip().upper()
                 or (self.ids.limpieza_spinner.text
                     if self.ids.limpieza_spinner.text != "SELECCIONAR MATERIAL" else ""))
        cant  = self.ids.m_c.text.strip()
        notas = self.ids.m_notas.text.strip()
        if not mat or not cant:
            self.ids.info_limpieza.text = "Material y cantidad requeridos"
            return
        existe = db_query("SELECT 1 FROM movimientos WHERE UPPER(material)=? LIMIT 1", (mat,), fetchall=False)
        if not existe:
            self.ids.info_limpieza.text = f"'{mat}' no existe en movimientos"
            return
        try:
            db_execute(
                "INSERT INTO limpieza (material,cantidad,estado,fecha,notas) VALUES (?,?,?,?,?)",
                (mat, float(cant), estado, datetime.now().strftime("%d/%m/%Y %H:%M"), notas)
            )
            self.ids.m_n.text = ""
            self.ids.m_c.text = ""
            self.ids.m_notas.text = ""
            self.ids.info_limpieza.text = ""
            self.ids.limpieza_spinner.text = "SELECCIONAR MATERIAL"
            self.consultar_historial()
            self.actualizar_spinner_limpieza()
        except Exception as e:
            logger.error("Error registrando limpieza: %s", e)
            self.ids.info_limpieza.text = f"Error: {e}"

    def consultar_historial(self) -> None:
        try:
            self.ids.hist_limpieza.clear_widgets()
            busq  = self.ids.f_l.text.lower()
            rows  = db_query("SELECT material, cantidad, estado FROM limpieza")
            totales = defaultdict(lambda: {"LIMPIO": 0.0, "SUCIO": 0.0})
            for m, c, e in rows:
                totales[str(m).upper()][e] += float(c)
            for mat, v in sorted(totales.items()):
                if busq and busq not in mat.lower():
                    continue
                neto = v["SUCIO"] - v["LIMPIO"]
                if neto <= 0:
                    continue
                card = crear_tarjeta(dp(90))
                card.add_widget(Label(text=f"[b]{mat}[/b]", markup=True,
                                      color=get_color_from_hex('#00D4FF'),
                                      size_hint_y=None, height=dp(26), font_size='12sp',
                                      halign='left', valign='middle',
                                      text_size=(Window.width * 0.82, None)))
                card.add_widget(Label(text=f"Sucio: {v['SUCIO']}  |  Limpio: {v['LIMPIO']}",
                                      color=get_color_from_hex('#5A6A7A'),
                                      size_hint_y=None, height=dp(22), font_size='11sp',
                                      halign='left', valign='middle',
                                      text_size=(Window.width * 0.82, None)))
                card.add_widget(Label(
                    text=f"[color=#FF0044]Pendiente de limpiar: {max(0, neto):.2f}[/color]",
                    markup=True,
                    size_hint_y=None, height=dp(22), font_size='11sp',
                    halign='left', valign='middle',
                    text_size=(Window.width * 0.82, None)))
                self.ids.hist_limpieza.add_widget(card)
        except Exception as e:
            logger.error("Error consultando historial limpieza: %s", e)
