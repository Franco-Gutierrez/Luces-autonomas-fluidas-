import requests
import csv
import os
import webbrowser
import urllib.parse
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider

# =====================================================================
# ⚙️ CONFIGURACIÓN GLOBAL Y MEMORIA LOCAL
# =====================================================================
ID_GOOGLE_SHEET = "13GiTsVRBGeKrDMjqCgT6f3-4u363xUPb_nDOiFangF4"
ARCHIVO_LOCAL = "progreso_kivy.csv"
DATOS_RUTAS = [] 
clinica_seleccionada = {}

# Variables dinámicas para el panel de ajustes interactivo
ALTO_BOTON_CONFIG = 180
TAMANO_LETRA_CONFIG = 16

def cargar_datos_iniciales(forzar_internet=False):
    global DATOS_RUTAS
    
    # Si NO se fuerza internet y el archivo local existe, lee del celular (Modo Ahorro/Offline)
    if not forzar_internet and os.path.exists(ARCHIVO_LOCAL):
        DATOS_RUTAS = []
        with open(ARCHIVO_LOCAL, mode='r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            for fila in lector:
                DATOS_RUTAS.append(fila)
        return

    # Si se presiona el botón o no hay archivo, va a la nube de Google
    try:
        enlace = f"https://docs.google.com/spreadsheets/d/{ID_GOOGLE_SHEET}/export?format=csv"
        respuesta = requests.get(enlace, timeout=8)
        if respuesta.status_code == 200:
            contenido = respuesta.text.splitlines()
            lector = csv.reader(contenido)
            lineas = list(lector)
            if lineas:
                cabeceras = [c.strip().upper() for c in lineas[0]]
                idx_nombre = next((i for i, c in enumerate(cabeceras) if "NOMBRE" in c or "POLICLINICO" in c), 0)
                idx_distrito = next((i for i, c in enumerate(cabeceras) if "DISTRITO" in c), 1)
                idx_ruta = next((i for i, c in enumerate(cabeceras) if "RUTA" in c), None)
                
                NUEVOS_DATOS = []
                for fila in lineas[1:]:
                    if len(fila) <= max(idx_nombre, idx_distrito):
                        continue
                    
                    # Filtro: Si la columna RUTA existe pero está vacía, se la salta
                    if idx_ruta is not None and idx_ruta < len(fila) and fila[idx_ruta].strip() == "":
                        continue
                    
                    nombre_clinica = fila[idx_nombre].strip()
                    distrito_clinica = fila[idx_distrito].strip()
                    
                    # Mantener observaciones si la clínica ya existía localmente
                    estado_antiguo = "PENDIENTE"
                    obs_antigua = ""
                    if os.path.exists(ARCHIVO_LOCAL):
                        for r in DATOS_RUTAS:
                            if r['nombre'] == nombre_clinica:
                                estado_antiguo = r['estado']
                                obs_antigua = r['obs']
                                break

                    NUEVOS_DATOS.append({
                        "nombre": nombre_clinica,
                        "distrito": distrito_clinica,
                        "estado": estado_antiguo,
                        "obs": obs_antigua
                    })
                
                DATOS_RUTAS = NUEVOS_DATOS
                guardar_progreso_local()
        else:
            raise Exception()
    except:
        # Respaldo si falla el internet por completo
        if not DATOS_RUTAS:
            DATOS_RUTAS = [
                {"nombre": "HAKAEM", "distrito": "VENTANILLA", "estado": "PENDIENTE", "obs": ""},
                {"nombre": "SEDIMEDIC", "distrito": "VENTANILLA", "estado": "PENDIENTE", "obs": ""},
                {"nombre": "SANTA LUZMILA", "distrito": "COMAS", "estado": "PENDIENTE", "obs": ""}
            ]

def guardar_progreso_local():
    with open(ARCHIVO_LOCAL, mode='w', encoding='utf-8', newline='') as f:
        if DATOS_RUTAS:
            escritor = csv.DictWriter(f, fieldnames=DATOS_RUTAS[0].keys())
            escritor.writeheader()
            escritor.writerows(DATOS_RUTAS)

# =====================================================================
# 🔒 PANTALLA 1: LOGIN
# =====================================================================
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=30, spacing=45)
        layout.add_widget(Label(text="🔒 [b]LOGISTICA V20[/b]", markup=True, font_size='20sp'))
        layout.add_widget(Label(text="Usuario:", font_size='25sp', size_hint_y=None, height=80))
        self.txt_usuario = TextInput(text="Franco", multiline=False, size_hint_y=None, height=85)
        layout.add_widget(self.txt_usuario)
        layout.add_widget(Label(text="PIN de Seguridad:", font_size='25sp', size_hint_y=None, height=150))
        self.txt_pin = TextInput(password=True, multiline=False, size_hint_y=None, height=85)
        layout.add_widget(self.txt_pin)
        
        btn_entrar = Button(text="INGRESAR A MIS RUTAS", background_color=(0.2, 0.6, 0.2, 1), font_size='20sp', size_hint_y=None, height=155)
        btn_entrar.bind(on_press=self.verificar_acceso)
        layout.add_widget(btn_entrar)
        
        self.lbl_error = Label(text="", color=(1, 0.6, 0, 1))
        layout.add_widget(self.lbl_error)
        layout.add_widget(Label()) 
        self.add_widget(layout)

    def verificar_acceso(self, instance):
        if self.txt_pin.text == "1234":
            cargar_datos_iniciales(forzar_internet=False)
            self.manager.get_screen('lista').cargar_lista_clinicas()
            self.manager.current = 'lista'
        else:
            self.lbl_error.text = "❌ PIN Incorrecto."

