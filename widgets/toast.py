from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.animation import Animation


class Toast(BoxLayout):
    _instance = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (None, None)
        self.pos_hint = {'center_x': 0.5}
        self.y = -dp(100)
        self.opacity = 0
        self._label = Label(
            text="", font_size='13sp',
            color=get_color_from_hex('#F8FAFC'),
            halign='center', valign='middle',
            padding=(dp(20), dp(12)),
            text_size=(Window.width * 0.85, None),
            size_hint=(None, None),
        )
        self._label.bind(texture_size=self._update_size)
        self.add_widget(self._label)

    def _update_size(self, inst, val):
        self.size = (min(val[0] + dp(40), Window.width * 0.9), val[1] + dp(24))

    @classmethod
    def show(cls, mensaje, color='#0066FF', duracion=3.0):
        if cls._instance is None:
            cls._instance = cls()
        toast = cls._instance
        if toast.parent:
            toast.parent.remove_widget(toast)
        toast._label.text = mensaje
        with toast.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(rgba=get_color_from_hex(color))
            toast._rect = RoundedRectangle(pos=toast.pos, size=toast.size, radius=[dp(10)])
        toast.bind(pos=lambda i, v: setattr(toast._rect, 'pos', v),
                   size=lambda i, v: setattr(toast._rect, 'size', v))
        Window.add_widget(toast)
        anim = Animation(y=dp(30), opacity=1, duration=0.3, t='out_back')
        anim.bind(on_complete=lambda *a: Clock.schedule_once(
            lambda dt: Animation(y=-dp(100), opacity=0, duration=0.3).start(toast), duracion))
        anim.start(toast)
