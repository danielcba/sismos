import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium, folium_static
import numpy as np
from supabase import create_client
from datetime import datetime, timedelta
import math

# Configuración de la página
st.set_page_config(
    page_title="Sismos cerca de Diques",
    page_icon="🏞️",
    layout="wide"
)

# Título de la página
st.title("Sismos cerca de Diques de Córdoba")
st.markdown("""
Visualización de sismos cercanos a los principales diques de la provincia de Córdoba.
Seleccione un dique para ver los sismos registrados en un radio de 30 km.
""")

# Conexión a Supabase
SUPABASE_URL = "https://dmgashfrjnhaduiifabr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRtZ2FzaGZyam5oYWR1aWlmYWJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4OTc5MDMsImV4cCI6MjA2MjQ3MzkwM30.vEld_xzy8Vcsz-0wBzZpTviWOKWi_OklLfTNP7JXDfo"

# Función para obtener datos de diques desde Supabase
def fetch_diques_data():
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Obtener todos los diques
        response = supabase.table('diques').select('*').execute()
        
        # Convertir a lista de diccionarios con los campos necesarios
        diques = []
        for dique in response.data:
            diques.append({
                'nombre': dique['nombre'],
                'latitud': dique['latitud'],
                'longitud': dique['longitud'],
                'cota_vertedero': dique.get('cota_vertedero'),
                'cota_actual': dique.get('cota_actual'),
                'diferencia': dique.get('diferencia'),
                'volumen_Hm3': dique.get('volumen_hm3')
            })
        
        return diques
        
    except Exception as e:
        st.error(f"Error al cargar datos de diques: {str(e)}")
        return []

# Obtener datos de diques
DIQUES = fetch_diques_data()

# Función para calcular distancia entre dos puntos en km (fórmula de Haversine)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radio de la Tierra en km
    
    # Convertir grados a radianes
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Diferencia de coordenadas
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Fórmula de Haversine
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distancia = R * c
    
    return distancia

# Función para obtener datos de sismos
def fetch_sismos_data():
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Obtener datos con paginación
        page_size = 1000
        offset = 0
        all_data = []
        
        while True:
            response = supabase.table('sismos').select('*').range(offset, offset + page_size - 1).execute()
            
            if not response.data:
                break
                
            all_data.extend(response.data)
            offset += page_size
        
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            # Convertir fechas y horas
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S').dt.time
            
        return df
        
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()

# Interfaz de usuario
st.sidebar.header("Filtros")

# Selector de dique
dique_seleccionado = st.sidebar.selectbox(
    "Seleccione un dique:",
    [dique["nombre"] for dique in DIQUES],
    index=0
)

# Obtener coordenadas del dique seleccionado
dique = next((d for d in DIQUES if d["nombre"] == dique_seleccionado), None)

# Filtros adicionales
st.sidebar.subheader("Filtros de Sismos")

# Rango de fechas
fecha_inicio = st.sidebar.date_input(
    "Fecha inicial",
    value=datetime(2007, 8, 27),  # Fecha del primer sismo registrado
    min_value=datetime(2007, 8, 27),
    max_value=datetime.now()
)

fecha_fin = st.sidebar.date_input(
    "Fecha final",
    value=datetime.now(),
    min_value=fecha_inicio,
    max_value=datetime.now()
)

# Rango de magnitudes
magnitud_min = st.sidebar.slider(
    "Magnitud mínima",
    min_value=1.5,
    max_value=4.5,
    value=1.5,
    step=0.1
)

magnitud_max = st.sidebar.slider(
    "Magnitud máxima",
    min_value=magnitud_min,
    max_value=4.5,
    value=4.5,
    step=0.1
)

# Rango de profundidades
profundidad_min = st.sidebar.slider(
    "Profundidad mínima (km)",
    min_value=1,
    max_value=25,
    value=1,
    step=1
)

profundidad_max = st.sidebar.slider(
    "Profundidad máxima (km)",
    min_value=profundidad_min,
    max_value=25,
    value=25,
    step=1
)

# Radio de búsqueda (km)
radio_km = st.sidebar.slider(
    "Radio de búsqueda (km)",
    min_value=1,
    max_value=50,
    value=30,
    step=1
)

# Cargar datos
with st.spinner("Cargando datos de sismos..."):
    sismos_df = fetch_sismos_data()

if sismos_df.empty:
    st.warning("No se encontraron datos de sismos.")
