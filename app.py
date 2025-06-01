import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import numpy as np
from supabase import create_client
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Sismos en Córdoba",
    page_icon="quake",
    layout="wide"
)

# Inicializar cliente Supabase
SUPABASE_URL = "https://dmgashfrjnhaduiifabr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRtZ2FzaGZyam5oYWR1aWlmYWJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4OTc5MDMsImV4cCI6MjA2MjQ3MzkwM30.vEld_xzy8Vcsz-0wBzZpTviWOKWi_OklLfTNP7JXDfo"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Función para mostrar mensajes de estado
def mostrar_mensaje_estado(resultado, tipo_filtro=None):
    if resultado.empty:
        mensaje = "No se encontraron sismos"
        if tipo_filtro:
            mensaje += f" que cumplan con los criterios de {tipo_filtro}"
        st.warning(mensaje)
        return False
    return True

# Función para obtener datos de sismos
def fetch_sismos_data():
    try:
        # Obtener todos los registros usando paginación
        page_size = 1000
        offset = 0
        all_data = []
        
        while True:
            response = supabase.from_('sismos').select(
                "fecha, hora, latitud, longitud, profundidad, magnitud"
            ).order("fecha", desc=True).order("hora", desc=True).range(offset, offset + page_size - 1)
            
            data = response.execute().data
            if not data:
                break
                
            all_data.extend(data)
            offset += page_size
            
        # Convertir a DataFrame
        df = pd.DataFrame(all_data)
        
        # Convertir fecha y hora a datetime
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S').dt.time
        df['fecha_hora'] = pd.to_datetime(
            df['fecha'].astype(str) + ' ' + df['hora'].astype(str)
        )
        
        return df
    
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()

# Obtener datos
sismos_df = fetch_sismos_data()

# Sidebar
st.sidebar.title("Filtros")

# Filtros de fecha
fecha_inicio = st.sidebar.date_input(
    "Fecha inicial",
    value=sismos_df['fecha'].min() if not sismos_df.empty else datetime.today(),
    min_value=datetime(2011, 6, 12),  # Fecha mínima de los datos
    max_value=datetime(2025, 12, 31)  # Fecha máxima permitida
)
fecha_fin = st.sidebar.date_input(
    "Fecha final",
    value=sismos_df['fecha'].max() if not sismos_df.empty else datetime.today(),
    min_value=fecha_inicio,  # La fecha final no puede ser anterior a la fecha inicial
    max_value=datetime(2025, 12, 31)  # Fecha máxima permitida
)

# Filtros de hora
hora_inicio = st.sidebar.time_input(
    "Hora inicial",
    value=datetime.strptime("00:00:00", "%H:%M:%S").time()
)
hora_fin = st.sidebar.time_input(
    "Hora final",
    value=datetime.strptime("23:59:59", "%H:%M:%S").time()
)

# Filtros de magnitud
magnitud_min = st.sidebar.number_input(
    "Magnitud mínima",
    min_value=0.0,
    max_value=10.0,
    value=0.0,
    step=0.1
)
magnitud_max = st.sidebar.number_input(
    "Magnitud máxima",
    min_value=0.0,
    max_value=10.0,
    value=10.0,
    step=0.1
)

# Filtros de profundidad
profundidad_min = st.sidebar.number_input(
    "Profundidad mínima (km)",
    min_value=0.0,
    max_value=1000.0,
    value=0.0,
    step=1.0
)
profundidad_max = st.sidebar.number_input(
    "Profundidad máxima (km)",
    min_value=0.0,
    max_value=1000.0,
    value=1000.0,
    step=1.0
)

# Filtro de proximidad
st.sidebar.subheader("Filtro de Proximidad")
latitud = st.sidebar.number_input(
    "Latitud",
    min_value=-90.0,
    max_value=90.0,
    value=None,  # Valor por defecto None
    step=0.001,  # 3 dígitos después de la coma
    format="%.3f"  # Formato para mostrar 3 dígitos
)
longitud = st.sidebar.number_input(
    "Longitud",
    min_value=-180.0,
    max_value=180.0,
    value=None,  # Valor por defecto None
    step=0.001,  # 3 dígitos después de la coma
    format="%.3f"  # Formato para mostrar 3 dígitos
)
radio = st.sidebar.number_input(
    "Radio de búsqueda (km)",
    min_value=0.0,
    max_value=1000.0,
    value=0.0,  # Valor por defecto 0
    step=0.1,   # 1 dígito después de la coma
    format="%.1f"  # Formato para mostrar 1 dígito
)

