import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
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
fecha_inicio = st.sidebar.date_input(
    "Fecha inicial",
    value=sismos_df['fecha'].min() if not sismos_df.empty else datetime.today(),
    max_value=datetime(2025, 12, 31)
)
fecha_fin = st.sidebar.date_input(
    "Fecha final",
    value=sismos_df['fecha'].max() if not sismos_df.empty else datetime.today(),
    max_value=datetime(2025, 12, 31)
)

# Filtrar datos por fecha
if not sismos_df.empty:
    sismos_filtro = sismos_df[
        (sismos_df['fecha'] >= pd.to_datetime(fecha_inicio)) &
        (sismos_df['fecha'] <= pd.to_datetime(fecha_fin))
    ]
else:
    sismos_filtro = pd.DataFrame()

# Título principal
st.title("Monitor de Sismos en Córdoba")

# Estadísticas básicas
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Número total de sismos", len(sismos_filtro))
with col2:
    max_mag = sismos_filtro['magnitud'].max() if not sismos_filtro.empty else 0
    st.metric("Magnitud máxima", f"{max_mag:.1f}")
with col3:
    prof_prom = sismos_filtro['profundidad'].mean() if not sismos_filtro.empty else 0
    st.metric("Profundidad promedio", f"{prof_prom:.1f} km")

# Mapa con los últimos sismos
st.header("Mapa de Sismos")

# Crear mapa centrado en Córdoba
m = folium.Map(location=[-32.2935000, -64.1810500], zoom_start=6.3)

if not sismos_filtro.empty:
    for _, sismo in sismos_filtro.iterrows():
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
            weight=0.5  # Grosor del borde
        ).add_to(m)

folium_static(m)

# Gráficos de distribución
st.header("Análisis de Datos")

if not sismos_filtro.empty:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Distribución de Magnitudes")
        fig, ax = plt.subplots()
        sns.histplot(sismos_filtro['magnitud'], bins=20, kde=True)
        ax.set_xlabel('Magnitud')
        ax.set_ylabel('Frecuencia')
        st.pyplot(fig)

    with col2:
        st.subheader("Distribución de Profundidades")
        fig, ax = plt.subplots()
        sns.histplot(sismos_filtro['profundidad'], bins=20, kde=True)
        ax.set_xlabel('Profundidad (km)')
        ax.set_ylabel('Frecuencia')
        st.pyplot(fig)

# Gráfico de dispersión
st.header("Relación Magnitud-Profundidad")
if not sismos_filtro.empty:
    fig = px.scatter(
        sismos_filtro,
        x='profundidad',
        y='magnitud',
        color='fecha',
        hover_data=['fecha', 'hora'],
        title='Magnitud vs Profundidad'
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No hay datos para mostrar en este rango de fechas")
