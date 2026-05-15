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
from database.connection import db_query, db_execute
from services.inventario import obtener_stock_material
from widgets.tarjeta import crear_tarjeta
from logging_config import logger


class ValorScreen(Screen):
    _precios = {}

    def on_enter(self):
        self._cargar_precios_guardados()
        self.cargar_materiales()

    def _cargar_precios_guardados(self):
        rows = db_query("SELECT clave, valor FROM config_app WHERE clave LIKE 'precio_%'")
        for clave, valor in rows:
            try:
                mat = clave.replace("precio_", "", 1)
                self._precios[mat] = int(valor)
            except Exception:
                pass

    def _guardar_precio(self, material, precio):
        db_execute(
            "INSERT INTO config_app (clave, valor) VALUES (?, ?) ON CONFLICT(clave) DO UPDATE SET valor = ?",
            (f"precio_{material}", str(precio), str(precio))
        )

    def cargar_materiales(self):
        self.ids.lista_valores.clear_widgets()
        rows = db_query("SELECT DISTINCT UPPER(material) FROM movimientos ORDER BY material")
        materiales = [r[0] for r in rows]
        self.ids.spinner_material.values = materiales
        self.actualizar_valor_unitario()

    def _ajustar_scroll(self):
        children = self.ids.lista_valores.children
        if children:
            total = sum(c.height for c in children) + (len(children) - 1) * dp(4)
            self.ids.scroll_items.height = min(total, dp(300))
        else:
            self.ids.scroll_items.height = 0

    def _calcular_total_inventario(self):
        rows = db_query("""
            SELECT UPPER(material), SUM(CASE WHEN tipo='ENTRADA' THEN cantidad ELSE -cantidad END)
            FROM movimientos GROUP BY UPPER(material)
        """)
        total = 0
        for mat, disp in rows:
            if disp and disp > 0:
                precio = self._precios.get(mat, 0)
                total += disp * precio
        return total

    def actualizar_valor_unitario(self):
        self.ids.lista_valores.clear_widgets()
        self._ajustar_scroll()
        mat = self.ids.spinner_material.text

        total_inventario = self._calcular_total_inventario()
        self.ids.total_inventario_label.text = f"$ {total_inventario:,.0f}"
        self.ids.total_inventario_label.color = get_color_from_hex('#00D4FF') if total_inventario > 0 else get_color_from_hex('#5A6A7A')

        if mat == "-- SELECCIONAR --" or not mat:
            self.ids.unitario_label.text = "$ 0"
            self.ids.unitario_label.color = get_color_from_hex('#5A6A7A')
            self.ids.total_label.text = "$ 0"
            self.ids.total_label.color = get_color_from_hex('#5A6A7A')
            return
        precio = self._precios.get(mat, 0)

        _, disp = obtener_stock_material(mat)
        if disp <= 0:
            self.ids.unitario_label.text = "$ 0"
            self.ids.unitario_label.color = get_color_from_hex('#5A6A7A')
            self.ids.total_label.text = "$ 0"
            self.ids.total_label.color = get_color_from_hex('#5A6A7A')
            return

        if precio > 0:
            self.ids.unitario_label.text = f"$ {precio:,.0f}"
            self.ids.unitario_label.color = get_color_from_hex('#00D4FF')
            subtotal = disp * precio
            self.ids.total_label.text = f"$ {subtotal:,.0f}"
            self.ids.total_label.color = get_color_from_hex('#00D4FF')
        else:
            self.ids.unitario_label.text = "SIN PRECIO"
            self.ids.unitario_label.color = get_color_from_hex('#5A6A7A')
            self.ids.total_label.text = "SIN PRECIO"
            self.ids.total_label.color = get_color_from_hex('#5A6A7A')

        card = crear_tarjeta(dp(56), '#1A2035')
        header = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        header.add_widget(Label(
            text=f"[b]{mat}[/b]  x [color=#00D4FF]{disp}[/color]",
            markup=True, color=get_color_from_hex('#00D4FF'),
            font_size='12sp', halign='left', valign='middle',
            text_size=(Window.width * 0.45, None),
            size_hint_x=0.5, shorten=True, shorten_from='right'))
        if precio > 0:
            subtotal = disp * precio
            header.add_widget(Label(
                text=f"$ {precio:,.0f}",
                color=get_color_from_hex('#00D4FF'),
                font_size='12sp', halign='center', valign='middle',
                text_size=self.size, size_hint_x=0.25, shorten=True))
            header.add_widget(Label(
                text=f"$ {subtotal:,.0f}",
                color=get_color_from_hex('#E8EAED'),
                font_size='13sp', halign='center', valign='middle',
                text_size=self.size, size_hint_x=0.25, bold=True, shorten=True))
        else:
            header.add_widget(Label(
                text="-",
                color=get_color_from_hex('#475569'),
                font_size='11sp', halign='center', valign='middle',
                size_hint_x=0.25))
            header.add_widget(Label(
                text="-",
                color=get_color_from_hex('#475569'),
                font_size='11sp', halign='center', valign='middle',
                size_hint_x=0.25))
        card.add_widget(header)
        self.ids.lista_valores.add_widget(card)
        self._ajustar_scroll()

    def asignar_precio(self):
        mat = self.ids.spinner_material.text
        precio_str = self.ids.input_precio.text.strip()
        if mat == "-- SELECCIONAR --" or not mat:
            self.ids.info_valor.text = "Selecciona un material"
            return
        if not precio_str:
            self.ids.info_valor.text = "Ingresa un precio"
            return
        try:
            precio = int(float(precio_str.replace(",", "")))
        except ValueError:
            self.ids.info_valor.text = "Precio invalido"
            return
        if precio <= 0:
            self.ids.info_valor.text = "Precio debe ser mayor a 0"
            return
        self._precios[mat] = precio
        self._guardar_precio(mat, precio)
        self.ids.input_precio.text = ""
        self.ids.info_valor.text = f"{mat}: $ {precio:,} asignado"
        self.cargar_materiales()
