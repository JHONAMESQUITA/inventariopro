from datetime import datetime, timedelta
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.app import App
from services.alertas import obtener_equipos_en_prestamo
from widgets.tarjeta import crear_tarjeta
from logging_config import logger


def _calcular_vencimiento(fecha_salida, dias_acordados):
    if not dias_acordados or dias_acordados <= 0:
        return "Sin vencimiento"
    try:
        fecha_dt = datetime.strptime(fecha_salida[:16], "%d/%m/%Y %H:%M")
        vence = fecha_dt + timedelta(days=dias_acordados)
        return vence.strftime("%d/%m/%Y")
    except Exception:
        return "Fecha invalida"


class AlertasScreen(Screen):
    def on_enter(self):
        self.cargar_alertas()

    def cargar_alertas(self):
        self.ids.container_alertas.clear_widgets()
        prestamos = obtener_equipos_en_prestamo()

        vencidos = [p for p in prestamos if p["estado"] == "VENCIDO"]
        por_vencer = [p for p in prestamos if p["estado"] == "POR_VENCER"]
        en_tiempo = [p for p in prestamos if p["estado"] == "EN_TIEMPO"]

        total_alertas = len(vencidos) + len(por_vencer)
        self.ids.total_alertas.text = f"Alertas: {total_alertas}"

        if total_alertas == 0 and not en_tiempo:
            card = crear_tarjeta(dp(70), '#0D1B2A')
            card.add_widget(Label(
                text="[color=#00D4FF]Todo en orden[/color]",
                markup=True, font_size='15sp', halign='center'))
            card.add_widget(Label(
                text="No hay materiales pendientes de retorno",
                color=get_color_from_hex('#5A6A7A'), font_size='12sp', halign='center'))
            self.ids.container_alertas.add_widget(card)
            return

        if vencidos:
            self.ids.container_alertas.add_widget(Label(
                text=f"VENCIDOS ({len(vencidos)})",
                bold=True, font_size='14sp',
                color=get_color_from_hex('#FF0044'),
                size_hint_y=None, height=dp(32),
                halign='left', text_size=(Window.width * 0.88, None)))

            for p in vencidos:
                self._agregar_tarjeta_prestamo(p, '#0D1B2A', '#FF0044')

        if por_vencer:
            self.ids.container_alertas.add_widget(Label(
                text=f"POR VENCER ({len(por_vencer)})",
                bold=True, font_size='14sp',
                color=get_color_from_hex('#FF0044'),
                size_hint_y=None, height=dp(32),
                halign='left', text_size=(Window.width * 0.88, None)))

            for p in por_vencer:
                self._agregar_tarjeta_prestamo(p, '#0D1B2A', '#FF0044')

        if en_tiempo:
            self.ids.container_alertas.add_widget(Label(
                text=f"EN TIEMPO ({len(en_tiempo)})",
                bold=True, font_size='13sp',
                color=get_color_from_hex('#5A6A7A'),
                size_hint_y=None, height=dp(28),
                halign='left', text_size=(Window.width * 0.88, None)))

            for p in en_tiempo:
                self._agregar_tarjeta_prestamo(p, '#0D1B2A', '#00D4FF')

    def _agregar_tarjeta_prestamo(self, p, color_fondo, color_estado):
        tiene_notas = bool(p["notas"] and p["notas"].strip())
        vence = _calcular_vencimiento(p["fecha_salida"], p["dias_acordados"])
        altura = dp(130) if tiene_notas else dp(108)
        card = crear_tarjeta(altura, color_fondo)

        header = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
        header.add_widget(Label(
            text=f"[b]{p['material']}[/b]  —  {p['responsable']}",
            markup=True, color=get_color_from_hex(color_estado),
            font_size='12sp', halign='left', valign='middle',
            text_size=(Window.width * 0.55, None),
            size_hint_x=0.6, shorten=True, shorten_from='right'))
        header.add_widget(Label(
            text=f"[color={color_estado}]{p['estado']}[/color]",
            markup=True, font_size='11sp', bold=True,
            size_hint_x=0.2, halign='center'))
        header.add_widget(Label(
            text=f"{p['dias_fuera']}d",
            color=get_color_from_hex('#5A6A7A'), font_size='11sp',
            size_hint_x=0.15, halign='center'))
        card.add_widget(header)

        sub = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(6))
        sub.add_widget(Label(
            text=f"Cant: {round(p['cantidad'], 2)}  |  SKU: {p['sku'] or 'N/A'}",
            color=get_color_from_hex('#5A6A7A'), font_size='11sp',
            halign='left', text_size=(Window.width * 0.55, None),
            size_hint_x=0.6))
        vence_label = vence if "Sin" in vence else f"Vence: {vence}"
        sub.add_widget(Label(
            text=vence_label,
            color=get_color_from_hex('#FF0044') if "Vence" in vence_label else get_color_from_hex('#5A6A7A'),
            font_size='10sp', size_hint_x=0.4, halign='center'))
        card.add_widget(sub)

        sub2 = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(6))
        sub2.add_widget(Label(
            text=f"Salida: {p['fecha_salida'][:16]}",
            color=get_color_from_hex('#5A6A7A'), font_size='10sp',
            halign='left', text_size=(Window.width * 0.55, None),
            size_hint_x=0.6))
        dias_txt = f"Acordado: {p['dias_acordados']}d" if p['dias_acordados'] > 0 else "Sin plazo"
        sub2.add_widget(Label(
            text=dias_txt,
            color=get_color_from_hex('#5A6A7A'), font_size='10sp',
            size_hint_x=0.4, halign='center'))
        card.add_widget(sub2)

        if tiene_notas:
            card.add_widget(Label(
                text=f"Notas: {p['notas']}",
                color=get_color_from_hex('#5A6A7A'),
                size_hint_y=None, height=dp(16), font_size='10sp',
                halign='left', text_size=(Window.width * 0.82, None)))

        btn_row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
        btn_row.add_widget(Widget(size_hint_x=0.6))
        btn_retornar = Button(
            text="RETORNAR", size_hint_x=0.4,
            font_size='10sp', bold=True,
            background_color=get_color_from_hex('#0066FF'))
        btn_retornar.bind(on_release=lambda x, item=p: self.confirmar_retorno(item))
        btn_row.add_widget(btn_retornar)
        card.add_widget(btn_row)

        self.ids.container_alertas.add_widget(card)

    def confirmar_retorno(self, p):
        content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        pop = Popup(title="Registrar Retorno", content=content, size_hint=(0.88, 0.45))
        content.add_widget(Label(
            text=f"Reingresar [b]{p['material']}[/b]  x{round(p['cantidad'], 2)}\nde [color=#FF0044]{p['responsable']}[/color]?",
            markup=True, halign='center', font_size='13sp',
            size_hint_y=None, height=dp(50)))
        btn = Button(text="SI, REGISTRAR RETORNO",
                     background_color=get_color_from_hex('#0066FF'),
                     bold=True, size_hint_y=None, height=dp(48))
        btn.bind(on_release=lambda x: self._ejecutar_retorno(p, pop))
        content.add_widget(btn)
        content.add_widget(Button(text="CANCELAR", size_hint_y=None, height=dp(42),
                                   background_color=get_color_from_hex('#334155'),
                                   on_release=pop.dismiss))
        pop.open()

    def _ejecutar_retorno(self, p, pop):
        pop.dismiss()
        App.get_running_app().root.get_screen('inventario').procesar(
            "ENTRADA", r=p['responsable'], p=p['material'], c=p['cantidad'], s=p['sku'], desde_retorno=True)
        Clock.schedule_once(lambda dt: self.cargar_alertas(), 0.3)