# =====================================================================
# 📋 PANTALLA 2: LISTA DE RUTAS (CON BOTÓN DE ACTUALIZACIÓN DE NUBE)
# =====================================================================
class ListaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout_principal = BoxLayout(orientation='vertical', padding=15, spacing=10)
        self.add_widget(self.layout_principal)

    def cargar_lista_clinicas(self):
        self.layout_principal.clear_widgets()
        
        # 1. Barra superior: Título + Botón Sincronizar Nube + Botón Ajustes
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=200, spacing=4)
        top_bar.add_widget(Label(text="[b]RUTAS[/b]", markup=True, font_size='18sp', size_hint_x=0.8))
        
        # 🔄 NUEVO: Botón para jalar al instante lo que agregues en Google Sheet
        btn_sync = Button(text="NUEVA LISTA", size_hint_x=None, width=450, background_color=(0, 0, 1, 1), font_size='16sp')
        btn_sync.bind(on_press=self.sincronizar_con_google_sheets)
        top_bar.add_widget(btn_sync)
        
        btn_config = Button(text="AJUSTES", size_hint_x=None, width=250, background_color=(1, 0.5, 0, 1), font_size='14sp')
        btn_config.bind(on_press=self.abrir_panel_ajustes)
        top_bar.add_widget(btn_config)
        
        self.layout_principal.add_widget(top_bar)
        
        # 2. Zona central con Scroll para las clínicas
        scroll = ScrollView()
        lista_botones = BoxLayout(orientation='vertical', spacing=15, size_hint_y=None)
        lista_botones.bind(minimum_height=lista_botones.setter('height'))
        
        for idx, item in enumerate(DATOS_RUTAS):
            color_btn = (0.2, 0.2, 0.2, 1) 
            if item['estado'] == 'COMPLETADO': color_btn = (0.1, 0.5, 0.2, 1)
            elif item['estado'] == 'INCIDENCIA': color_btn = (0.8, 0.4, 0.1, 1)
            
            texto_boton = f"[b]{idx+1}. {item['nombre']}[/b]\n📍 {item['distrito']}\n✨ Estado: {item['estado']} {item['obs']}"
            
            btn = Button(
                text=texto_boton, markup=True, size_hint_y=None, height=ALTO_BOTON_CONFIG, 
                background_color=color_btn, halign='center', valign='middle',
                font_size=f"{TAMANO_LETRA_CONFIG}sp"
            )
            btn.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0] - 20, None)))
            
            btn.info_clinica = item
            btn.bind(on_press=self.abrir_detalles_clinica)
            lista_botones.add_widget(btn)
            
        scroll.add_widget(lista_botones)
        self.layout_principal.add_widget(scroll)
        
        # 3. Botón Salir fijado abajo del todo
        btn_volver = Button(text="↩ SALIR AL LOGIN", size_hint_y=None, height=250, background_color=(1, 0.2, 0.2, 1), font_size='19sp')
        btn_volver.bind(on_press=self.regresar_a_login)
        self.layout_principal.add_widget(btn_volver)

    def sincronizar_con_google_sheets(self, instance):
        # Rompe el candado, descarga lo nuevo de la nube y redibuja la pantalla
        cargar_datos_iniciales(forzar_internet=True)
        self.cargar_lista_clinicas()
        
        # Popup de confirmación rápida
        contenido = BoxLayout(orientation='vertical', padding=10)
        contenido.add_widget(Label(text="¡Lista de Google Sheets\nSincronizada con éxito! ✅", halign='center'))
        popup = Popup(title='Sistema', content=contenido, size_hint=(0.6, 0.3))
        popup.open()

    def abrir_detalles_clinica(self, instance):
        global clinica_seleccionada
        clinica_seleccionada = instance.info_clinica
        self.manager.get_screen('detalles').actualizar_interfaz()
        self.manager.current = 'detalles'

    def regresar_a_login(self, instance):
        self.manager.current = 'login'

    def abrir_panel_ajustes(self, instance):
        global ALTO_BOTON_CONFIG, TAMANO_LETRA_CONFIG
        contenido = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        contenido.add_widget(Label(text=f"📐 Alto de los Cuadros: ({ALTO_BOTON_CONFIG} px)", font_size='14sp', size_hint_y=None, height=25))
        slider_alto = Slider(min=120, max=300, value=ALTO_BOTON_CONFIG, step=10, size_hint_y=None, height=35)
        contenido.add_widget(slider_alto)
        
        contenido.add_widget(Label(text=f"🔤 Tamaño de Letras: ({TAMANO_LETRA_CONFIG} sp)", font_size='14sp', size_hint_y=None, height=25))
        slider_letra = Slider(min=12, max=24, value=TAMANO_LETRA_CONFIG, step=1, size_hint_y=None, height=35)
        contenido.add_widget(slider_letra)
        
        contenido.add_widget(Label()) 
        btn_aplicar = Button(text="✅ APLICAR CAMBIOS", size_hint_y=None, height=50, background_color=(0.2, 0.6, 0.3, 1))
        contenido.add_widget(btn_aplicar)
        
        popup = Popup(title='⚙️ Ajustes Visuales', content=contenido, size_hint=(0.9, 0.6))
        
        def aplicar_cambios(*args):
            global ALTO_BOTON_CONFIG, TAMANO_LETRA_CONFIG
            ALTO_BOTON_CONFIG = int(slider_alto.value)
            TAMANO_LETRA_CONFIG = int(slider_letra.value)
            popup.dismiss()
            self.cargar_lista_clinicas()
            
        btn_aplicar.bind(on_press=aplicar_cambios)
        popup.open()