# Filtrar datos por todos los criterios
if not sismos_df.empty:
    sismos_filtro = sismos_df.copy()  # Inicialmente copiamos el DataFrame
    filtros_aplicados = []  # Lista para rastrear qué filtros se aplican
    
    # Filtro de fechas
    if fecha_inicio:
        sismos_filtro = sismos_filtro[sismos_filtro['fecha'] >= pd.to_datetime(fecha_inicio)]
        filtros_aplicados.append("fecha")
    if fecha_fin:
        sismos_filtro = sismos_filtro[sismos_filtro['fecha'] <= pd.to_datetime(fecha_fin)]
        filtros_aplicados.append("fecha")
    
    # Filtro de horas
    if hora_inicio:
        sismos_filtro = sismos_filtro[sismos_filtro['hora'] >= pd.to_datetime(hora_inicio.strftime('%H:%M:%S')).time()]
        filtros_aplicados.append("hora")
    if hora_fin:
        sismos_filtro = sismos_filtro[sismos_filtro['hora'] <= pd.to_datetime(hora_fin.strftime('%H:%M:%S')).time()]
        filtros_aplicados.append("hora")
    
    # Filtro de magnitud
    if magnitud_min > 0:
        sismos_filtro = sismos_filtro[sismos_filtro['magnitud'] >= magnitud_min]
        filtros_aplicados.append("magnitud")
    if magnitud_max < 10:
        sismos_filtro = sismos_filtro[sismos_filtro['magnitud'] <= magnitud_max]
        filtros_aplicados.append("magnitud")
    
    # Filtro de profundidad
    if profundidad_min > 0:
        sismos_filtro = sismos_filtro[sismos_filtro['profundidad'] >= profundidad_min]
        filtros_aplicados.append("profundidad")
    if profundidad_max < 1000:
        sismos_filtro = sismos_filtro[sismos_filtro['profundidad'] <= profundidad_max]
        filtros_aplicados.append("profundidad")
    
    # Filtro de proximidad
    if latitud is not None and longitud is not None and radio > 0:
        # Convertir radio de km a grados (aproximadamente 111.32 km por grado)
        radio_grados = radio / 111.32
        
        # Calcular distancia en grados
        sismos_filtro['distancia'] = np.sqrt(
            (sismos_filtro['latitud'] - latitud) ** 2 +
            (sismos_filtro['longitud'] - longitud) ** 2
        )
        
        # Filtrar por distancia
        sismos_filtro = sismos_filtro[sismos_filtro['distancia'] <= radio_grados]
        
        # Agregar columna de distancia en km
        sismos_filtro['distancia_km'] = sismos_filtro['distancia'] * 111.32
        filtros_aplicados.append("proximidad")
    
    # Si no se aplicaron filtros, usar el DataFrame original
    if not filtros_aplicados:  # Si no se aplicaron filtros
        sismos_filtro = sismos_df.copy()  # Mantener todos los datos
    elif sismos_filtro.shape[0] == 0:  # Si se aplicaron filtros pero no hay resultados
        tipo_filtro = filtros_aplicados[0]  # Usar el primer filtro aplicado para el mensaje
        mostrar_mensaje_estado(sismos_filtro, tipo_filtro)
else:
    sismos_filtro = pd.DataFrame()

# Título principal
st.title("Monitor de Sismos en Córdoba")

# Estadísticas básicas
st.sidebar.header("Estadísticas")
if mostrar_mensaje_estado(sismos_filtro, "fecha"):
    st.sidebar.write(f"Total de sismos: {len(sismos_filtro)}")
    st.sidebar.write(f"Magnitud máxima: {sismos_filtro['magnitud'].max():.2f}")
    st.sidebar.write(f"Magnitud mínima: {sismos_filtro['magnitud'].min():.2f}")
    st.sidebar.write(f"Profundidad máxima: {sismos_filtro['profundidad'].max():.2f} km")
    st.sidebar.write(f"Profundidad mínima: {sismos_filtro['profundidad'].min():.2f} km")

