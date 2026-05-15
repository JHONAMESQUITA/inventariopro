from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from database.connection import db_query
from widgets.tarjeta import crear_tarjeta
from logging_config import logger


class FiltroScreen(Screen):
    def on_enter(self):
        self.filtrar()

    def filtrar(self) -> None:
        try:
            self.ids.c_r.clear_widgets()
            bn   = self.ids.f_n.text.upper()
            bp   = self.ids.f_p.text.upper()
            tipo = self.ids.filtro_tipo.text
            if len(bn) < 2 and len(bp) < 2:
                self.ids.filtro_count.text = "Escribe al menos 2 caracteres para buscar"
                return
            sql    = "SELECT material,tipo,cantidad,nombre,fecha,sku FROM movimientos WHERE UPPER(nombre) LIKE ? AND UPPER(material) LIKE ?"
            params = [f'%{bn}%', f'%{bp}%']
            if tipo in ("ENTRADA", "SALIDA"):
                sql += " AND tipo=?"
                params.append(tipo)
            sql += " ORDER BY id DESC LIMIT 200"
            rows = db_query(sql, params)
            self.ids.filtro_count.text = f"{len(rows)} resultado(s)"
            for m, t, c, n, f, s in rows:
                color_tipo = '#10B981' if t == "ENTRADA" else '#F87171'
                card = crear_tarjeta(dp(90))
                card.add_widget(Label(text=f"[b]{m}[/b]  [color={color_tipo}]{t}[/color]",
                                      markup=True, color=get_color_from_hex('#38BDF8'),
                                      size_hint_y=None, height=dp(26), font_size='12sp',
                                      halign='left', valign='middle',
                                      text_size=(Window.width * 0.82, None)))
                card.add_widget(Label(text=f"Cant: {c} | SKU: {s or 'N/A'}",
                                      color=get_color_from_hex('#94A3B8'),
                                      size_hint_y=None, height=dp(22), font_size='11sp',
                                      halign='left', valign='middle',
                                      text_size=(Window.width * 0.82, None)))
                card.add_widget(Label(text=f"{n}  *  {f}",
                                      font_size='11sp', color=get_color_from_hex('#94A3B8'),
                                      size_hint_y=None, height=dp(22),
                                      halign='left', valign='middle',
                                      text_size=(Window.width * 0.82, None)))
                self.ids.c_r.add_widget(card)
        except Exception as e:
            logger.error("Error filtrando: %s", e)