# =====================================================================
# 🎛️ PANTALLA 3: PANEL DE CONTROL DE CLÍNICA
# =====================================================================
class DetallesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout_principal = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        self.lbl_info = Label(text="", markup=True, font_size='22sp', halign='center', size_hint_y=0.2)
        self.layout_principal.add_widget(self.lbl_info)
        
        grid = GridLayout(cols=2, spacing=15, size_hint_y=0.65)
        
        btn_ok = Button(text="✅\nCOMPLETADO", background_color=(0.2, 0.7, 0.3, 1), font_size='16sp', halign='center')
        btn_ok.bind(on_press=self.accion_completado)
        
        btn_alert = Button(text="⚠️\nINCIDENCIA", background_color=(0.9, 0.5, 0.1, 1), font_size='16sp', halign='center')
        btn_alert.bind(on_press=self.accion_incidencia)
        
        btn_gps = Button(text="🗺️\nVER MAPA", background_color=(0.1, 0.5, 0.8, 1), font_size='16sp', halign='center')
        btn_gps.bind(on_press=self.accion_gps)
        
        btn_wsp = Button(text="📸\nENVIAR REPORT\nWHATSAPP", background_color=(0.05, 0.65, 0.3, 1), font_size='15sp', halign='center')
        btn_wsp.bind(on_press=self.abrir_whatsapp_grupo)
        
        grid.add_widget(btn_ok)
        grid.add_widget(btn_alert)
        grid.add_widget(btn_gps)
        grid.add_widget(btn_wsp)
        self.layout_principal.add_widget(grid)
        
        btn_cancelar = Button(text="↩️ Regresar a la Lista", size_hint_y=0.12, background_color=(0.3, 0.3, 0.3, 1))
        btn_cancelar.bind(on_press=self.cambiar_a_lista)
        self.layout_principal.add_widget(btn_cancelar)
        self.add_widget(self.layout_principal)

    def actualizar_interfaz(self):
        self.lbl_info.text = f"📍 Establecimiento:\n[b][color=33ff33]{clinica_seleccionada['nombre']}[/color][/b]\n({clinica_seleccionada['distrito']})"

    def abrir_whatsapp_grupo(self, instance):
        # RECUERDA: Aquí colocas el enlace real de invitación cuando la doctora te lo dé
        LINK_GRUPO_DIAGNOSTICO = "https://chat.whatsapp.com/G1H2I3J4K5L6M7N8O9P0Q" 
        webbrowser.open(LINK_GRUPO_DIAGNOSTICO)
        
        guardar_progreso_local()
        self.manager.get_screen('lista').cargar_lista_clinicas()
        self.manager.current = 'lista'

    def accion_gps(self, instance):
        query = f"{clinica_seleccionada['nombre']}, {clinica_seleccionada['distrito']}, Lima, Peru"
        url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query)}"
        webbrowser.open(url)

    def accion_completado(self, instance):
        clinica_seleccionada['estado'] = 'COMPLETADO'
        clinica_seleccionada['obs'] = "- OK"
        guardar_progreso_local()
        self.manager.get_screen('lista').cargar_lista_clinicas()
        self.manager.current = 'lista'

    def accion_incidencia(self, instance):
        clinica_seleccionada['estado'] = 'INCIDENCIA'
        clinica_seleccionada['obs'] = "- OBS"
        guardar_progreso_local()
        self.manager.get_screen('lista').cargar_lista_clinicas()
        self.manager.current = 'lista'

    def cambiar_a_lista(self, instance):
        self.manager.current = 'lista'

# =====================================================================
# 🏁 INICIADOR DEL SISTEMA
# =====================================================================
class MainApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(ListaScreen(name='lista'))
        sm.add_widget(DetallesScreen(name='detalles'))
        return sm

if __name__ == '__main__':
    MainApp().run()