# Mapa
st.header("Ubicación de los Sismos")
if mostrar_mensaje_estado(sismos_filtro, "proximidad"):
    # Crear mapa centrado en Córdoba
    m = folium.Map(location=[-32.2935000, -64.1810500], zoom_start=6)
    
    # Añadir marcadores para cada sismo
    for _,sismo in sismos_filtro.iterrows():
        folium.CircleMarker(
            location=[sismo['latitud'], sismo['longitud']],
            radius=2 + sismo['magnitud'] * 1.2,  # Tamaño proporcional a la magnitud
            popup=f"""
                Fecha: {sismo['fecha'].strftime('%Y-%m-%d')}<br>
                Hora: {sismo['hora']}<br>
                Magnitud: {sismo['magnitud']}<br>
                Profundidad: {sismo['profundidad']} km
            """,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.3,  # Ajustar la opacidad del relleno
            weight=0.5,  # Grosor del borde
        ).add_to(m)
    
    # Mostrar mapa
    folium_static(m)

# Gráficos
st.header("Análisis de Datos")

# Distribución de magnitudes y profundidades con sus medias
st.header("Distribuciones y Medias")

# Configurar estilo oscuro global
plt.style.use('dark_background')
plt.rcParams.update({
    'axes.facecolor': 'black',
    'figure.facecolor': 'black',
    'text.color': 'white',
    'axes.labelcolor': 'white',
    'xtick.color': 'white',
    'ytick.color': 'white',
    'axes.edgecolor': 'white',
    'grid.color': 'gray',
    'grid.alpha': 0.1,
    'grid.linestyle': '-',
    'lines.linewidth': 0.2
})

# Gráfico de magnitudes
st.subheader("Magnitud de los sismos en la escala Richter")
if mostrar_mensaje_estado(sismos_filtro, "magnitud"):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Ordenar datos por fecha
    sismos_ordenados = sismos_filtro.sort_values('fecha')
    
    # Graficar la línea de magnitudes
    ax.plot(range(len(sismos_ordenados)), sismos_ordenados['magnitud'], 
           linewidth=0.2, color='green', label='Magnitud')
    
    # Calcular y mostrar la media
    media_magnitud = sismos_ordenados['magnitud'].mean()
    ax.axhline(media_magnitud, color='white', linestyle='--', 
              linewidth=0.2, label=f'Media: {media_magnitud:.2f}')
    
    # Configurar el gráfico
    ax.set_title('Magnitud de los sismos en la escala Richter', color='white')
    ax.set_xlabel('Total de sismos', color='white')
    ax.set_ylabel('Magnitud', color='white')
    
    # Añadir leyenda y cuadrícula
    ax.legend()
    ax.grid(True, linestyle='-', alpha=0.1)
    
    # Configurar colores de los ejes
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_edgecolor('white')
    
    # Mostrar gráfico
    st.pyplot(fig)

# Gráfico de profundidades
st.subheader("Profundidad de los sismos en Km")
if mostrar_mensaje_estado(sismos_filtro, "profundidad"):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Ordenar datos por fecha
    sismos_ordenados = sismos_filtro.sort_values('fecha')
    
    # Graficar la línea de profundidades
    ax.plot(range(len(sismos_ordenados)), sismos_ordenados['profundidad'], 
           linewidth=0.2, color='green', label='Profundidad')
    
    # Calcular y mostrar la media
    media_profundidad = sismos_ordenados['profundidad'].mean()
    ax.axhline(media_profundidad, color='white', linestyle='--', 
              linewidth=0.2, label=f'Media: {media_profundidad:.2f}')
    
    # Configurar el gráfico
    ax.set_title('Profundidad de los sismos en Km', color='white')
    ax.set_xlabel('Total de sismos', color='white')
    ax.set_ylabel('Profundidad (km)', color='white')
    
    # Añadir leyenda y cuadrícula
    ax.legend()
    ax.grid(True, linestyle='-', alpha=0.1)
    
    # Configurar colores de los ejes
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_edgecolor('white')
    
    # Mostrar gráfico
    st.pyplot(fig)

# Gráfico de dispersión
st.header("Relación Magnitud-Profundidad")
if mostrar_mensaje_estado(sismos_filtro, "relación magnitud-profundidad"):
    fig = px.scatter(
        sismos_filtro,
        x='profundidad',
        y='magnitud',
        color='fecha',
        hover_data=['fecha', 'hora'],
        title='Magnitud vs Profundidad'
    )
    st.plotly_chart(fig, use_container_width=True)
