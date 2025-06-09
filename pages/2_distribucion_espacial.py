# pages/2_distribucion_espacial.py

# Importar bibliotecas necesarias
import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
import seaborn as sns
from supabase import create_client
from datetime import datetime
import math  # Para cálculos geográficos

# Configuración de la página
st.set_page_config(
    page_title="Distribución Espacial de Sismos",
    page_icon="🌍",
    layout="wide"
)

st.title("Distribución Espacial de Sismos en Córdoba")

# Función para cargar datos (similar a app.py)
@st.cache_data
def fetch_sismos_data():
    try:
        # Credenciales de Supabase
        SUPABASE_URL = "https://dmgashfrjnhaduiifabr.supabase.co"
        SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRtZ2FzaGZyam5oYWR1aWlmYWJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4OTc5MDMsImV4cCI6MjA2MjQ3MzkwM30.vEld_xzy8Vcsz-0wBzZpTviWOKWi_OklLfTNP7JXDfo"
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Paginación para obtener todos los datos
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
        
        # Crear DataFrame
        df = pd.DataFrame(all_data)
        
        # Procesamiento de fechas y horas
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S').dt.time
            df['fecha_hora'] = pd.to_datetime(
                df['fecha'].astype(str) + ' ' + df['hora'].astype(str)
            )
        
        return df
        
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()

# Cargar datos
sismos_df = fetch_sismos_data()

# Mostrar mensaje si no hay datos
if sismos_df.empty:
    st.warning("No se encontraron datos de sismos.")
    st.stop()

# Crear pestañas para los diferentes análisis
tab1, tab2, tab3 = st.tabs([
    "Mapa de Calor Geográfico", 
    "Profundidad vs. Ubicación", 
    "Clústeres Espaciales"
])

# =============================================
# Pestaña 1: Mapa de Calor Geográfico
# =============================================
with tab1:
    st.header("Mapa de Calor de Sismos")
    st.markdown("""
        Este mapa muestra la densidad de sismos en la provincia de Córdoba. 
        Las zonas con mayor concentración de eventos sísmicos se muestran en colores más cálidos.
    """)
    
    # Crear mapa base
    m = folium.Map(location=[-32.2935, -64.1810], zoom_start=6)
    
    # Preparar datos para el mapa de calor
    heat_data = [[row['latitud'], row['longitud']] for _, row in sismos_df.iterrows()]
    
    # Añadir capa de calor
    HeatMap(heat_data, radius=15).add_to(m)
    
    # Mostrar mapa
    folium_static(m, width=1000, height=600)

# =============================================
# Pestaña 2: Profundidad vs. Ubicación
# =============================================
with tab2:
    st.header("Relación entre Profundidad y Ubicación Geográfica")
    st.markdown("""
        En este mapa, cada círculo representa un sismo. El color indica la profundidad del sismo:
        - **🔴 Rojo**: Sismos superficiales (0-30 km)
        - **🟠 Naranja**: Sismos intermedios (30-70 km)
        - **🟡 Amarillo**: Sismos profundos (>70 km)
    """)
    
    # Crear mapa base
    m = folium.Map(location=[-32.2935, -64.1810], zoom_start=6)
    
    # Función para determinar color según profundidad
    def get_color(profundidad):
        if profundidad < 30:
            return 'red'
        elif profundidad < 70:
            return 'orange'
        else:
            return 'yellow'
    
    # Añadir marcadores
    for _, row in sismos_df.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=3,
            popup=f"Prof: {row['profundidad']} km | Mag: {row['magnitud']}",
            color=get_color(row['profundidad']),
            fill=True,
            fill_color=get_color(row['profundidad']),
            fill_opacity=0.7
        ).add_to(m)
    
    # Mostrar mapa
    folium_static(m, width=1000, height=600)
    
    # Gráfico de dispersión adicional
    st.subheader("Relación Geográfica de Profundidades")
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(
        sismos_df['longitud'], 
        sismos_df['latitud'], 
        c=sismos_df['profundidad'], 
        cmap='viridis',
        alpha=0.6,
        s=sismos_df['magnitud'] * 10  # Tamaño según magnitud
    )
    
    # Configurar gráfico
    ax.set_xlabel('Longitud')
    ax.set_ylabel('Latitud')
    ax.set_title('Distribución de Profundidad de Sismos')
    cbar = plt.colorbar(scatter)
    cbar.set_label('Profundidad (km)')
    plt.grid(True, alpha=0.2)
    
    st.pyplot(fig)

