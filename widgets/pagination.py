from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.utils import get_color_from_hex


class PaginationBar(BoxLayout):
    def __init__(self, callback=None, page_size=20, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.page_size = page_size
        self.total = 0
        self.current_page = 0
        self.total_pages = 0
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(40)
        self.spacing = dp(6)
        self._build_ui()

    def _build_ui(self):
        self.clear_widgets()
        self._btn_prev = Button(
            text="<", size_hint_x=None, width=dp(48),
            background_color=get_color_from_hex('#334155'),
            font_size='15sp', bold=True,
            on_release=lambda x: self._ir_pagina(self.current_page - 1)
        )
        self.add_widget(self._btn_prev)

        self._lbl_info = Label(
            text="", color=get_color_from_hex('#94A3B8'),
            font_size='12sp', halign='center'
        )
        self.add_widget(self._lbl_info)

        self._btn_next = Button(
            text=">", size_hint_x=None, width=dp(48),
            background_color=get_color_from_hex('#334155'),
            font_size='15sp', bold=True,
            on_release=lambda x: self._ir_pagina(self.current_page + 1)
        )
        self.add_widget(self._btn_next)

    def actualizar(self, total):
        self.total = total
        self.total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.current_page >= self.total_pages:
            self.current_page = max(0, self.total_pages - 1)
        self._actualizar_ui(notificar=False)

    def _actualizar_ui(self, notificar=True):
        inicio = self.current_page * self.page_size + 1
        fin = min((self.current_page + 1) * self.page_size, self.total)
        self._lbl_info.text = f"{inicio}-{fin} / {self.total}" if self.total > 0 else "0"
        self._btn_prev.disabled = self.current_page <= 0
        self._btn_next.disabled = self.current_page >= self.total_pages - 1 or self.total_pages <= 1
        if notificar and self.callback:
            self.callback(self.current_page, self.page_size)

    def _ir_pagina(self, pagina):
        if pagina < 0 or pagina >= self.total_pages:
            return
        self.current_page = pagina
        self._actualizar_ui(notificar=True)
