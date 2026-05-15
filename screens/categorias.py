from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from database.connection import db_query, db_execute
from widgets.tarjeta import crear_tarjeta
from logging_config import logger


class CategoriasScreen(Screen):
    def on_enter(self):
        self.cargar_categorias()

    def cargar_categorias(self):
        self.ids.lista_categorias.clear_widgets()
        rows = db_query("SELECT id, nombre, descripcion, color_hex FROM categorias ORDER BY nombre")
        if not rows:
            lbl = Label(text="Sin categorias - crea una con + NUEVA",
                        color=get_color_from_hex('#94A3B8'),
                        size_hint_y=None, height=dp(60))
            self.ids.lista_categorias.add_widget(lbl)
            return
        for r in rows:
            items = db_query("SELECT nombre FROM categoria_items WHERE categoria_id = ? ORDER BY nombre", (r[0],))
            item_count = len(items)
            item_names = ", ".join([it[0] for it in items[:5]])
            if len(items) > 5:
                item_names += f" ... (+{len(items)-5})"
            card_height = dp(80) + (min(len(items), 5) * dp(22) if items else 0)
            card = crear_tarjeta(card_height, '#1A2035')

            header = BoxLayout(size_hint_y=None, height=dp(26))
            header.add_widget(Label(
                text=f"[b]{r[1]}[/b]  [color=#64748B]({item_count} items)[/color]",
                markup=True, color=get_color_from_hex(r[3] or '#38BDF8'),
                font_size='13sp', halign='left',
                text_size=(Window.width * 0.5, None), size_hint_x=0.55))
            btn_items = Button(text="ITEMS", size_hint_x=0.18,
                               font_size='11sp',
                               background_color=get_color_from_hex('#0E7490'))
            btn_items.bind(on_release=lambda x, cid=r[0], cnom=r[1]: self._gestionar_items(cid, cnom))
            header.add_widget(btn_items)
            btn_del = Button(text="X", size_hint_x=0.12,
                             font_size='13sp', bold=True,
                             background_color=get_color_from_hex('#991B1B'))
            btn_del.bind(on_release=lambda x, cid=r[0]: self._eliminar(cid))
            header.add_widget(btn_del)
            card.add_widget(header)

            if items:
                for it in items[:5]:
                    card.add_widget(Label(
                        text=f"  • {it[0]}",
                        color=get_color_from_hex('#94A3B8'),
                        size_hint_y=None, height=dp(20), font_size='11sp',
                        halign='left', text_size=(Window.width * 0.8, None)))

            self.ids.lista_categorias.add_widget(card)

    def mostrar_nueva(self):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
        pop = Popup(title="NUEVA CATEGORIA", content=content, size_hint=(0.88, 0.48))
        inp_nombre = TextInput(hint_text="Nombre (ej: H, ANGULO, PLATINA)", multiline=False,
                               size_hint_y=None, height=dp(45))
        inp_desc = TextInput(hint_text="Descripcion (opcional)", multiline=False,
                             size_hint_y=None, height=dp(45))
        colores = ["#38BDF8", "#F59E0B", "#10B981", "#F87171", "#A78BFA", "#F472B6", "#34D399"]
        spinner_color = Spinner(text=colores[0], values=colores, size_hint_y=None, height=dp(45))
        content.add_widget(Label(text="Nombre", color=get_color_from_hex('#94A3B8'),
                                  font_size='12sp', size_hint_y=None, height=dp(18)))
        content.add_widget(inp_nombre)
        content.add_widget(inp_desc)
        content.add_widget(spinner_color)

        def guardar(btn):
            nombre = inp_nombre.text.strip().upper()
            if not nombre:
                inp_nombre.text = "Obligatorio"
                return
            try:
                db_execute("INSERT INTO categorias (nombre, descripcion, color_hex) VALUES (?,?,?)",
                           (nombre, inp_desc.text.strip(), spinner_color.text))
                pop.dismiss()
                self.cargar_categorias()
            except Exception as e:
                inp_nombre.text = f"Error: {e}"

        btn = Button(text="CREAR", size_hint_y=None, height=dp(48),
                     background_color=get_color_from_hex('#059669'), on_release=guardar)
        content.add_widget(btn)
        content.add_widget(Button(text="CANCELAR", size_hint_y=None, height=dp(40),
                                   background_color=get_color_from_hex('#334155'),
                                   on_release=pop.dismiss))
        pop.open()

    def _gestionar_items(self, cid, cnom):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(12))
        pop = Popup(title=f"ITEMS: {cnom}", content=content, size_hint=(0.92, 0.78))

        inp = TextInput(hint_text="Nuevo item (ej: H 80)", multiline=False,
                        size_hint_y=None, height=dp(42))
        btn_add = Button(text="AGREGAR", size_hint_y=None, height=dp(40),
                         background_color=get_color_from_hex('#059669'))
        input_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        input_row.add_widget(inp)
        input_row.add_widget(btn_add)
        content.add_widget(input_row)

        sv = ScrollView()
        gl = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        gl.bind(minimum_height=gl.setter('height'))

        def refrescar():
            gl.clear_widgets()
            items = db_query("SELECT id, nombre FROM categoria_items WHERE categoria_id = ? ORDER BY nombre", (cid,))
            if not items:
                gl.add_widget(Label(text="Sin items todavia", color=get_color_from_hex('#64748B'),
                                     size_hint_y=None, height=dp(40)))
            for it in items:
                row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
                row.add_widget(Label(
                    text=f"  {it[1]}",
                    color=get_color_from_hex('#CBD5E1'),
                    font_size='12sp', halign='left',
                    text_size=(Window.width * 0.7, None),
                    size_hint_x=0.8))
                btn_rm = Button(text="X", size_hint_x=0.2,
                                font_size='12sp',
                                background_color=get_color_from_hex('#991B1B'))
                btn_rm.bind(on_release=lambda x, iid=it[0]: (_eliminar_item(iid), refrescar()))
                row.add_widget(btn_rm)
                gl.add_widget(row)

        def _eliminar_item(iid):
            db_execute("DELETE FROM categoria_items WHERE id = ?", (iid,))

        def agregar():
            nombre = inp.text.strip().upper()
            if nombre:
                try:
                    db_execute("INSERT INTO categoria_items (categoria_id, nombre) VALUES (?,?)",
                               (cid, nombre))
                    inp.text = ""
                    refrescar()
                except Exception as e:
                    inp.text = f"Ya existe o error"
            inp.focus = True

        btn_add.bind(on_release=lambda x: agregar())
        inp.bind(on_text_validate=lambda x: agregar())
        sv.add_widget(gl)
        content.add_widget(sv)

        btn_cerrar = Button(text="CERRAR", size_hint_y=None, height=dp(44),
                            background_color=get_color_from_hex('#334155'),
                            on_release=pop.dismiss)
        content.add_widget(btn_cerrar)

        refrescar()
        pop.open()

    def _eliminar(self, cid):
        db_execute("DELETE FROM categoria_items WHERE categoria_id = ?", (cid,))
        db_execute("DELETE FROM categorias WHERE id = ?", (cid,))
        self.cargar_categorias()