else:
    # Filtrar por fechas
    sismos_filtrados = sismos_df[
        (sismos_df['fecha'].dt.date >= fecha_inicio) & 
        (sismos_df['fecha'].dt.date <= fecha_fin) &
        (sismos_df['magnitud'] >= magnitud_min) &
        (sismos_df['magnitud'] <= magnitud_max) &
        (sismos_df['profundidad'] >= profundidad_min) &
        (sismos_df['profundidad'] <= profundidad_max)
    ].copy()
    
    # Calcular distancia al dique seleccionado
    sismos_filtrados['distancia_km'] = sismos_filtrados.apply(
        lambda row: haversine(
            dique['latitud'], dique['longitud'],
            row['latitud'], row['longitud']
        ),
        axis=1
    )
    
    # Filtrar por radio
    sismos_cercanos = sismos_filtrados[sismos_filtrados['distancia_km'] <= radio_km]
    
    # Mostrar estadísticas
    st.subheader(f"Sismos cercanos a {dique_seleccionado}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de sismos", len(sismos_cercanos))
    with col2:
        if not sismos_cercanos.empty:
            st.metric("Magnitud máxima", f"{sismos_cercanos['magnitud'].max():.1f}")
        else:
            st.metric("Magnitud máxima", "N/A")
    with col3:
        if not sismos_cercanos.empty:
            st.metric("Distancia promedio", f"{sismos_cercanos['distancia_km'].mean():.1f} km")
        else:
            st.metric("Distancia promedio", "N/A")
    with col4:
        if not sismos_cercanos.empty and 'profundidad' in sismos_cercanos.columns:
            st.metric("Profundidad promedio", f"{sismos_cercanos['profundidad'].mean():.1f} km")
        else:
            st.metric("Profundidad promedio", "N/A")
    
    # Crear mapa
    st.subheader("Mapa de Sismos")
    
    # Crear mapa centrado en el dique
    m = folium.Map(
        location=[dique['latitud'], dique['longitud']],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Añadir marcador del dique
    folium.Marker(
        [dique['latitud'], dique['longitud']],
        popup=f"<b>{dique['nombre']}</b><br>Dique",
        icon=folium.Icon(color='blue', icon='tint', prefix='fa')
    ).add_to(m)
    
    # Añadir círculo de radio
    folium.Circle(
        location=[dique['latitud'], dique['longitud']],
        radius=radio_km * 1000,  # Convertir a metros
        color='blue',
        fill=True,
        fill_color='blue',
        fill_opacity=0.1,
        popup=f"Radio: {radio_km} km"
    ).add_to(m)
    
    # Añadir marcadores de sismos
    for _, sismo in sismos_cercanos.iterrows():
        # Color basado en la magnitud
        if sismo['magnitud'] < 2.5:
            color = 'green'
        elif sismo['magnitud'] < 3.5:
            color = 'orange'
        else:
            color = 'red'
        
        # Tamaño basado en la magnitud (misma fórmula que en app.py)
        size = 2 + (sismo['magnitud'] * 1.2)
        
        # Popup con información
        popup = f"""
        <b>Fecha:</b> {sismo['fecha'].strftime('%Y-%m-%d')}<br>
        <b>Hora:</b> {sismo['hora']}<br>
        <b>Magnitud:</b> {sismo['magnitud']:.1f}<br>
        <b>Profundidad:</b> {sismo['profundidad']} km<br>
        <b>Distancia:</b> {sismo['distancia_km']:.1f} km
        """
        
        folium.CircleMarker(
            location=[sismo['latitud'], sismo['longitud']],
            radius=size,
            popup=popup,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.5,  # Reducida la opacidad para mejor visibilidad
            opacity=0.7,  # Añadida opacidad para el borde
            weight=1  # Grosor del borde
        ).add_to(m)
    
    # Mostrar mapa
    folium_static(m, width=1200, height=600)
    
    # Mostrar tabla de datos
    if not sismos_cercanos.empty:
        st.subheader("Datos de Sismos")
        # Ordenar por fecha descendente
        sismos_mostrar = sismos_cercanos.sort_values('fecha', ascending=False)
        
        # Definir columnas que queremos mostrar y sus nombres de visualización
        columnas_posibles = {
            'fecha': 'Fecha',
            'hora': 'Hora',
            'magnitud': 'Magnitud',
            'profundidad': 'Profundidad (km)',
            'distancia_km': 'Distancia (km)',
            'localidad': 'Localidad',
            'latitud': 'Latitud',
            'longitud': 'Longitud'
        }
        
        # Filtrar solo las columnas que existen en el DataFrame
        columnas_existentes = [col for col in columnas_posibles.keys() if col in sismos_mostrar.columns]
        
        if columnas_existentes:
            # Renombrar columnas para visualización
            df_mostrar = sismos_mostrar[columnas_existentes].copy()
            df_mostrar = df_mostrar.rename(columns={
                k: v for k, v in columnas_posibles.items() if k in columnas_existentes
            })
            
            # Mostrar el DataFrame
            st.dataframe(
                df_mostrar,
                use_container_width=True,
                height=400
            )
        else:
            st.warning("No hay columnas de datos disponibles para mostrar.")
    else:
        st.info("No se encontraron sismos que cumplan con los criterios de búsqueda.")

# Estilos CSS personalizados
st.markdown("""
<style>
    .stMetricLabel {
        font-size: 1rem !important;
    }
    .stMetricValue {
        font-size: 1.5rem !important;
    }
</style>
""", unsafe_allow_html=True)
