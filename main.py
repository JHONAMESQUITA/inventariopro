import gc
import os
import sys
import threading

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.utils import platform

from config import DB_PATH, VERSION_ACTUAL
from logging_config import logger

from database.models import init_db
init_db(DB_PATH)
logger.info("Base de datos inicializada: %s", DB_PATH)

if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission
        from jnius import autoclass
        permisos = [Permission.INTERNET]
        Build = autoclass('android.os.Build$VERSION')
        if Build.SDK_INT < 29:
            permisos += [
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
            ]
        request_permissions(permisos)
    except Exception as e:
        logger.warning("Error configurando permisos Android: %s", e)

from kivy.core.window import Window
Window.softinput_mode = 'below_target'

KV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screens')
for kv_file in ['limpieza.kv', 'pendientes_filtros.kv',
                'stock_estadisticas.kv', 'ajustes_importar.kv',
                'auditoria.kv', 'alertas.kv',
                'categorias.kv', 'ubicaciones.kv',
                'gestion.kv',
                'valor.kv']:
    ruta = os.path.join(KV_DIR, kv_file)
    if os.path.exists(ruta):
        with open(ruta, 'r', encoding='utf-8') as f:
            Builder.load_string(f.read())
    else:
        ruta_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), kv_file)
        if os.path.exists(ruta_base):
            Builder.load_file(ruta_base)

from screens.inventario import InventarioScreen
from screens.limpieza import LimpiezaScreen
from screens.pendientes import PendientesScreen
from screens.filtros import FiltroScreen
from screens.stock import StockScreen
from screens.estadisticas import EstadisticasScreen
from screens.ajustes import AjustesScreen
from screens.importar import ImportarExcelScreen
from screens.auditoria import AuditoriaScreen
from screens.alertas import AlertasScreen
from screens.categorias import CategoriasScreen
from screens.ubicaciones import UbicacionesScreen
from screens.gestion import GestionScreen
from screens.valor import ValorScreen


class InventarioApp(App):
    def build(self):
        self.title = "Gestion Inventario PRO v" + VERSION_ACTUAL
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(InventarioScreen(name='inventario'))
        sm.add_widget(LimpiezaScreen(name='limpieza'))
        sm.add_widget(PendientesScreen(name='pendientes'))
        sm.add_widget(FiltroScreen(name='filtros'))
        sm.add_widget(StockScreen(name='stock'))
        sm.add_widget(EstadisticasScreen(name='estadisticas'))
        sm.add_widget(AjustesScreen(name='ajustes'))
        sm.add_widget(ImportarExcelScreen(name='importar'))
        sm.add_widget(AuditoriaScreen(name='auditoria'))
        sm.add_widget(AlertasScreen(name='alertas'))
        sm.add_widget(CategoriasScreen(name='categorias'))
        sm.add_widget(UbicacionesScreen(name='ubicaciones'))
        sm.add_widget(GestionScreen(name='gestion'))
        sm.add_widget(ValorScreen(name='valor'))
        self._iniciar_auto_actualizacion()
        self._iniciar_scheduler()
        return sm

    def _iniciar_auto_actualizacion(self):
        Clock.schedule_once(lambda dt: self._auto_check(None), 2)
        Clock.schedule_interval(self._auto_check, 30)

    def _auto_check(self, dt):
        threading.Thread(target=self._auto_worker, daemon=True).start()
        threading.Thread(target=self._enviar_sync, daemon=True).start()

    def _auto_worker(self):
        try:
            from services.correo import AutoActualizador
            actualizador = AutoActualizador(callback_fin=self._auto_fin)
            actualizador.ejecutar()
        except Exception:
            pass

    def _auto_fin(self, exito, datos):
        if exito and datos.get("importados", 0) > 0:
            n = datos["importados"]
            Clock.schedule_once(lambda dt, cant=n: self._notificar_actualizacion(cant))

    def _notificar_actualizacion(self, cant):
        try:
            inv = self.root.get_screen('inventario')
            inv.ids.info.text = f"[color=#10B981]Auto-actualizado: +{cant} registros[/color]"
            inv.actualizar_spinners()
            inv._actualizar_dashboard()
            inv._verificar_alertas_silencioso()
            self._enviar_sync()
        except Exception:
            pass

    def _enviar_sync(self):
        try:
            from services.correo import enviar_sync_email
            enviar_sync_email()
        except Exception:
            pass

    def on_pause(self):
        return True

    def _iniciar_scheduler(self):
        from services.scheduler import ProgramadorTareas
        self._scheduler = ProgramadorTareas(self)
        self._scheduler.iniciar()

    def on_start(self):
        from kivy.core.window import Window as KivyWindow
        KivyWindow.bind(on_key_down=self._on_key_down)

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if self.root.current != 'inventario':
            return
        ctrl = 'ctrl' in modifiers
        if ctrl and codepoint == 'e':
            self.root.get_screen('inventario').procesar("ENTRADA")
        elif ctrl and codepoint == 's':
            self.root.get_screen('inventario').procesar("SALIDA")
        elif ctrl and codepoint == 'b':
            self.root.get_screen('inventario').hacer_backup()

    def on_stop(self):
        gc.collect()


if __name__ == "__main__":
    try:
        InventarioApp().run()
    except Exception as e:
        logger.critical("Error fatal en main: %s", e, exc_info=True)
        try:
            ruta_err = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_main.txt")
            with open(ruta_err, "w", encoding="utf-8") as f:
                import traceback
                f.write("CRASH en __main__ " + str(__import__('datetime').datetime.now()) + "\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise
