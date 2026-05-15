from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivy.utils import get_color_from_hex


def crear_tarjeta(altura=dp(90), color='#0D1B2A', radius=dp(4)) -> BoxLayout:
    card = BoxLayout(orientation='vertical', size_hint_y=None, height=altura, padding=dp(10))
    with card.canvas.before:
        Color(rgba=get_color_from_hex(color))
        card._rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[radius])

    def _upd(inst, val):
        inst._rect.pos  = inst.pos
        inst._rect.size = inst.size

    card.bind(pos=_upd, size=_upd)
    return card
