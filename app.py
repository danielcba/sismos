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
import os  # Importar os para variables de entorno

# Configuración de la página
st.set_page_config(
    page_title="Sismos en Córdoba",
    page_icon="quake",
    layout="wide"
)

# Función para conectarse a la base de datos (MODIFICADO PARA STREAMLIT CLOUD)
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT'),
            sslmode='require',  # Obligatorio para Supabase
            sslrootcert='cert.crt'  # Certificado SSL (lo generamos después)
        )
        return conn
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        st.stop()

# Función para obtener datos de sismos (AGREGADO MANEJO DE ERRORES)
def fetch_sismos_data():
    try:
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
        
        # Convertir a DataFrame con verificación de datos
        columns = ['fecha', 'hora', 'latitud', 'longitud', 'profundidad', 'magnitud']
        df = pd.DataFrame(data, columns=columns)
        
        # Conversión segura de fecha y hora
        df['fecha_hora'] = pd.to_datetime(
            df['fecha'].astype(str) + ' ' + df['hora'].astype(str),
            errors='coerce'
        )
        return df.dropna(subset=['fecha_hora'])
        
    except Exception as e:
        st.error(f"Error al obtener datos: {str(e)}")
        st.stop()

# Obtener datos con loader
with st.spinner('Cargando datos sísmicos...'):
    sismos_df = fetch_sismos_data()

# [El resto del código se mantiene igual...]

# Al final de cada gráfico de matplotlib, agregar plt.close()
with col1:
    st.subheader("Distribución de Magnitudes")
    fig, ax = plt.subplots()
    sns.histplot(sismos_filtro['magnitud'], bins=20, kde=True)
    ax.set_xlabel('Magnitud')
    ax.set_ylabel('Frecuencia')
    st.pyplot(fig)
    plt.close(fig)  # Liberar memoria

with col2:
    st.subheader("Distribución de Profundidades")
    fig, ax = plt.subplots()
    sns.histplot(sismos_filtro['profundidad'], bins=20, kde=True)
    ax.set_xlabel('Profundidad (km)')
    ax.set_ylabel('Frecuencia')
    st.pyplot(fig)
    plt.close(fig)  # Liberar memoria
