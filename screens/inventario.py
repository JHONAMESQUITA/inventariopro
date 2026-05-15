import os
import sqlite3
import threading
import gc
from datetime import datetime
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color as GColor, Line as GLine
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.metrics import dp
from config import EMAIL_CONFIG, DB_PATH, EXPORT_DIR, VERSION_ACTUAL
from database.connection import db_query, db_execute
from widgets.tarjeta import crear_tarjeta
from services.inventario import obtener_stock_material, obtener_alertas_activas, obtener_reporte_estadisticas
from services.alertas import obtener_equipos_en_prestamo
from services.auditoria import log_auditoria
from services.correo import enviar_reporte_por_correo, ActualizadorCorreo
from services.excel_service import generar_excel, ruta_exportacion
from logging_config import logger

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class InventarioScreen(Screen):
    _ultimo_mov_id = None
    _ultimo_mov_tipo = None
    _menu_abierto = False

    def on_enter(self):
        self.actualizar_spinners()
        self._verificar_alertas_silencioso()
        self._actualizar_dashboard()
        try:
            self.ids.info_carpeta.text = f"Exportaciones: {EXPORT_DIR}"
        except Exception:
            pass
        gc.collect()

    MENU_ITEMS = [
        ("FUERA", 'pendientes', '#FF0044'),
        ("FILTROS", 'filtros', '#00D4FF'),
        ("GESTION", 'gestion', '#FF6600'),
        ("AUDITORIA", 'auditoria', '#8800FF'),
        ("CATEGORIAS", 'categorias', '#FF00FF'),
        ("STOCK", 'stock', '#00FF88'),
        ("LIMPIEZA", 'limpieza', '#00FFFF'),
        ("ESTADISTICAS", 'estadisticas', '#FF0088'),
        ("AJUSTES", 'ajustes', '#FFFF00'),
        ("VALOR", 'valor', '#00D4FF'),
        ("UBICACIONES", 'ubicaciones', '#00FFAA'),
        ("IMPORTAR", 'importar', '#0088FF'),
    ]
    MENU_ACCIONES = [
        ("EXPORTAR", 'mostrar_opciones_exportar', '#FFAA00'),
        ("BACKUP", 'hacer_backup', '#00FF88'),
        ("ACT. CORREO", 'actualizar_desde_correo', '#FF6600'),
        ("ALERTAS", 'alertas', '#FF0044'),
    ]

    def _construir_menu(self):
        grid = self.ids.menu_grid
        grid.clear_widgets()
        from kivy.uix.button import Button
        for item in self.MENU_ITEMS:
            txt = item[0]
            scr = item[1]
            color = item[2] if len(item) > 2 else '#00D4FF'
            btn = Button(
                text=txt, size_hint_y=None, height=dp(38),
                background_normal='', background_color=[0.051, 0.106, 0.165, 1],
                color=get_color_from_hex(color), font_size='12sp',
                halign='left', valign='middle',
                padding=[dp(10), 0], text_size=(Window.width * 0.65, None),
            )
            btn.bind(on_release=lambda x, s=scr: (setattr(self.manager, 'current', s), self.toggle_menu()))
            grid.add_widget(btn)
        for item in self.MENU_ACCIONES:
            txt = item[0]
            metodo = item[1]
            color = item[2] if len(item) > 2 else '#00D4FF'
            btn = Button(
                text=txt, size_hint_y=None, height=dp(38),
                background_normal='', background_color=[0.051, 0.106, 0.165, 1],
                color=get_color_from_hex(color), font_size='12sp',
                halign='left', valign='middle',
                padding=[dp(10), 0], text_size=(Window.width * 0.65, None),
            )
            if metodo == 'mostrar_opciones_exportar':
                btn.bind(on_release=lambda x: (self.mostrar_opciones_exportar(), self.toggle_menu()))
            elif metodo == 'hacer_backup':
                btn.bind(on_release=lambda x: (self.hacer_backup(), self.toggle_menu()))
            elif metodo == 'actualizar_desde_correo':
                btn.bind(on_release=lambda x: (self.actualizar_desde_correo(), self.toggle_menu()))
            elif metodo == 'alertas':
                btn.bind(on_release=lambda x: (setattr(self.manager, 'current', 'alertas'), self.toggle_menu()))
            grid.add_widget(btn)

    def toggle_menu(self):
        drawer = self.ids.drawer
        overlay = self.ids.drawer_overlay
        if self._menu_abierto:
            anim = Animation(opacity=0, duration=0.15) + Animation(x=-drawer.width, duration=0.2)
            anim.start(drawer)
            Animation(opacity=0, duration=0.15).start(overlay)
            self._menu_abierto = False
        else:
            self._construir_menu()
            drawer.x = -drawer.width
            drawer.opacity = 1
            anim = Animation(x=0, duration=0.2)
            anim.start(drawer)
            Animation(opacity=1, duration=0.15).start(overlay)
            self._menu_abierto = True

    def on_touch_down(self, touch):
        if self._menu_abierto and not self.ids.drawer.collide_point(*touch.pos):
            self.toggle_menu()
            return True
        return super().on_touch_down(touch)

    def actualizar_spinners(self) -> None:
        try:
            nombres    = sorted({str(r[0]).upper() for r in db_query("SELECT DISTINCT nombre FROM movimientos") if r[0]})
            materiales = sorted({str(r[0]).upper() for r in db_query("SELECT DISTINCT material FROM movimientos") if r[0]})
            self.ids.responsable_spinner.values = nombres
            self.ids.producto_spinner.values    = materiales
        except Exception as e:
            logger.error("Error actualizando spinners: %s", e)

    def _verificar_alertas_silencioso(self) -> None:
        try:
            alertas = obtener_alertas_activas()
            if alertas:
                n = len(alertas)
                self.ids.info.text = f"[color=#FF0044]{n} alerta{'s' if n > 1 else ''} de stock[/color]"
        except Exception as e:
            logger.error("Error verificando alertas: %s", e)

    def _actualizar_dashboard(self) -> None:
        try:
            hora = datetime.now().hour
            if hora < 7:
                saludo = "Buenas noches"
            elif hora < 12:
                saludo = "Buenos dias"
            elif hora < 18:
                saludo = "Buenas tardes"
            else:
                saludo = "Buenas noches"
            self.ids.lbl_saludo.text = saludo

            meses = ['enero','febrero','marzo','abril','mayo','junio',
                     'julio','agosto','septiembre','octubre','noviembre','diciembre']
            ahora = datetime.now()
            self.ids.lbl_fecha_hoy.text = f"{ahora.day} de {meses[ahora.month-1]} {ahora.year}  *  {ahora.strftime('%H:%M')}"

            total_mat = int(db_query("SELECT COUNT(DISTINCT material) FROM movimientos", fetchall=False)[0] or 0)
            self.ids.stat_materiales.text = str(total_mat)

            hoy = ahora.strftime("%d/%m/%Y")
            movs_hoy = int(db_query("SELECT COUNT(*) FROM movimientos WHERE fecha LIKE ? || '%'", (hoy,), fetchall=False)[0] or 0)
            self.ids.stat_movs_hoy.text = str(movs_hoy)

            alertas = obtener_alertas_activas()
            self.ids.stat_alertas.text = str(len(alertas))

            prestamos_activos = obtener_equipos_en_prestamo()
            self.ids.stat_pendientes.text = str(len(prestamos_activos))

            try:
                size_kb = os.path.getsize(DB_PATH) / 1024
                self.ids.lbl_resumen_db.text = f"BD: {size_kb:.0f} KB"
            except Exception:
                pass
        except Exception as e:
            logger.error("Error actualizando dashboard: %s", e)

    def _cargar_actividad_reciente(self) -> None:
        try:
            movs = db_query(
                "SELECT nombre, material, cantidad, tipo, fecha FROM movimientos ORDER BY id DESC LIMIT 5"
            )
            texto = "\n".join(
                f"{'▲' if t == 'ENTRADA' else '▼'} {m} x{c} - {n} {str(f)[:16] if f else ''}"
                for n, m, c, t, f in movs
            ) if movs else "Sin movimientos registrados"
            self.ids.info.text = f"[color=#5A6A7A]{texto}[/color]"
        except Exception as e:
            logger.error("Error cargando actividad: %s", e)

    def mostrar_alertas(self) -> None:
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
            elif t == "ENTRADA" and key in actualmente_fuera:
                actualmente_fuera[key][3] -= float(c)
                if actualmente_fuera[key][3] <= 0:
                    del actualmente_fuera[key]
        pendientes = list(actualmente_fuera.values())
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        pop = Popup(title=f"MATERIALES SIN RETORNAR ({len(pendientes)})",
                    content=content, size_hint=(0.93, 0.82))
        if not pendientes:
            content.add_widget(Label(text="Todo en orden - ningun material pendiente de retorno.",
                                     color=get_color_from_hex('#00D4FF'), halign='center'))
        else:
            sv = ScrollView()
            gl = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
            gl.bind(minimum_height=gl.setter('height'))
            for item in sorted(pendientes, key=lambda x: x[0]):
                n, m, s, c, _, f, notas = item
                tiene_notas = bool(notas and notas.strip())
                altura = dp(110) if tiene_notas else dp(80)
                card = crear_tarjeta(altura, '#0D1B2A')
                card.add_widget(Label(
                    text=f"[b]{m}[/b]  -  Responsable: [color=#FF0044]{n}[/color]",
                    markup=True, color=get_color_from_hex('#FF0044'),
                    size_hint_y=None, height=dp(24),
                    halign='left', text_size=(Window.width * 0.82, None)
                ))
                card.add_widget(Label(
                    text=f"Cantidad fuera: [b]{round(c,2)}[/b]  |  SKU: {s or 'N/A'}  |  Salida: {f}",
                    color=get_color_from_hex('#FF0044'), font_size='12sp',
                    size_hint_y=None, height=dp(20),
                    halign='left', text_size=(Window.width * 0.82, None)
                ))
                if tiene_notas:
                    card.add_widget(Label(
                        text=f"[color=#5A6A7A]Notas:[/color] [color=#00D4FF]{notas}[/color]",
                        markup=True, font_size='11sp',
                        size_hint_y=None, height=dp(22),
                        halign='left', text_size=(Window.width * 0.82, None)
                    ))
                gl.add_widget(card)
            sv.add_widget(gl)
            content.add_widget(sv)
        content.add_widget(Button(text="CERRAR", size_hint_y=None, height=dp(45),
                                   background_color=get_color_from_hex('#334155'),
                                   on_release=pop.dismiss))
        pop.open()

    def procesar(self, tipo, r=None, p=None, c=None, s="N/A", desde_retorno=False) -> None:
        resp = (r
                or self.ids.nombre_nuevo.text.strip().upper()
                or (self.ids.responsable_spinner.text
                    if self.ids.responsable_spinner.text != "SELECCIONAR RESPONSABLE" else ""))
        prod = (p
                or self.ids.producto_nuevo.text.strip().upper()
                or (self.ids.producto_spinner.text
                    if self.ids.producto_spinner.text != "SELECCIONAR MATERIAL" else ""))
        cant_str = str(c) if c else self.ids.cantidad.text.strip()

        if not all([resp, prod, cant_str]):
            self.ids.info.text = "[color=#FF0044]Responsable, material y cantidad son obligatorios[/color]"
            return
        try:
            val = float(cant_str)
            if val <= 0:
                self.ids.info.text = "[color=#FF0044]La cantidad debe ser mayor a 0[/color]"
                return
            es_inventario = resp.upper() == "INVENTARIO"
            if tipo == "ENTRADA" and not es_inventario and not desde_retorno:
                self.ids.info.text = "[color=#FF0044]Solo INVENTARIO puede registrar entradas[/color]"
                return
            _, actual = obtener_stock_material(prod)
            if tipo == "SALIDA":
                if actual <= 0:
                    self.ids.info.text = f"[color=#FF0044]SIN STOCK DISPONIBLE: {prod}[/color]"
                    return
                if val > actual:
                    self.ids.info.text = f"[color=#FF0044]SOLO HAY {actual} UNIDADES DISPONIBLES[/color]"
                    return
            f_str     = self.ids.f_m.text.strip() or datetime.now().strftime("%d/%m/%Y %H:%M")
            dias      = self.ids.d_p.text.strip() or 0
            notas     = self.ids.notas.text.strip()
            ubicacion = self.ids.ubicacion.text.strip().upper()
            sku_val   = s if s != "N/A" else self.ids.sku.text.strip()
            fijo, actual2 = obtener_stock_material(prod)
            nuevo_st = round(actual2 + (val if tipo == "ENTRADA" else -val), 4)

            last_id = db_execute(
                "INSERT INTO movimientos (nombre,material,sku,cantidad,tipo,fecha,stock_registro,dias,retorno,notas,ubicacion) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (resp, prod, sku_val, val, tipo, f_str, nuevo_st, dias, "N/A", notas, ubicacion)
            )
            self._ultimo_mov_id = last_id
            self._ultimo_mov_tipo = tipo
            try:
                self.ids.btn_deshacer.disabled = False
            except Exception:
                pass
            if resp.upper() == "INVENTARIO" and self.ids.c_l.active:
                db_execute(
                    "INSERT INTO limpieza (material,cantidad,estado,fecha,notas) VALUES (?,?,?,?,?)",
                    (prod, val, "SUCIO", f_str, notas)
                )
            log_auditoria(f"MOV_{tipo}", f"{resp} | {prod} | x{val} | {f_str}")
            icono = "▲" if tipo == "ENTRADA" else "▼"
            self.ids.info.text = f"[color=#00D4FF] {icono} {tipo} REGISTRADA - {prod} x{val}[/color]"
            self.actualizar_spinners()
            self._actualizar_dashboard()
        except ValueError:
            self.ids.info.text = "[color=#FF0044] CANTIDAD INVALIDA[/color]"
        except sqlite3.Error as e:
            self.ids.info.text = f"[color=#FF0044] ERROR BD: {e}[/color]"

    def limpiar_campos(self) -> None:
        for field in ['nombre_nuevo','producto_nuevo','sku','cantidad','d_p','f_m','notas','ubicacion']:
            self.ids[field].text = ""
        self.ids.responsable_spinner.text = "SELECCIONAR RESPONSABLE"
        self.ids.producto_spinner.text    = "SELECCIONAR MATERIAL"
        self.ids.c_l.active = False

    def deshacer_ultimo(self):
        if not self._ultimo_mov_id:
            return
        try:
            db_execute("DELETE FROM movimientos WHERE id = ?", (self._ultimo_mov_id,))
            log_auditoria("DESHACER", f"Movimiento #{self._ultimo_mov_id} eliminado")
            self.ids.info.text = f"[color=#FF0044] Deshecho: ultimo movimiento eliminado[/color]"
            self._ultimo_mov_id = None
            self._ultimo_mov_tipo = None
            self.ids.btn_deshacer.disabled = True
            self.actualizar_spinners()
            self._actualizar_dashboard()
        except Exception as e:
            self.ids.info.text = f"[color=#FF0044] Error al deshacer: {e}[/color]"
        gc.collect()

    def salida_por_categoria(self):
        from kivy.uix.gridlayout import GridLayout
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.spinner import Spinner
        from kivy.uix.textinput import TextInput as TI

        categorias = db_query("SELECT id, nombre FROM categorias ORDER BY nombre")
        if not categorias:
            self.ids.info.text = "[color=#FF0044]Crea categorias primero en CATEGORIAS[/color]"
            return
        if len(categorias) == 1:
            self._mostrar_items_categoria(categorias[0][0], categorias[0][1])
            return
        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(15))
        pop = Popup(title="SELECCIONAR CATEGORIA", content=content, size_hint=(0.85, 0.35))
        spinner = Spinner(text=categorias[0][1], values=[c[1] for c in categorias],
                          size_hint_y=None, height=dp(48))
        content.add_widget(spinner)
        def continuar(btn):
            for cid, cnom in categorias:
                if cnom == spinner.text:
                    pop.dismiss()
                    self._mostrar_items_categoria(cid, cnom)
                    break
        btn = Button(text="CONTINUAR", size_hint_y=None, height=dp(50),
                     background_color=get_color_from_hex('#0066FF'), on_release=continuar)
        content.add_widget(btn)
        pop.open()

    def _mostrar_items_categoria(self, cid, cnom):
        from kivy.uix.gridlayout import GridLayout as GL
        from kivy.uix.scrollview import ScrollView as SV
        from kivy.uix.textinput import TextInput as TI

        items = db_query("SELECT id, nombre FROM categoria_items WHERE categoria_id = ? ORDER BY nombre", (cid,))
        if not items:
            self.ids.info.text = f"[color=#FF0044]La categoria {cnom} no tiene items[/color]"
            return
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(12))
        pop = Popup(title=f"SALIDA: {cnom}", content=content, size_hint=(0.92, 0.82))

        resp = self.ids.nombre_nuevo.text.strip().upper() or self.ids.responsable_spinner.text
        if not resp or resp == "SELECCIONAR RESPONSABLE":
            content.add_widget(Label(
                text="Primero selecciona un responsable arriba",
                color=get_color_from_hex('#FF0044'), size_hint_y=None, height=dp(30)))
            content.add_widget(Button(text="CERRAR", size_hint_y=None, height=dp(44),
                                       background_color=get_color_from_hex('#334155'),
                                       on_release=pop.dismiss))
            pop.open()
            return

        inputs = {}
        sv = SV()
        gl = GL(cols=1, size_hint_y=None, spacing=dp(4))
        gl.bind(minimum_height=gl.setter('height'))

        for it in items:
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
            row.add_widget(Label(
                text=it[1],
                color=get_color_from_hex('#E8EAED'),
                font_size='13sp', halign='left',
                text_size=(Window.width * 0.5, None),
                size_hint_x=0.6))
            inp = TI(hint_text="0", input_filter='float', multiline=False,
                     size_hint_x=0.25, font_size='14sp')
            inputs[it[0]] = (it[1], inp)
            row.add_widget(inp)
            gl.add_widget(row)

        sv.add_widget(gl)
        content.add_widget(sv)

        def confirmar(btn):
            registrados = 0
            fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
            notas = self.ids.notas.text.strip()
            for iid, (inom, inp) in inputs.items():
                val_str = inp.text.strip()
                if not val_str:
                    continue
                try:
                    val = float(val_str)
                except ValueError:
                    continue
                if val <= 0:
                    continue
                from services.inventario import obtener_stock_material
                _, actual = obtener_stock_material(inom)
                if actual <= 0:
                    continue
                if val > actual:
                    val = actual
                _, actual2 = obtener_stock_material(inom)
                nuevo_st = round(actual2 - val, 4)
                db_execute(
                    "INSERT INTO movimientos (nombre,material,sku,cantidad,tipo,fecha,stock_registro,dias,retorno,notas,ubicacion,categoria_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (resp, inom, "", val, "SALIDA", fecha, nuevo_st, 0, "N/A", notas, "", cid)
                )
                registrados += 1
            pop.dismiss()
            if registrados > 0:
                self.ids.info.text = f"[color=#00D4FF] Salida x{registrados} items de {cnom}[/color]"
                self.actualizar_spinners()
                self._actualizar_dashboard()

        btn = Button(text=f"CONFIRMAR SALIDA", size_hint_y=None, height=dp(48),
                     background_color=get_color_from_hex('#FF0044'), on_release=confirmar)
        content.add_widget(btn)
        pop.open()

    def enviar_correo(self) -> None:
        self.ids.info.text = "Preparando Excel..."
        threading.Thread(target=self._enviar_correo_worker, daemon=True).start()

    def _enviar_correo_worker(self) -> None:
        exito, msg = enviar_reporte_por_correo()
        if not exito:
            logger.error("Error al enviar correo: %s", msg)
        Clock.schedule_once(lambda dt: setattr(
            self.ids.info, 'text',
            f"[color=#00D4FF]ENVIADO EXITOSAMENTE[/color]" if exito else f"[color=#FF0044]ERROR: {msg}[/color]"
        ))

    def mostrar_opciones_exportar(self):
        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(15))
        pop = Popup(title="EXPORTAR", content=content, size_hint=(0.8, 0.35))
        btn_pdf = Button(text="EXPORTAR PDF", font_size='15sp', bold=True,
                         background_color=get_color_from_hex('#0066FF'),
                         size_hint_y=None, height=dp(52))
        btn_pdf.bind(on_release=lambda x: (pop.dismiss(), self.exportar_pdf()))
        btn_excel = Button(text="ENVIAR POR CORREO (EXCEL)", font_size='13sp',
                           background_color=get_color_from_hex('#0066FF'),
                           size_hint_y=None, height=dp(52))
        btn_excel.bind(on_release=lambda x: (pop.dismiss(), self.enviar_correo()))
        content.add_widget(btn_pdf)
        content.add_widget(btn_excel)
        content.add_widget(Button(text="CANCELAR", size_hint_y=None, height=dp(40),
                                   background_color=get_color_from_hex('#334155'),
                                   on_release=pop.dismiss))
        pop.open()

    def hacer_backup(self) -> None:
        self.ids.info.text = " Generando backup..."
        threading.Thread(target=self._backup_worker, daemon=True).start()

    def exportar_pdf(self) -> None:
        self.ids.info.text = " Generando PDF..."
        threading.Thread(target=self._pdf_worker, daemon=True).start()

    def _pdf_worker(self):
        try:
            from services.reporting import generar_pdf
            ruta = generar_pdf()
            from widgets.toast import Toast
            Clock.schedule_once(lambda dt: Toast.show(f"PDF guardado", '#0066FF', 4))
            Clock.schedule_once(lambda dt: setattr(self.ids.info, 'text',
                                                   f"[color=#00D4FF]PDF: {os.path.basename(ruta)}[/color]"))
        except Exception as e:
            logger.error("Error PDF: %s", e)
            Clock.schedule_once(lambda dt, err=str(e): setattr(
                self.ids.info, 'text', f"[color=#FF0044]Error PDF: {err}[/color]"))

    def _backup_worker(self) -> None:
        try:
            nombre = ruta_exportacion(f"backup_inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            generar_excel(nombre)
            log_auditoria("BACKUP", nombre)
            Clock.schedule_once(lambda dt: setattr(self.ids.info, 'text',
                                                   f"[color=#00D4FF]Backup guardado en:\n{nombre}[/color]"))
        except Exception as e:
            logger.error("Error backup: %s", e)
            Clock.schedule_once(lambda dt: setattr(self.ids.info, 'text',
                                                   f"[color=#FF0044]Error backup: {e}[/color]"))

    def actualizar_desde_correo(self) -> None:
        self._popup_correo = self._crear_popup_progreso()
        self._popup_correo.open()
        actualizador = ActualizadorCorreo(
            callback_progreso=self._actualizar_progreso_correo,
            callback_fin=self._finalizar_actualizacion_correo,
        )
        actualizador.ejecutar()

    def _crear_popup_progreso(self):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(12))
        pop = Popup(title="Actualizando desde correo...", content=content,
                    size_hint=(0.92, 0.55), auto_dismiss=False)
        self._lbl_progreso = Label(
            text="Iniciando...", color=get_color_from_hex('#00D4FF'),
            halign='center', font_size='14sp',
            text_size=(Window.width * 0.85, None),
        )
        content.add_widget(self._lbl_progreso)
        btn_cerrar = Button(
            text="Procesando... (toca para cerrar si ya termino)",
            size_hint_y=None, height=dp(46),
            background_color=get_color_from_hex('#334155'),
        )
        btn_cerrar.bind(on_release=pop.dismiss)
        content.add_widget(btn_cerrar)
        self._btn_cerrar_popup = btn_cerrar
        return pop

    def _actualizar_progreso_correo(self, texto):
        try:
            self._lbl_progreso.text = texto
        except Exception:
            pass

    def _finalizar_actualizacion_correo(self, exito, datos):
        try:
            self._popup_correo.dismiss()
        except Exception:
            pass
        if exito:
            self._mostrar_resultado_correo(datos)
            self.actualizar_spinners()
        else:
            self._mostrar_error_correo(datos.get("error", "Error desconocido"))

    def _mostrar_resultado_correo(self, datos):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        pop = Popup(title="Inventario actualizado", content=content, size_hint=(0.92, 0.72))
        card_ok = crear_tarjeta(dp(60), '#0D1B2A')
        card_ok.add_widget(Label(
            text="[b][color=#00D4FF]ACTUALIZACION COMPLETADA[/color][/b]",
            markup=True, font_size='15sp',
        ))
        content.add_widget(card_ok)
        if datos.get("de") or datos.get("asunto"):
            card_origen = crear_tarjeta(dp(80), '#0D1B2A')
            card_origen.add_widget(Label(
                text=f"De: {datos.get('de', 'N/A')[:50]}",
                color=get_color_from_hex('#5A6A7A'), font_size='12sp',
            ))
            card_origen.add_widget(Label(
                text=f"Asunto: {datos.get('asunto', 'N/A')[:50]}",
                color=get_color_from_hex('#5A6A7A'), font_size='12sp',
            ))
            content.add_widget(card_origen)
        card_stats = crear_tarjeta(dp(110), '#0D1B2A')
        card_stats.add_widget(Label(
            text="RESULTADOS DE LA IMPORTACION",
            color=get_color_from_hex('#00D4FF'), font_size='12sp', bold=True,
        ))
        card_stats.add_widget(Label(
            text=f"[b][color=#00D4FF]Insertados: {datos.get('insertados', 0)}[/color][/b]",
            markup=True, font_size='16sp',
        ))
        card_stats.add_widget(Label(
            text=f"Omitidos: {datos.get('omitidos', 0)}   Errores: {datos.get('errores', 0)}",
            color=get_color_from_hex('#5A6A7A'), font_size='13sp',
        ))
        content.add_widget(card_stats)
        card_archivo = crear_tarjeta(dp(65), '#0D1B2A')
        card_archivo.add_widget(Label(
            text=f"Archivo: {datos.get('archivo', 'N/A')[:45]}",
            color=get_color_from_hex('#E8EAED'), font_size='12sp',
        ))
        card_archivo.add_widget(Label(
            text=f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            color=get_color_from_hex('#5A6A7A'), font_size='11sp',
        ))
        content.add_widget(card_archivo)
        content.add_widget(Button(
            text="ENTENDIDO", size_hint_y=None, height=dp(48),
            background_color=get_color_from_hex('#0066FF'), on_release=pop.dismiss,
        ))
        self.ids.info.text = f"[color=#00D4FF]Actualizado desde correo: +{datos.get('insertados', 0)} registros[/color]"
        pop.open()

    def _mostrar_error_correo(self, mensaje_error):
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        pop = Popup(title="Error al actualizar desde correo", content=content, size_hint=(0.92, 0.65))
        sv = ScrollView()
        lbl = Label(
            text=mensaje_error, color=get_color_from_hex('#FF0044'),
            halign='center', font_size='13sp', size_hint_y=None,
            text_size=(Window.width * 0.82, None),
        )
        lbl.bind(texture_size=lbl.setter('size'))
        sv.add_widget(lbl)
        content.add_widget(sv)
        card_tip = crear_tarjeta(dp(130), '#0D1B2A')
        card_tip.add_widget(Label(
            text="POSIBLES SOLUCIONES",
            color=get_color_from_hex('#FF0044'), bold=True, font_size='13sp',
        ))
        card_tip.add_widget(Label(
            text="* Activa IMAP en Gmail -> Configuracion -> Ver toda la config -> Reenvio e IMAP",
            color=get_color_from_hex('#5A6A7A'), font_size='11sp', halign='center',
            text_size=(Window.width * 0.75, None),
        ))
        card_tip.add_widget(Label(
            text="* Usa una contrasena de aplicacion (no la contrasena normal)",
            color=get_color_from_hex('#5A6A7A'), font_size='11sp', halign='center',
            text_size=(Window.width * 0.75, None),
        ))
        card_tip.add_widget(Label(
            text="* Verifica que el Excel adjunto este en la bandeja de entrada",
            color=get_color_from_hex('#5A6A7A'), font_size='11sp', halign='center',
            text_size=(Window.width * 0.75, None),
        ))
        content.add_widget(card_tip)
        content.add_widget(Button(
            text="CERRAR", size_hint_y=None, height=dp(46),
            background_color=get_color_from_hex('#334155'), on_release=pop.dismiss,
        ))
        self.ids.info.text = "[color=#FF0044]Error al actualizar desde correo[/color]"
        pop.open()
