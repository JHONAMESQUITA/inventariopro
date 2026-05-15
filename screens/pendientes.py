from collections import defaultdict
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window
from database.connection import db_query
from widgets.tarjeta import crear_tarjeta
from logging_config import logger


class PendientesScreen(Screen):
    def on_enter(self):
        self.cargar_pendientes()

    def cargar_pendientes(self) -> None:
        try:
            self.ids.lista_pendientes.clear_widgets()
            filtro = self.ids.filtro_pendientes.text.upper()
            rows = db_query(
                "SELECT nombre,material,sku,cantidad,tipo,fecha,notas FROM movimientos "
                "WHERE UPPER(nombre) != 'INVENTARIO' ORDER BY id ASC"
            )
            actualmente_fuera = {}
            for n, m, s, c, t, f, notas in rows:
                key = f"{n}|{m}"
                if t == "SALIDA":
                    if key not in actualmente_fuera:
                        actualmente_fuera[key] = [n, m, s, float(c), t, f, notas or ""]
                    else:
                        actualmente_fuera[key][3] += float(c)
                        nota_existente = actualmente_fuera[key][6]
                        nota_nueva = notas or ""
                        if nota_nueva and nota_nueva not in nota_existente:
                            actualmente_fuera[key][6] = (
                                (nota_existente + " | " + nota_nueva).strip(" | ")
                                if nota_existente else nota_nueva
                            )
                elif t == "ENTRADA" and key in actualmente_fuera:
                    actualmente_fuera[key][3] -= float(c)
                    if actualmente_fuera[key][3] <= 0:
                        del actualmente_fuera[key]

            grupos = defaultdict(list)
            for item in actualmente_fuera.values():
                if filtro and filtro not in item[0].upper() and filtro not in item[1].upper():
                    continue
                grupos[item[0]].append(item)

            if not grupos:
                card = crear_tarjeta(dp(70), '#1E293B')
                card.add_widget(Label(text="No hay materiales fuera",
                                      color=get_color_from_hex('#10B981')))
                self.ids.lista_pendientes.add_widget(card)
                return

            for responsable, materiales in sorted(grupos.items()):
                extra_por_item = [dp(75) if (it[6] and it[6].strip()) else dp(58) for it in materiales]
                btns_height = dp(32) if len(materiales) > 1 else 0
                card_h = dp(50) + sum(extra_por_item) + btns_height
                card = crear_tarjeta(card_h, '#1A2035')

                header = BoxLayout(size_hint_y=None, height=dp(30))
                header.add_widget(Label(
                    text=f"[b]{responsable}[/b]  ({len(materiales)} material{'es' if len(materiales)>1 else ''})",
                    markup=True, color=get_color_from_hex('#FF0044'),
                    size_hint_y=None, height=dp(30),
                    halign='center', valign='middle',
                    text_size=(Window.width * 0.9, None),
                    size_hint_x=1, shorten=True, shorten_from='right'))
                if len(materiales) > 1:
                    btn_entrar_todo = Button(
                        text="ENTRAR TODO", size_hint_x=0.4,
                        font_size='11sp', bold=True,
                        background_color=get_color_from_hex('#059669'))
                    btn_entrar_todo.bind(on_release=lambda x, r=responsable, mats=materiales: self.confirmar_entrar_todo(r, mats))
                    header.add_widget(btn_entrar_todo)
                else:
                    header.add_widget(Label(size_hint_x=0.4))
                card.add_widget(header)

                for it in materiales:
                    n, m, s, c, _, f, notas = it
                    tiene_notas = bool(notas and notas.strip())
                    item_box = BoxLayout(
                        orientation='vertical',
                        size_hint_y=None,
                        height=dp(72) if tiene_notas else dp(55),
                        spacing=dp(2)
                    )
                    with item_box.canvas.before:
                        Color(rgba=get_color_from_hex('#334155'))
                        item_box._rect = RoundedRectangle(
                            pos=item_box.pos, size=item_box.size, radius=[dp(8)]
                        )

                    def _make_rect_updater(rect):
                        def upd_pos(i, v):
                            rect.pos = v
                        def upd_size(i, v):
                            rect.size = v
                        return upd_pos, upd_size

                    _upd_pos, _upd_size = _make_rect_updater(item_box._rect)
                    item_box.bind(pos=_upd_pos, size=_upd_size)

                    btn_text = (
                        f"[b]{m}[/b]   x{round(c,2)}\n"
                        f"[size=11sp][color=#94A3B8]SKU: {s or 'N/A'}  |  Salida: {f}[/color][/size]"
                    )
                    btn = Button(
                        text=btn_text, markup=True, size_hint_y=None, height=dp(55),
                        background_color=(0, 0, 0, 0),
                        halign='left', valign='middle', padding=[dp(8), 0])
                    btn.bind(on_release=lambda x, i=it: self.confirmar_retorno_individual(i))
                    item_box.add_widget(btn)

                    if tiene_notas:
                        notas_box = BoxLayout(
                            orientation='horizontal',
                            size_hint_y=None, height=dp(22),
                            padding=[dp(10), 0])
                        with notas_box.canvas.before:
                            Color(rgba=get_color_from_hex('#1E3A5F'))
                            notas_box._rect2 = RoundedRectangle(
                                pos=notas_box.pos, size=notas_box.size,
                                radius=[dp(0), dp(0), dp(8), dp(8)])

                        def _make_rect2_updater(rect2):
                            def upd_pos2(i, v):
                                rect2.pos = v
                            def upd_size2(i, v):
                                rect2.size = v
                            return upd_pos2, upd_size2

                        _upd_pos2, _upd_size2 = _make_rect2_updater(notas_box._rect2)
                        notas_box.bind(pos=_upd_pos2, size=_upd_size2)
                        notas_box.add_widget(Label(
                            text=f"[color=#64748B]NOTAS:[/color] [color=#CBD5E1]{notas}[/color]",
                            markup=True, font_size='11sp',
                            halign='left', valign='middle',
                            text_size=(Window.width * 0.82, None)))
                        item_box.add_widget(notas_box)
                    card.add_widget(item_box)
                self.ids.lista_pendientes.add_widget(card)
        except Exception as e:
            logger.error("Error cargando pendientes: %s", e)

    def confirmar_retorno_individual(self, item):
        n, m, s, c, _, f, notas = item
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(12))
        pop = Popup(title="RETORNAR MATERIAL", content=content, size_hint=(0.9, 0.55))

        content.add_widget(Label(
            text=f"[b]{m}[/b]  x[color=#F59E0B]{round(c, 2)}[/color]  de [color=#F87171]{n}[/color]",
            markup=True, font_size='14sp', halign='center', valign='middle',
            size_hint_y=None, height=dp(34),
            text_size=(Window.width * 0.8, None), shorten=True, shorten_from='right'))
        content.add_widget(Label(
            text=f"SKU: {s or 'N/A'}  |  Salida: {f[:16]}",
            color=get_color_from_hex('#64748B'), font_size='11sp',
            size_hint_y=None, height=dp(20), halign='center'))

        info = Label(
            text="", color=get_color_from_hex('#F59E0B'),
            size_hint_y=None, height=dp(22), font_size='12sp', halign='center')
        content.add_widget(info)

        inp = TextInput(
            hint_text=f"Cantidad a retornar (max {round(c,2)})",
            input_filter='float', multiline=False,
            size_hint_y=None, height=dp(48), font_size='16sp')
        content.add_widget(inp)

        def retornar_todo(btn):
            pop.dismiss()
            self._ejecutar_retorno(item, round(c, 2))

        def retornar_parcial(btn):
            val_str = inp.text.strip()
            if not val_str:
                info.text = "Ingresa una cantidad"
                return
            try:
                val = float(val_str)
            except ValueError:
                info.text = "Cantidad invalida"
                return
            if val <= 0:
                info.text = "Debe ser mayor a 0"
                return
            if val > c:
                info.text = f"Maximo {round(c, 2)}"
                return
            pop.dismiss()
            self._ejecutar_retorno(item, round(val, 4))

        btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_todo = Button(
            text=f"ENTRAR TODO ({round(c, 2)})",
            font_size='13sp', bold=True,
            background_color=get_color_from_hex('#059669'))
        btn_todo.bind(on_release=retornar_todo)
        btns.add_widget(btn_todo)
        btn_parcial = Button(
            text="ENTRAR CANTIDAD",
            font_size='11sp',
            background_color=get_color_from_hex('#2563EB'))
        btn_parcial.bind(on_release=retornar_parcial)
        btns.add_widget(btn_parcial)
        content.add_widget(btns)
        content.add_widget(Button(text="CANCELAR", size_hint_y=None, height=dp(40),
                                   background_color=get_color_from_hex('#334155'),
                                   on_release=pop.dismiss))
        pop.open()

    def confirmar_entrar_todo(self, responsable, materiales):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
        pop = Popup(title=f"RETORNAR TODO: {responsable}", content=content, size_hint=(0.88, 0.45))
        content.add_widget(Label(
            text=f"Entrar todos los materiales de [b]{responsable}[/b]?",
            markup=True, font_size='13sp', halign='center',
            size_hint_y=None, height=dp(30)))
        for it in materiales:
            content.add_widget(Label(
                text=f"  {it[1]}  x{round(it[3], 2)}",
                color=get_color_from_hex('#94A3B8'),
                size_hint_y=None, height=dp(20), font_size='11sp',
                halign='left', text_size=(Window.width * 0.7, None)))

        def ejecutar(btn):
            pop.dismiss()
            for it in materiales:
                self._ejecutar_retorno(it, round(it[3], 2))
            Clock.schedule_once(lambda dt: self.cargar_pendientes(), 0.3)

        btn = Button(text="SI, ENTRAR TODO",
                     size_hint_y=None, height=dp(48),
                     background_color=get_color_from_hex('#059669'),
                     on_release=ejecutar)
        content.add_widget(btn)
        content.add_widget(Button(text="CANCELAR", size_hint_y=None, height=dp(40),
                                   background_color=get_color_from_hex('#334155'),
                                   on_release=pop.dismiss))
        pop.open()

    def _ejecutar_retorno(self, item, cantidad):
        n, m, s, c, _, _, _ = item
        App.get_running_app().root.get_screen('inventario').procesar(
            "ENTRADA", r=n, p=m, c=cantidad, s=s, desde_retorno=True)
