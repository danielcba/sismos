# Importar bibliotecas necesarias
import streamlit as st  # Para crear la aplicación web
import pandas as pd  # Para manipulación de datos
import folium  # Para crear mapas interactivos
from streamlit_folium import folium_static  # Para mostrar mapas de Folium en Streamlit
import matplotlib.pyplot as plt  # Para gráficos estáticos
import seaborn as sns  # Para visualización de datos
import plotly.express as px  # Para gráficos interactivos
import numpy as np  # Para cálculos numéricos
import mplcursors  # Para mejorar interactividad en gráficos de matplotlib
from supabase import create_client  # Cliente para conectar con Supabase
from datetime import datetime  # Para manejo de fechas

# =============================================
# CONFIGURACIÓN INICIAL DE LA APLICACIÓN
# =============================================

# Configurar propiedades de la página de Streamlit
st.set_page_config(
    page_title="Sismos en Córdoba",  # Título de la pestaña del navegador
    page_icon="quake",  # Ícono (emoji de terremoto)
    layout="wide"  # Diseño amplio para usar todo el ancho
)

# =============================================
# CONEXIÓN A LA BASE DE DATOS SUPABASE
# =============================================

# Credenciales de Supabase (base de datos PostgreSQL en la nube)
SUPABASE_URL = "https://dmgashfrjnhaduiifabr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRtZ2FzaGZyam5oYWR1aWlmYWJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4OTc5MDMsImV4cCI6MjA2MjQ3MzkwM30.vEld_xzy8Vcsz-0wBzZpTviWOKWi_OklLfTNP7JXDfo"

# Crear cliente de Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================================
# FUNCIONES AUXILIARES
# =============================================

def mostrar_mensaje_estado(resultado, tipo_filtro=None):
    """
    Muestra un mensaje de advertencia si no hay datos después de aplicar filtros.
    
    Parámetros:
        resultado (DataFrame): Conjunto de datos filtrados
        tipo_filtro (str): Tipo de filtro aplicado (para mensaje personalizado)
    
    Retorna:
        bool: True si hay datos, False si no hay datos
    """
    if resultado.empty:
        mensaje = "No se encontraron sismos"
        if tipo_filtro:
            mensaje += f" que cumplan con los criterios de {tipo_filtro}"
        st.warning(mensaje)
        return False
    return True

def fetch_sismos_data():
    """
    Obtiene datos de sismos desde Supabase usando paginación.
    
    Retorna:
        DataFrame: Datos de sismos con columnas procesadas
    """
    try:
        # Configuración de paginación para manejar grandes conjuntos de datos
        page_size = 1000  # Cantidad de registros por página
        offset = 0  # Desplazamiento inicial
        all_data = []  # Almacenará todos los registros
        
        while True:
            # Consulta a Supabase con ordenamiento y rango
            response = supabase.from_('sismos').select(
                "fecha, hora, latitud, longitud, profundidad, magnitud"
            ).order("fecha", desc=True).order("hora", desc=True).range(offset, offset + page_size - 1)
            
            # Obtener datos de la consulta
            data = response.execute().data
            
            # Salir del bucle si no hay más datos
            if not data:
                break
                
            # Acumular datos
            all_data.extend(data)
            # Avanzar al siguiente lote
            offset += page_size
            
        # Crear DataFrame con todos los datos
        df = pd.DataFrame(all_data)
        
        # Procesamiento de fechas y horas:
        # Convertir columna 'fecha' a datetime
        df['fecha'] = pd.to_datetime(df['fecha'])
        # Convertir columna 'hora' a objeto time
        df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S').dt.time
        # Crear columna combinada de fecha y hora
        df['fecha_hora'] = pd.to_datetime(
            df['fecha'].astype(str) + ' ' + df['hora'].astype(str)
        )
        
        return df
    
    except Exception as e:
        # Manejo de errores en la carga de datos
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()  # Retorna DataFrame vacío en caso de error

