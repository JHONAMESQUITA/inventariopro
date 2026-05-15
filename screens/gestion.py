from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from database.connection import db_query, db_execute
from services.auditoria import log_auditoria
from services.inventario import obtener_stock_material
from widgets.tarjeta import crear_tarjeta
from widgets.toast import Toast
from logging_config import logger


class GestionScreen(Screen):
    def on_enter(self):
        self._modo = "materiales"
        self.cargar()

    def cargar(self, filtro=""):
        self.ids.lista_gestion.clear_widgets()
        filtro = filtro.upper().strip()

        if self._modo == "materiales":
            self.ids.titulo_seccion.text = "MATERIALES"
            rows = db_query(
                "SELECT DISTINCT UPPER(material) FROM movimientos ORDER BY material"
            )
            for (mat,) in rows:
                if filtro and filtro not in mat:
                    continue
                fijo, disp = obtener_stock_material(mat)
                card = crear_tarjeta(dp(72), '#0D1B2A')
                card.add_widget(Label(
                    text=f"[b]{mat}[/b]",
                    markup=True, color=get_color_from_hex('#00D4FF'),
                    size_hint_y=None, height=dp(22), font_size='13sp',
                    halign='left', text_size=(Window.width * 0.5, None)))

                estado_color = '#00D4FF' if disp > 0 else '#FF0044'
                card.add_widget(Label(
                    text=f"Stock: [color={estado_color}]{disp}[/color]  |  Total sistema: {fijo}",
                    markup=True, color=get_color_from_hex('#5A6A7A'),
                    size_hint_y=None, height=dp(18), font_size='11sp',
                    halign='left', text_size=(Window.width * 0.5, None)))

                total_movs = db_query(
                    "SELECT COUNT(*) FROM movimientos WHERE UPPER(material)=?",
                    (mat,), fetchall=False
                )[0] or 0

                btn_row = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(6))
                btn_limpiar = Button(
                    text="ELIMINAR MATERIAL", size_hint_x=0.5,
                    font_size='10sp', bold=True,
                    background_color=get_color_from_hex('#FF0044'))
                btn_limpiar.bind(on_release=lambda x, m=mat, c=total_movs: self._confirmar_eliminar("material", m, c))
                btn_row.add_widget(btn_limpiar)
                btn_row.add_widget(Label(
                    text=f"{total_movs} movs",
                    color=get_color_from_hex('#5A6A7A'), font_size='10sp',
                    size_hint_x=0.5, halign='center'))
                card.add_widget(btn_row)
                self.ids.lista_gestion.add_widget(card)

        else:
            self.ids.titulo_seccion.text = "RESPONSABLES"
            rows = db_query(
                "SELECT DISTINCT UPPER(nombre) FROM movimientos WHERE UPPER(nombre) != 'INVENTARIO' ORDER BY nombre"
            )
            for (nom,) in rows:
                if filtro and filtro not in nom:
                    continue
                total_movs = db_query(
                    "SELECT COUNT(*) FROM movimientos WHERE UPPER(nombre)=?",
                    (nom,), fetchall=False
                )[0] or 0
                ultima_fecha = db_query(
                    "SELECT fecha FROM movimientos WHERE UPPER(nombre)=? ORDER BY id DESC LIMIT 1",
                    (nom,), fetchall=False
                )
                ultimo = str(ultima_fecha[0]) if ultima_fecha else "N/A"

                card = crear_tarjeta(dp(72), '#0D1B2A')
                card.add_widget(Label(
                    text=f"[b]{nom}[/b]",
                    markup=True, color=get_color_from_hex('#FF0044'),
                    size_hint_y=None, height=dp(22), font_size='13sp',
                    halign='left', text_size=(Window.width * 0.5, None)))
                card.add_widget(Label(
                    text=f"Ultimo movimiento: {ultimo}",
                    color=get_color_from_hex('#5A6A7A'),
                    size_hint_y=None, height=dp(18), font_size='11sp',
                    halign='left', text_size=(Window.width * 0.5, None)))

                btn_row = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(6))
                btn_limpiar = Button(
                    text="ELIMINAR RESPONSABLE", size_hint_x=0.5,
                    font_size='10sp', bold=True,
                    background_color=get_color_from_hex('#FF0044'))
                btn_limpiar.bind(on_release=lambda x, n=nom, c=total_movs: self._confirmar_eliminar("responsable", n, c))
                btn_row.add_widget(btn_limpiar)
                btn_row.add_widget(Label(
                    text=f"{total_movs} movs",
                    color=get_color_from_hex('#5A6A7A'), font_size='10sp',
                    size_hint_x=0.5, halign='center'))
                card.add_widget(btn_row)
                self.ids.lista_gestion.add_widget(card)

    def cambiar_modo(self, modo):
        self._modo = modo
        self.ids.filtro_gestion.text = ""
        self.cargar()

    def filtrar(self):
        self.cargar(self.ids.filtro_gestion.text)

    def _confirmar_eliminar(self, tipo, nombre, total_movs):
        tipo_txt = "material" if tipo == "material" else "responsable"
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        pop = Popup(
            title=f"ELIMINAR {tipo_txt.upper()}",
            content=content, size_hint=(0.88, 0.42))
        content.add_widget(Label(
            text=f"Eliminar [b]{nombre}[/b] y sus {total_movs} movimiento(s)?",
            markup=True, halign='center', color=get_color_from_hex('#FF0044'),
            font_size='13sp'))
        content.add_widget(Label(
            text="Esta accion no se puede deshacer.",
            color=get_color_from_hex('#5A6A7A'), font_size='11sp',
            halign='center'))

        def ejecutar(btn):
            try:
                if tipo == "material":
                    db_execute("DELETE FROM movimientos WHERE UPPER(material)=?", (nombre,))
                    db_execute("DELETE FROM alertas_stock WHERE UPPER(material)=?", (nombre,))
                    log_auditoria("ELIMINAR_MATERIAL", f"{nombre}: {total_movs} movs eliminados")
                else:
                    db_execute("DELETE FROM movimientos WHERE UPPER(nombre)=?", (nombre,))
                    log_auditoria("ELIMINAR_RESPONSABLE", f"{nombre}: {total_movs} movs eliminados")
                pop.dismiss()
                Toast.show(f"{nombre} eliminado", '#FF0044', 3)
                self.cargar(self.ids.filtro_gestion.text)
            except Exception as e:
                pop.dismiss()
                Toast.show(f"Error: {e}", '#FF0044', 4)

        btn = Button(text="SI, ELIMINAR TODO",
                     size_hint_y=None, height=dp(48),
                     background_color=get_color_from_hex('#FF0044'),
                     on_release=ejecutar)
        content.add_widget(btn)
        content.add_widget(Button(text="CANCELAR", size_hint_y=None, height=dp(40),
                                   background_color=get_color_from_hex('#334155'),
                                   on_release=pop.dismiss))
        pop.open()
