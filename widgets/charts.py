from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window


class BarraHorizontal(BoxLayout):
    def __init__(self, label, valor, maximo, color='#00D4FF', **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(32)
        self.spacing = dp(2)

        pct = min(valor / maximo, 1.0) if maximo > 0 else 0

        header = BoxLayout(size_hint_y=None, height=dp(16))
        header.add_widget(Label(
            text=f"{label}:  {valor}",
            color=get_color_from_hex('#CBD5E1'),
            font_size='11sp', halign='left',
            text_size=(Window.width * 0.78, None),
            size_hint_y=None, height=dp(16)
        ))
        self.add_widget(header)

        bar_bg = BoxLayout(size_hint_y=None, height=dp(12))
        with bar_bg.canvas.before:
            Color(rgba=get_color_from_hex('#0F172A'))
            bar_bg._rect_bg = RoundedRectangle(pos=bar_bg.pos, size=bar_bg.size, radius=[dp(6)])
        bar_bg.bind(
            pos=lambda i, v: setattr(bar_bg._rect_bg, 'pos', v),
            size=lambda i, v: setattr(bar_bg._rect_bg, 'size', v)
        )

        bar_fill = Widget(size_hint_x=max(pct, 0.02), size_hint_y=1)
        with bar_fill.canvas.before:
            Color(rgba=get_color_from_hex(color))
            bar_fill._rect_fill = RoundedRectangle(pos=bar_fill.pos, size=bar_fill.size, radius=[dp(6)])
        bar_fill.bind(
            pos=lambda i, v: setattr(bar_fill._rect_fill, 'pos', v),
            size=lambda i, v: setattr(bar_fill._rect_fill, 'size', v)
        )
        bar_bg.add_widget(bar_fill)
        self.add_widget(bar_bg)


class GraficoTendencia(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(110)
        self.spacing = dp(4)

    def mostrar(self, datos, color='#00D4FF'):
        self.clear_widgets()
        if not datos:
            self.add_widget(Label(text="Sin datos", color=get_color_from_hex('#64748B'),
                                  size_hint_y=None, height=dp(30)))
            return
        max_val = max(datos) if max(datos) > 0 else 1
        header = BoxLayout(size_hint_y=None, height=dp(18))
        header.add_widget(Label(text="Tendencia", color=get_color_from_hex('#94A3B8'),
                                font_size='11sp', halign='left',
                                text_size=(Window.width * 0.8, None)))
        self.add_widget(header)

        bars = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(3), padding=[0, dp(4)])
        for val in datos:
            pct = max(val / max_val, 0.05)
            bar = Widget(size_hint_x=None, width=dp(20), size_hint_y=pct,
                         pos_hint={'y': 0})
            from kivy.graphics import Color as GColor, RoundedRectangle as GRect
            with bar.canvas.before:
                GColor(rgba=get_color_from_hex(color))
                bar._rect = GRect(pos=bar.pos, size=bar.size, radius=[dp(4)])
            bar.bind(
                pos=lambda i, v: setattr(bar._rect, 'pos', v) if hasattr(bar, '_rect') else None,
                size=lambda i, v: setattr(bar._rect, 'size', v) if hasattr(bar, '_rect') else None
            )
            bars.add_widget(bar)
        self.add_widget(bars)

        labels = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(3))
        for i, val in enumerate(datos):
            labels.add_widget(Label(text=str(val), color=get_color_from_hex('#64748B'),
                                    font_size='9sp', halign='center'))
        self.add_widget(labels)
