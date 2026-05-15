from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from database.connection import db_query, db_execute
from widgets.tarjeta import crear_tarjeta
from logging_config import logger


class UbicacionesScreen(Screen):
    def on_enter(self):
        self.cargar_ubicaciones()

    def cargar_ubicaciones(self):
        self.ids.lista_ubicaciones.clear_widgets()
        rows = db_query("SELECT id, nombre FROM ubicaciones ORDER BY nombre")
        if not rows:
            lbl = Label(text="Sin ubicaciones", color=get_color_from_hex('#94A3B8'),
                        size_hint_y=None, height=dp(60))
            self.ids.lista_ubicaciones.add_widget(lbl)
            return
        for r in rows:
            card = crear_tarjeta(dp(56), '#1A2035')
            row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
            row.add_widget(Label(
                text=f"[b]{r[1]}[/b]",
                markup=True, color=get_color_from_hex('#38BDF8'),
                font_size='13sp', halign='left',
                text_size=(Window.width * 0.6, None), size_hint_x=0.7))
            btn = Button(text="ELIMINAR", size_hint_x=0.3,
                         font_size='11sp',
                         background_color=get_color_from_hex('#991B1B'))
            btn.bind(on_release=lambda x, uid=r[0]: self._eliminar(uid))
            row.add_widget(btn)
            card.add_widget(row)
            self.ids.lista_ubicaciones.add_widget(card)

    def mostrar_nueva(self):
        inp = TextInput(hint_text="Nombre de la ubicacion", multiline=False,
                        size_hint_y=None, height=dp(48))
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
        content.add_widget(inp)
        pop = Popup(title="NUEVA UBICACION", content=content, size_hint=(0.85, 0.32))

        def guardar(btn):
            if inp.text.strip():
                db_execute("INSERT INTO ubicaciones (nombre) VALUES (?)", (inp.text.strip().upper(),))
            pop.dismiss()
            self.cargar_ubicaciones()

        btn = Button(text="CREAR", size_hint_y=None, height=dp(48),
                     background_color=get_color_from_hex('#059669'), on_release=guardar)
        content.add_widget(btn)
        pop.open()

    def _eliminar(self, uid):
        db_execute("DELETE FROM ubicaciones WHERE id = ?", (uid,))
        self.cargar_ubicaciones()