# =============================================
# CARGA DE DATOS
# =============================================

# Obtener datos de sismos desde Supabase
sismos_df = fetch_sismos_data()

# =============================================
# BARRA LATERAL (SIDEBAR) - FILTROS
# =============================================

# Título del sidebar con estilo HTML
st.sidebar.markdown("<h1 style='margin-bottom: 0;'>Filtros</h1>", unsafe_allow_html=True)

# Estilos CSS personalizados para el sidebar
st.sidebar.markdown("""
<style>
.sidebar .sidebar-content {
    padding-top: 0;
}
.sidebar .stDateInput, .sidebar .stTimeInput {
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# Filtros de fecha
# ----------------------------
fecha_inicio = st.sidebar.date_input(
    "Fecha inicial",
    value=sismos_df['fecha'].min() if not sismos_df.empty else datetime.today(),
    min_value=datetime(2007, 8, 27),  # Fecha mínima histórica
    max_value=datetime(2026, 12, 31)   # Fecha máxima permitida
)

fecha_fin = st.sidebar.date_input(
    "Fecha final",
    value=datetime.today(),
    min_value=fecha_inicio,  # No puede ser anterior a fecha inicial
    max_value=datetime(2026, 12, 31)
)

# ----------------------------
# Filtros de hora
# ----------------------------
hora_inicio = st.sidebar.time_input(
    "Hora inicial",
    value=datetime.strptime("00:00:00", "%H:%M:%S").time()  # Valor predeterminado: media noche
)

hora_fin = st.sidebar.time_input(
    "Hora final",
    value=datetime.strptime("23:59:59", "%H:%M:%S").time()  # Valor predeterminado: fin de día
)

# ----------------------------
# Filtros de magnitud (escala Richter)
# ----------------------------
magnitud_min = st.sidebar.number_input(
    "Magnitud mínima",
    min_value=0.0,     # Valor mínimo posible
    max_value=10.0,    # Valor máximo teórico
    value=0.0,         # Valor predeterminado
    step=0.1           # Incremento/decremento
)

magnitud_max = st.sidebar.number_input(
    "Magnitud máxima",
    min_value=0.0,
    max_value=10.0,
    value=10.0,        # Valor predeterminado (máximo)
    step=0.1
)

# ----------------------------
# Filtros de profundidad (kilómetros)
# ----------------------------
profundidad_min = st.sidebar.number_input(
    "Profundidad mínima (km)",
    min_value=0.0,      # Superficie
    max_value=1000.0,   # Valor máximo razonable
    value=0.0,
    step=1.0
)

profundidad_max = st.sidebar.number_input(
    "Profundidad máxima (km)",
    min_value=0.0,
    max_value=1000.0,
    value=1000.0,       # Valor predeterminado (máximo)
    step=1.0
)

# ----------------------------
# Filtro de proximidad geográfica
# ----------------------------
st.sidebar.subheader("Filtro de Proximidad")

# Input para latitud con precisión de 3 decimales
latitud = st.sidebar.number_input(
    "Latitud en Grados Decimales (DD) ej. -31.351",
    min_value=-90.0,    # Rango válido de latitudes
    max_value=90.0,
    value=None,         # Sin valor predeterminado
    step=0.001,         # Precisión de 3 decimales
    format="%.3f"       # Formato de visualización
)

# Input para longitud con precisión de 3 decimales
longitud = st.sidebar.number_input(
    "Longitud en Grados Decimales (DD) ej. -64.619",
    min_value=-180.0,   # Rango válido de longitudes
    max_value=180.0,
    value=None,
    step=0.001,
    format="%.3f"
)

# Radio de búsqueda en kilómetros
radio = st.sidebar.number_input(
    "Radio de búsqueda en km",
    min_value=0.0,      # Radio mínimo (0 = mismo punto)
    max_value=1000.0,   # Radio máximo permitido
    value=0.0,          # Valor predeterminado (desactivado)
    step=0.1,           # Precisión de 1 decimal
    format="%.1f"
)

# =============================================
# APLICACIÓN DE FILTROS AL DATASET
# =============================================

# Solo procesar si hay datos disponibles
if not sismos_df.empty:
    # Copia del DataFrame original para aplicar filtros
    sismos_filtro = sismos_df.copy()
    # Lista para rastrear qué tipos de filtros se aplicaron
    filtros_aplicados = []
    
    # Filtro de fechas (rango)
    if fecha_inicio:
        sismos_filtro = sismos_filtro[sismos_filtro['fecha'] >= pd.to_datetime(fecha_inicio)]
        filtros_aplicados.append("fecha")
    if fecha_fin:
        sismos_filtro = sismos_filtro[sismos_filtro['fecha'] <= pd.to_datetime(fecha_fin)]
        filtros_aplicados.append("fecha")
    
    # Filtro de horas (rango)
    if hora_inicio:
        # Convertir a objeto time para comparación
        hora_inicio_obj = pd.to_datetime(hora_inicio.strftime('%H:%M:%S')).time()
        sismos_filtro = sismos_filtro[sismos_filtro['hora'] >= hora_inicio_obj]
        filtros_aplicados.append("hora")
    if hora_fin:
        hora_fin_obj = pd.to_datetime(hora_fin.strftime('%H:%M:%S')).time()
        sismos_filtro = sismos_filtro[sismos_filtro['hora'] <= hora_fin_obj]
        filtros_aplicados.append("hora")
    
    # Filtro de magnitud (rango)
    if magnitud_min > 0:
        sismos_filtro = sismos_filtro[sismos_filtro['magnitud'] >= magnitud_min]
        filtros_aplicados.append("magnitud")
    if magnitud_max < 10:
        sismos_filtro = sismos_filtro[sismos_filtro['magnitud'] <= magnitud_max]
        filtros_aplicados.append("magnitud")
    
    # Filtro de profundidad (rango)
    if profundidad_min > 0:
        sismos_filtro = sismos_filtro[sismos_filtro['profundidad'] >= profundidad_min]
        filtros_aplicados.append("profundidad")
    if profundidad_max < 1000:
        sismos_filtro = sismos_filtro[sismos_filtro['profundidad'] <= profundidad_max]
        filtros_aplicados.append("profundidad")
    
    # Filtro de proximidad geográfica (solo si se proporcionan coordenadas y radio)
    if latitud is not None and longitud is not None and radio > 0:
        # Conversión de kilómetros a grados (aproximación)
        # 111.32 km ≈ 1 grado de latitud/longitud
        radio_grados = radio / 111.32
        
        # Cálculo de distancia euclidiana en grados
        sismos_filtro['distancia'] = np.sqrt(
            (sismos_filtro['latitud'] - latitud) ** 2 +
            (sismos_filtro['longitud'] - longitud) ** 2
        )
        
        # Filtrar eventos dentro del radio
        sismos_filtro = sismos_filtro[sismos_filtro['distancia'] <= radio_grados]
        
        # Convertir distancia a kilómetros para visualización
        sismos_filtro['distancia_km'] = sismos_filtro['distancia'] * 111.32
        filtros_aplicados.append("proximidad")
    
    # Manejo de casos especiales:
    # - Si no se aplicó ningún filtro, mostrar todos los datos
    # - Si se aplicaron filtros pero no hay resultados, mostrar advertencia
    if not filtros_aplicados:
        sismos_filtro = sismos_df.copy()  # Mostrar dataset completo
    elif sismos_filtro.shape[0] == 0:
        # Mostrar mensaje específico para el primer filtro aplicado
        tipo_filtro = filtros_aplicados[0]
        mostrar_mensaje_estado(sismos_filtro, tipo_filtro)
else:
    # Si no hay datos iniciales, crear DataFrame vacío
    sismos_filtro = pd.DataFrame()

# =============================================
# INTERFAZ PRINCIPAL
# =============================================

# Título principal de la aplicación
st.title("Monitor de Sismos en Córdoba")

# =============================================
# ESTADÍSTICAS EN EL SIDEBAR
# =============================================

# Estadísticas básicas (solo se muestran si hay datos filtrados)
st.sidebar.header("Estadísticas")
if mostrar_mensaje_estado(sismos_filtro, "fecha"):
    st.sidebar.write(f"Total de sismos: {len(sismos_filtro)}")
    st.sidebar.write(f"Magnitud máxima: {sismos_filtro['magnitud'].max():.2f}")
    st.sidebar.write(f"Magnitud mínima: {sismos_filtro['magnitud'].min():.2f}")
    st.sidebar.write(f"Profundidad máxima: {sismos_filtro['profundidad'].max():.2f} km")
    st.sidebar.write(f"Profundidad mínima: {sismos_filtro['profundidad'].min():.2f} km")

# =============================================
# SECCIÓN DEL MAPA INTERACTIVO
# =============================================

st.header("Ubicación de los Sismos")
if mostrar_mensaje_estado(sismos_filtro, "proximidad"):
    # Crear mapa centrado en Córdoba, Argentina
    m = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
    
    # Añadir marcadores circulares para cada sismo
    for _, sismo in sismos_filtro.sort_values("magnitud", ascending=False).iterrows():
        # Color basado en la magnitud
        if sismo['magnitud'] < 2.5:
            color = 'green'
        elif sismo['magnitud'] < 3.5:
            color = 'orange'
        else:
            color = 'red'
            
        # Tamaño basado en la magnitud
        size = 2 + (sismo['magnitud'] * 1.2)
        
        folium.CircleMarker(
            # Coordenadas del sismo
            location=[sismo['latitud'], sismo['longitud']],
            # Radio proporcional a la magnitud
            radius=size,
            # Popup con información detallada
            popup=f"""
                <b>Fecha:</b> {sismo['fecha'].strftime('%Y-%m-%d')}<br>
                <b>Hora:</b> {sismo['hora']}<br>
                <b>Magnitud:</b> {sismo['magnitud']:.1f}<br>
                <b>Profundidad:</b> {sismo['profundidad']} km<br>
                <b>Latitud:</b> {sismo['latitud']:.4f}<br>
                <b>Longitud:</b> {sismo['longitud']:.4f}
            """,
            color=color,         # Color del borde basado en magnitud
            fill=True,           # Rellenar el círculo
            fill_color=color,    # Color de relleno basado en magnitud
            fill_opacity=0.4,    # Transparencia del relleno (más transparente)
            opacity=0.7,         # Opacidad del borde
            weight=1             # Grosor del borde
        ).add_to(m)
    
    # Si se está aplicando un filtro de proximidad, agregar un círculo con el radio de búsqueda
    if 'proximidad' in filtros_aplicados and latitud is not None and longitud is not None and radio > 0:
        # Agregar marcador en el centro
        folium.Marker(
            location=[latitud, longitud],
            popup=f"Centro de búsqueda\nRadio: {radio} km",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
        
        # Agregar círculo con el radio de búsqueda
        folium.Circle(
            location=[latitud, longitud],
            radius=radio * 1000,  # Convertir km a metros
            color='blue',
            weight=1,  # Línea muy fina
            fill=False,
            opacity=0.7
        ).add_to(m)
    
    # Mostrar el mapa en la aplicación
    folium_static(m, width=1000, height=600)

# =============================================
# SECCIÓN DE GRÁFICOS ANALÍTICOS
# =============================================

st.header("Análisis de Datos")

# ----------------------------
# Configuración estética global para gráficos
# ----------------------------
plt.style.use('dark_background')  # Usar tema oscuro
plt.rcParams.update({
    'axes.facecolor': 'black',      # Fondo de ejes negro
    'figure.facecolor': 'black',    # Fondo de figura negro
    'text.color': 'white',           # Color de texto blanco
    'axes.labelcolor': 'white',      # Color de etiquetas de ejes
    'xtick.color': 'white',          # Color de marcas en eje X
    'ytick.color': 'white',          # Color de marcas en eje Y
    'axes.edgecolor': 'white',       # Color de bordes de ejes
    'grid.color': 'gray',            # Color de la grilla
    'grid.alpha': 0.1,               # Transparencia de la grilla
    'grid.linestyle': '-',           # Estilo de línea de la grilla
    'lines.linewidth': 0.2           # Grosor de líneas
})

# ----------------------------
# Gráfico de series temporales de magnitud
# ----------------------------
st.subheader("Magnitud de los sismos en la escala Richter")
if mostrar_mensaje_estado(sismos_filtro, "magnitud"):
    # Ordenar datos cronológicamente
    sismos_ordenados = sismos_filtro.sort_values('fecha')
    
    # Crear gráfico interactivo con Plotly
    fig = px.line(
        sismos_ordenados,
        x=range(len(sismos_ordenados)),  # Eje X: índice de eventos
        y='magnitud',                    # Eje Y: magnitud
        labels={'x': 'Total de sismos', 'y': 'Magnitud'},
        template='plotly_dark'           # Usar tema oscuro de Plotly
    )
    
    # Personalizar apariencia de la línea
    fig.update_traces(
        line=dict(color='green', width=0.8),
        mode='lines+markers',            # Línea con marcadores
        marker=dict(size=2)              # Tamaño de marcadores
    )
    
    # Calcular y agregar línea de media
    media_magnitud = sismos_ordenados['magnitud'].mean()
    fig.add_hline(
        y=media_magnitud,
        line_dash="dash",                # Línea discontinua
        line_color="white",
        line_width=0.5,
        annotation_text=f'Media: {media_magnitud:.2f}',  # Texto anotación
        annotation_position="top right"   # Posición de la anotación
    )
    
    # Personalizar tooltips
    fig.update_traces(
        hovertemplate='<b>Magnitud: %{y:.2f}</b><br>'
    )
    
    # Mostrar gráfico en la aplicación
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Gráfico de series temporales de profundidad
# ----------------------------
st.subheader("Profundidad de los sismos en Km")
if mostrar_mensaje_estado(sismos_filtro, "profundidad"):
    # Ordenar datos cronológicamente
    sismos_ordenados = sismos_filtro.sort_values('fecha')
    
    # Crear gráfico interactivo con Plotly
    fig = px.line(
        sismos_ordenados,
        x=range(len(sismos_ordenados)),
        y='profundidad',
        labels={'x': 'Total de sismos', 'y': 'Profundidad (km)'}
    )
    
    # Personalizar apariencia
    fig.update_traces(
        line=dict(color='green', width=1),
        mode='lines+markers',
        marker=dict(size=2)
    )
    
    # Calcular y agregar línea de media
    media_profundidad = sismos_ordenados['profundidad'].mean()
    fig.add_hline(
        y=media_profundidad,
        line_dash="dash",
        line_color="white",
        line_width=0.2,
        annotation_text=f'Media: {media_profundidad:.2f}',
        annotation_position="top right"
    )
    
    # Personalizar tooltips
    fig.update_traces(
        hovertemplate='<b>Profundidad: %{y:.2f} km</b><br>'
    )
    
    # Mostrar gráfico
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Gráfico de dispersión: Magnitud vs Profundidad
# ----------------------------
st.header("Magnitud vs Profundidad")
if mostrar_mensaje_estado(sismos_filtro, "relación magnitud-profundidad"):
    fig = px.scatter(
        sismos_filtro,
        x='profundidad',    # Eje X: profundidad
        y='magnitud',       # Eje Y: magnitud
        color='fecha',      # Color por fecha (escala temporal)
        hover_data=['fecha', 'hora'],  # Datos adicionales en tooltip
    )
    # Mostrar gráfico interactivo
    st.plotly_chart(fig, use_container_width=True)
