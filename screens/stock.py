from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from database.connection import db_query
from widgets.tarjeta import crear_tarjeta
from services.inventario import obtener_stock_material
from logging_config import logger


class StockScreen(Screen):
    _filtro_estado = ""

    def on_enter(self):
        self.actualizar_spinner_stock()
        self.consultar()

    def actualizar_spinner_stock(self) -> None:
        try:
            mats = sorted({str(r[0]).upper() for r in db_query("SELECT DISTINCT material FROM movimientos") if r[0]})
            self.ids.stock_spinner.values = mats
        except Exception as e:
            logger.error("Error actualizando spinner stock: %s", e)

    def set_filtro_estado(self, estado: str) -> None:
        self._filtro_estado = estado
        self.consultar()

    def consultar(self, *args) -> None:
        try:
            self.ids.s_r.clear_widgets()
            f_texto = self.ids.f_s.text.upper()
            f_spin  = (self.ids.stock_spinner.text.upper()
                       if self.ids.stock_spinner.text != "BUSCAR MATERIAL" else "")
            alertas_conf = {r[0].upper(): r[1] for r in db_query("SELECT material,stock_minimo FROM alertas_stock")}
            mats = sorted({r[0] for r in db_query("SELECT DISTINCT UPPER(material) FROM movimientos") if r[0]})
            for m in mats:
                if f_spin and m != f_spin:
                    continue
                if not f_spin and f_texto and f_texto not in m:
                    continue
                fijo, disponible = obtener_stock_material(m)
                minimo = alertas_conf.get(m, 5)
                if disponible <= 0:
                    estado = "sin_stock"
                elif disponible <= minimo:
                    estado = "bajo"
                else:
                    estado = "ok"
                if self._filtro_estado and estado != self._filtro_estado:
                    continue
                color_text = {'sin_stock':'#FF0044','bajo':'#FF0044','ok':'#00D4FF'}[estado]
                etiqueta   = {'sin_stock':'SIN STOCK','bajo':'STOCK BAJO','ok':'DISPONIBLE'}[estado]
                color_card = {'sin_stock':'#0D1B2A','bajo':'#0D1B2A','ok':'#0D1B2A'}[estado]
                card = crear_tarjeta(dp(110), color_card)
                card.add_widget(Label(text=f"[b]{m}[/b]", markup=True,
                                       color=get_color_from_hex('#00D4FF'),
                                       size_hint_y=None, height=dp(28),
                                       halign='left', valign='middle',
                                       text_size=(Window.width * 0.8, None)))
                card.add_widget(Label(text=f"Total sistema: {fijo}  |  Minimo alerta: {minimo}",
                                       color=get_color_from_hex('#5A6A7A'),
                                       size_hint_y=None, height=dp(24), font_size='11sp',
                                       halign='left', valign='middle',
                                       text_size=(Window.width * 0.8, None)))
                card.add_widget(Label(
                    text=f"[b][color={color_text}] {etiqueta}: {disponible}[/color][/b]",
                    markup=True,
                    size_hint_y=None, height=dp(28), font_size='14sp',
                    halign='left', valign='middle',
                    text_size=(Window.width * 0.8, None)))
                self.ids.s_r.add_widget(card)
        except Exception as e:
            logger.error("Error consultando stock: %s", e)
