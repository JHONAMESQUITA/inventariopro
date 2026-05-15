from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from database.connection import db_query
from widgets.tarjeta import crear_tarjeta
from widgets.pagination import PaginationBar
from logging_config import logger


class AuditoriaScreen(Screen):
    PAGE_SIZE = 30

    def on_enter(self):
        self._filtro_accion = ""
        self._filtro_usuario = ""
        self.cargar_log()

    def cargar_log(self, pagina=0, page_size=None):
        self.ids.log_container.clear_widgets()
        if page_size is None:
            page_size = self.PAGE_SIZE

        where = []
        params = []
        if self._filtro_accion:
            where.append("accion LIKE ?")
            params.append(f"%{self._filtro_accion}%")
        if self._filtro_usuario:
            where.append("usuario LIKE ?")
            params.append(f"%{self._filtro_usuario}%")

        sql_where = (" WHERE " + " AND ".join(where)) if where else ""
        try:
            count = db_query(
                f"SELECT COUNT(*) FROM auditoria{sql_where}", params, fetchall=False
            )
            total = count[0] if count else 0

            offset = pagina * page_size
            rows = db_query(
                f"SELECT id, accion, detalle, fecha, usuario FROM auditoria{sql_where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [page_size, offset]
            )

            if not rows:
                lbl = Label(text="No hay registros de auditoria",
                            color=get_color_from_hex('#94A3B8'), size_hint_y=None, height=dp(60))
                self.ids.log_container.add_widget(lbl)
            else:
                for r in rows:
                    card = crear_tarjeta(dp(72), '#1A2035')
                    card.add_widget(Label(
                        text=f"[b]{r[1]}[/b]  [color=#64748B]{r[3]}[/color]",
                        markup=True, color=get_color_from_hex('#38BDF8'),
                        size_hint_y=None, height=dp(22), font_size='12sp',
                        halign='left', text_size=(Window.width * 0.82, None)
                    ))
                    card.add_widget(Label(
                        text=r[2] if len(r[2]) < 80 else r[2][:77] + "...",
                        color=get_color_from_hex('#CBD5E1'),
                        size_hint_y=None, height=dp(22), font_size='11sp',
                        halign='left', text_size=(Window.width * 0.82, None)
                    ))
                    card.add_widget(Label(
                        text=f"Usuario: {r[4] or 'sistema'}",
                        color=get_color_from_hex('#64748B'),
                        size_hint_y=None, height=dp(18), font_size='10sp',
                        halign='left', text_size=(Window.width * 0.82, None)
                    ))
                    self.ids.log_container.add_widget(card)

            if hasattr(self, 'ids') and 'pagination' in self.ids:
                self.ids.pagination.actualizar(total)

        except Exception as e:
            logger.error("Error cargando auditoria: %s", e)
            self.ids.log_container.add_widget(Label(
                text=f"Error: {e}", color=get_color_from_hex('#F87171'),
                size_hint_y=None, height=dp(40)
            ))

    def filtrar(self):
        self._filtro_accion = self.ids.filtro_accion.text.strip().upper()
        self._filtro_usuario = self.ids.filtro_usuario.text.strip().upper()
        self.cargar_log()
