from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from database.connection import db_query
from widgets.tarjeta import crear_tarjeta
from widgets.charts import BarraHorizontal, GraficoTendencia
from services.inventario import obtener_alertas_activas, obtener_reporte_estadisticas
from logging_config import logger


class EstadisticasScreen(Screen):
    def on_enter(self):
        self.cargar_estadisticas()

    def _crear_seccion(self, titulo, color_titulo='#00D4FF'):
        return Label(
            text=f"\n{titulo}", font_size='13sp', bold=True,
            color=get_color_from_hex(color_titulo),
            size_hint_y=None, height=dp(35),
            halign='left', valign='bottom',
            text_size=(Window.width * 0.85, None),
        )

    def _crear_barra(self, label, valor, maximo, color='#00D4FF'):
        return BarraHorizontal(label, valor, maximo, color)

    def cargar_estadisticas(self) -> None:
        try:
            self.ids.stats_container.clear_widgets()
            stats   = obtener_reporte_estadisticas()
            alertas = obtener_alertas_activas()

            self.ids.stats_container.add_widget(self._crear_seccion("RESUMEN GENERAL", '#FF0044'))

            kpis = [
                ("Total Movimientos",    stats["total_movimientos"], '#00D4FF'),
                ("Entradas",             stats["entradas"],          '#00D4FF'),
                ("Salidas",              stats["salidas"],           '#FF0044'),
                ("Materiales",           stats["materiales"],        '#00D4FF'),
                ("Responsables",         stats["responsables"],      '#FF0044'),
                ("Movs. 7 dias",          stats["movs_7dias"],        '#00D4FF'),
                ("Movs. 30 dias",         stats["movs_30dias"],       '#00D4FF'),
                ("Prom. cantidad",       stats["prom_cant"],         '#FF0044'),
            ]
            gl = GridLayout(cols=2, size_hint_y=None, spacing=dp(8))
            gl.bind(minimum_height=gl.setter('height'))
            for label, valor, color in kpis:
                card = crear_tarjeta(dp(80))
                card.add_widget(Label(text=label, font_size='11sp',
                                      color=get_color_from_hex('#5A6A7A')))
                card.add_widget(Label(
                    text=f"[b][color={color}]{valor}[/color][/b]",
                    markup=True, font_size='22sp'))
                gl.add_widget(card)
            self.ids.stats_container.add_widget(gl)

            self.ids.stats_container.add_widget(self._crear_seccion("VOLUMENES MOVIDOS"))
            card_vol = crear_tarjeta(dp(130))
            card_vol.add_widget(Label(
                text=f"Cantidad total entrada:  [b][color=#00D4FF]{stats['vol_entradas']}[/color][/b]",
                markup=True, font_size='13sp', color=get_color_from_hex('#E8EAED'),
                size_hint_y=None, height=dp(28), halign='left', text_size=(Window.width*0.8, None)
            ))
            card_vol.add_widget(Label(
                text=f"Cantidad total salida:   [b][color=#FF0044]{stats['vol_salidas']}[/color][/b]",
                markup=True, font_size='13sp', color=get_color_from_hex('#E8EAED'),
                size_hint_y=None, height=dp(28), halign='left', text_size=(Window.width*0.8, None)
            ))
            balance = stats['vol_entradas'] - stats['vol_salidas']
            bal_color = '#00D4FF' if balance >= 0 else '#FF0044'
            card_vol.add_widget(Label(
                text=f"Balance neto:  [b][color={bal_color}]{round(balance, 2)}[/color][/b]",
                markup=True, font_size='14sp', color=get_color_from_hex('#E8EAED'),
                size_hint_y=None, height=dp(30), halign='left', text_size=(Window.width*0.8, None)
            ))
            ratio = round(stats['entradas'] / max(stats['salidas'], 1), 2)
            card_vol.add_widget(Label(
                text=f"Ratio E/S:  [b][color=#00D4FF]{ratio}[/color][/b]",
                markup=True, font_size='12sp', color=get_color_from_hex('#5A6A7A'),
                size_hint_y=None, height=dp(24), halign='left', text_size=(Window.width*0.8, None)
            ))
            self.ids.stats_container.add_widget(card_vol)

            valor_inv = db_query(
                "SELECT COALESCE(SUM(cantidad * costo_unitario), 0), COALESCE(SUM(cantidad * precio_venta), 0) FROM movimientos WHERE tipo='ENTRADA'",
                fetchall=False
            )
            if valor_inv:
                costo_total, venta_total = valor_inv
                self.ids.stats_container.add_widget(self._crear_seccion("VALOR DEL INVENTARIO", '#00D4FF'))
                card_val = crear_tarjeta(dp(70), '#0D1B2A')
                card_val.add_widget(Label(
                    text=f"Costo total: [b][color=#00D4FF]$ {round(costo_total or 0, 2)}[/color][/b]",
                    markup=True, font_size='13sp', color=get_color_from_hex('#E8EAED'),
                    size_hint_y=None, height=dp(26), halign='left',
                    text_size=(Window.width*0.8, None)))
                margen = (venta_total or 0) - (costo_total or 0)
                color_margen = '#00D4FF' if margen >= 0 else '#FF0044'
                card_val.add_widget(Label(
                    text=f"Valor venta estimado: [b][color={color_margen}]$ {round(venta_total or 0, 2)}[/color][/b]",
                    markup=True, font_size='13sp', color=get_color_from_hex('#E8EAED'),
                    size_hint_y=None, height=dp(26), halign='left',
                    text_size=(Window.width*0.8, None)))
                self.ids.stats_container.add_widget(card_val)

            self.ids.stats_container.add_widget(self._crear_seccion("TENDENCIA 7 DIAS"))
            card_trend = crear_tarjeta(dp(90))
            max_7d = max(stats['ent_7d'], stats['sal_7d'], 1)
            card_trend.add_widget(self._crear_barra("Entradas", stats['ent_7d'], max_7d, '#00D4FF'))
            card_trend.add_widget(self._crear_barra("Salidas", stats['sal_7d'], max_7d, '#FF0044'))
            self.ids.stats_container.add_widget(card_trend)

            chart = GraficoTendencia()
            datos = db_query(
                "SELECT COUNT(*), strftime('%w', fecha) FROM movimientos WHERE fecha >= date('now','-7 days') GROUP BY strftime('%w', fecha) ORDER BY 2",
                fetchall=False
            )
            if datos:
                vals = [0]*7
                for cnt, dia in datos:
                    vals[int(dia)] = cnt
                chart.mostrar(vals, '#00D4FF')
                self.ids.stats_container.add_widget(chart)

            if stats['top5_materiales']:
                self.ids.stats_container.add_widget(self._crear_seccion("TOP 5 MATERIALES", '#00D4FF'))
                max_cnt = stats['top5_materiales'][0][1] if stats['top5_materiales'] else 1
                card_top = crear_tarjeta(dp(40 * len(stats['top5_materiales']) + 10))
                for i, (m, cnt) in enumerate(stats['top5_materiales'], 1):
                    colors = ['#FF0044', '#5A6A7A', '#5A6A7A', '#5A6A7A', '#5A6A7A']
                    prefix = '*' if i == 1 else '-'
                    card_top.add_widget(self._crear_barra(f"{prefix} {m}", cnt, max_cnt, colors[i-1]))
                self.ids.stats_container.add_widget(card_top)

            if stats['top5_responsables']:
                self.ids.stats_container.add_widget(self._crear_seccion("TOP 5 RESPONSABLES", '#FF0044'))
                max_r = stats['top5_responsables'][0][1] if stats['top5_responsables'] else 1
                card_resp = crear_tarjeta(dp(40 * len(stats['top5_responsables']) + 10))
                for i, (n, cnt) in enumerate(stats['top5_responsables'], 1):
                    card_resp.add_widget(self._crear_barra(f"{i}. {n}", cnt, max_r, '#FF0044'))
                self.ids.stats_container.add_widget(card_resp)

            if stats["material_top"] != "N/A":
                card = crear_tarjeta(dp(70), '#0D1B2A')
                card.add_widget(Label(text="Material mas activo",
                                      color=get_color_from_hex('#00D4FF'), font_size='12sp'))
                card.add_widget(Label(text=f"[b]{stats['material_top']}[/b]",
                                      markup=True, font_size='18sp',
                                      color=get_color_from_hex('#E8EAED')))
                self.ids.stats_container.add_widget(card)

            if alertas:
                self.ids.stats_container.add_widget(self._crear_seccion(
                    f"ALERTAS DE STOCK ({len(alertas)})", '#FF0044'))
                card = crear_tarjeta(dp(30 + len(alertas)*36), '#0D1B2A')
                for mat, disp, minimo in alertas:
                    card.add_widget(Label(
                        text=f"  {mat}:  {disp}  (min: {minimo})",
                        font_size='13sp', color=get_color_from_hex('#FF0044'),
                        size_hint_y=None, height=dp(32),
                        halign='left', valign='middle',
                        text_size=(Window.width*0.8, None),
                        padding=(dp(4), dp(2))
                    ))
                self.ids.stats_container.add_widget(card)

            if stats['total_limpieza'] > 0:
                self.ids.stats_container.add_widget(self._crear_seccion("LIMPIEZA", '#00D4FF'))
                card_limp = crear_tarjeta(dp(90))
                max_l = max(stats['limpios'], stats['sucios'], 1)
                card_limp.add_widget(self._crear_barra("Limpios", stats['limpios'], max_l, '#00D4FF'))
                card_limp.add_widget(self._crear_barra("Sucios", stats['sucios'], max_l, '#FF0044'))
                self.ids.stats_container.add_widget(card_limp)

            if stats['mats_inactivos']:
                self.ids.stats_container.add_widget(self._crear_seccion(
                    f"MATERIALES INACTIVOS (+30d):  {len(stats['mats_inactivos'])}", '#5A6A7A'))
                card_inact = crear_tarjeta(dp(20 + len(stats['mats_inactivos'])*24))
                for m in stats['mats_inactivos']:
                    card_inact.add_widget(Label(
                        text=f"  {m}", font_size='11sp',
                        color=get_color_from_hex('#5A6A7A'),
                        size_hint_y=None, height=dp(22),
                        halign='left', text_size=(Window.width*0.8, None)
                    ))
                self.ids.stats_container.add_widget(card_inact)

            self.ids.stats_container.add_widget(self._crear_seccion("SISTEMA", '#5A6A7A'))
            card_sys = crear_tarjeta(dp(100))
            card_sys.add_widget(Label(
                text=f"Primer movimiento:  {stats['primer_mov']}",
                font_size='11sp', color=get_color_from_hex('#5A6A7A'),
                size_hint_y=None, height=dp(22), halign='left', text_size=(Window.width*0.8, None)
            ))
            card_sys.add_widget(Label(
                text=f"Ultimo movimiento:  {stats['ultimo_mov']}",
                font_size='11sp', color=get_color_from_hex('#5A6A7A'),
                size_hint_y=None, height=dp(22), halign='left', text_size=(Window.width*0.8, None)
            ))
            import os
            from config import DB_PATH
            try:
                size_kb = os.path.getsize(DB_PATH) / 1024
                card_sys.add_widget(Label(
                    text=f"Base de datos:  {size_kb:.1f} KB",
                    font_size='11sp', color=get_color_from_hex('#5A6A7A'),
                    size_hint_y=None, height=dp(22), halign='left', text_size=(Window.width*0.8, None)
                ))
            except Exception:
                pass
            from config import VERSION_ACTUAL
            card_sys.add_widget(Label(
                text=f"Version:  {VERSION_ACTUAL}",
                font_size='11sp', color=get_color_from_hex('#5A6A7A'),
                size_hint_y=None, height=dp(22), halign='left', text_size=(Window.width*0.8, None)
            ))
            self.ids.stats_container.add_widget(card_sys)
        except Exception as e:
            logger.error("Error cargando estadisticas: %s", e)
