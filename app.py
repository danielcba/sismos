import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import numpy as np
from datetime import datetime
import psycopg2

# Configuración de la página
st.set_page_config(
    page_title="Sismos en Córdoba",
    page_icon="quake",
    layout="wide"
)

# Función para conectarse a la base de datos
def get_db_connection():
    return psycopg2.connect(
        dbname=st.secrets.supabase.dbname,
        user=st.secrets.supabase.user,
        password=st.secrets.supabase.password,
        host=st.secrets.supabase.host,
        port=st.secrets.supabase.port,
        sslmode='require'
    )

# Función para obtener datos de sismos
def fetch_sismos_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT fecha, hora, latitud, longitud, profundidad, magnitud
        FROM sismos
        ORDER BY fecha DESC, hora DESC
    """)
    data = cur.fetchall()
    cur.close()
    conn.close()
    
    # Convertir a DataFrame
    columns = ['fecha', 'hora', 'latitud', 'longitud', 'profundidad', 'magnitud']
    df = pd.DataFrame(data, columns=columns)
    
    # Convertir fecha y hora a datetime
    df['fecha_hora'] = pd.to_datetime(df['fecha'].astype(str) + ' ' + df['hora'].astype(str))
    
    return df

# Obtener datos
sismos_df = fetch_sismos_data()

# Sidebar
st.sidebar.title("Filtros")
fecha_inicio = st.sidebar.date_input("Fecha inicial", value=sismos_df['fecha'].min())
fecha_fin = st.sidebar.date_input("Fecha final", value=sismos_df['fecha'].max())

# Filtrar datos por fecha
sismos_filtro = sismos_df[(sismos_df['fecha'] >= fecha_inicio) & (sismos_df['fecha'] <= fecha_fin)]

# Título principal
st.title("Monitor de Sismos en Córdoba")

# Estadísticas básicas
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Número total de sismos", len(sismos_filtro))
with col2:
    st.metric("Magnitud máxima", f"{sismos_filtro['magnitud'].max():.1f}")
with col3:
    st.metric("Profundidad promedio", f"{sismos_filtro['profundidad'].mean():.1f} km")

# Mapa con los últimos sismos
st.header("Mapa de Sismos")

# Crear mapa centrado en Córdoba
m = folium.Map(location=[-32.2935000, -64.1810500], zoom_start=6.3)

# Agregar marcadores para cada sismo
for _, sismo in sismos_filtro.iterrows():
    folium.CircleMarker(
        location=[sismo['latitud'], sismo['longitud']],
        radius=0.01 + sismo['magnitud'] * 1.5,  # Tamaño proporcional a la magnitud
        popup=f"Fecha: {sismo['fecha']}\nHora: {sismo['hora']}\nMagnitud: {sismo['magnitud']}\nProfundidad: {sismo['profundidad']} km",
        color='red',
        fill=True,
        fill_color='red'
    ).add_to(m)

folium_static(m)

# Gráficos de distribución
st.header("Análisis de Datos")

# Gráfico de distribución de magnitudes
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
fig = px.scatter(
    sismos_filtro,
    x='profundidad',
    y='magnitud',
    color='fecha',
    hover_data=['fecha', 'hora'],
    title='Magnitud vs Profundidad'
)
st.plotly_chart(fig, use_container_width=True)