# =============================================
# Pestaña 3: Clústeres Espaciales (ACTUALIZADO PARA USAR KM)
# =============================================
with tab3:
    st.header("Identificación de Agrupamientos Sísmicos")
    st.markdown("""
        Se aplica el algoritmo DBSCAN para identificar zonas de alta densidad sísmica (clústeres).
        Cada color representa un grupo diferente de actividad sísmica.
        
        **Parámetros:**
        - **Radio de búsqueda (km)**: Distancia máxima entre sismos para considerarlos parte del mismo grupo
        - **Mínimo de muestras**: Número mínimo de sismos cercanos para formar un grupo
    """)
    
    # Función para calcular distancia en km entre coordenadas
    def haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calcula la distancia en kilómetros entre dos puntos geográficos
        usando la fórmula de Haversine (precisión mayor)
        """
        R = 6371  # Radio de la Tierra en km
        
        # Convertir grados a radianes
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Diferencias
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Fórmula Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

    # Crear matriz de distancias (en km)
    def distance_matrix(coords):
        """
        Construye una matriz de distancias en kilómetros entre todos los pares de puntos
        """
        n = coords.shape[0]
        dist_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                dist = haversine_distance(
                    coords[i, 0], coords[i, 1],
                    coords[j, 0], coords[j, 1]
                )
                dist_matrix[i, j] = dist
                dist_matrix[j, i] = dist
                
        return dist_matrix

    # Preparamos los datos para clustering
    coords = sismos_df[['latitud', 'longitud']].values
    
    # Parámetros ajustables por el usuario (EN KILÓMETROS)
    eps_km = st.slider("Radio de búsqueda (km)", 0.1, 50.0, 5.0, 0.1)
    min_samples = st.slider("Mínimo de muestras por clúster", 1, 50, 10)
    
    # Calcular matriz de distancias (solo si hay datos)
    if len(coords) > 0:
        # Mostrar mensaje de carga
        with st.spinner("Calculando distancias entre sismos..."):
            dist_matrix = distance_matrix(coords)
            
            # Aplicar DBSCAN con la matriz de distancias
            db = DBSCAN(eps=eps_km, min_samples=min_samples, metric="precomputed").fit(dist_matrix)
            labels = db.labels_
    else:
        labels = np.array([])
    
    # Número de clusters encontrados (excluyendo ruido)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    st.info(f"Se identificaron {n_clusters} zonas de alta actividad sísmica.")
    
    # Añadir etiquetas al DataFrame
    sismos_df['cluster'] = labels
    
    # Crear mapa
    m = folium.Map(location=[-32.2935, -64.1810], zoom_start=6)
    
    # Paleta de colores para los clusters
    colors = [
        'red', 'blue', 'green', 'purple', 'orange', 
        'darkred', 'lightblue', 'pink', 'darkblue', 'gray'
    ]
    
    # Añadir marcadores por cluster
    for _, row in sismos_df.iterrows():
        cluster_id = row['cluster']
        if cluster_id == -1:
            color = 'black'  # Ruido
        else:
            color = colors[cluster_id % len(colors)]
        
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=3,
            popup=f"Cluster: {cluster_id} | Mag: {row['magnitud']}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7
        ).add_to(m)
    
    # Mostrar mapa
    folium_static(m, width=1000, height=600)
    
    # Estadísticas de clusters
    st.subheader("Características de los Agrupamientos")
    if n_clusters > 0:
        cluster_stats = sismos_df[sismos_df['cluster'] != -1].groupby('cluster').agg({
            'latitud': 'mean',
            'longitud': 'mean',
            'magnitud': ['mean', 'max'],
            'profundidad': ['mean', 'min', 'max'],
            'fecha': 'count'
        }).reset_index()
        
        cluster_stats.columns = [
            'Cluster', 'Latitud Promedio', 'Longitud Promedio', 
            'Magnitud Media', 'Magnitud Máxima',
            'Profundidad Media', 'Profundidad Mínima', 'Profundidad Máxima',
            'Cantidad de Sismos'
        ]
        
        st.dataframe(cluster_stats.sort_values('Cantidad de Sismos', ascending=False))
    else:
        st.warning("No se identificaron zonas de alta densidad sísmica con los parámetros actuales.")
