# pages/2_distribucion_espacial.py

# Importar bibliotecas necesarias
import streamlit as st  # Framework para crear aplicaciones web interactivas
import pandas as pd  # Biblioteca para manipulación y análisis de datos
import folium  # Biblioteca para crear mapas interactivos
from folium.plugins import HeatMap  # Plugin para mapas de calor en Folium
from streamlit_folium import folium_static  # Para mostrar mapas de Folium en Streamlit
import numpy as np  # Biblioteca para operaciones numéricas
from sklearn.cluster import DBSCAN  # Algoritmo de clustering para identificar grupos de datos
from sklearn.preprocessing import StandardScaler  # Para normalizar datos antes de aplicar algoritmos
import matplotlib.pyplot as plt  # Biblioteca para crear gráficos estáticos
import seaborn as sns  # Biblioteca para mejorar la visualización de gráficos
from supabase import create_client  # Cliente para interactuar con Supabase (base de datos)
from datetime import datetime  # Para trabajar con fechas y horas

# =============================================================================
# CONFIGURACIÓN INICIAL DE LA PÁGINA
# =============================================================================
# Esta sección establece las propiedades básicas de la página web
st.set_page_config(
    page_title="Distribución Espacial de Sismos",  # Título que aparece en la pestaña del navegador
    page_icon="🌍",  # Ícono que aparece en la pestaña del navegador
    layout="wide"  # Usar todo el ancho disponible en la página
)

# Título principal de la aplicación
st.title("Distribución Espacial de Sismos en Córdoba")

# =============================================================================
# FUNCIÓN PARA CARGAR DATOS DESDE LA BASE DE DATOS
# =============================================================================
@st.cache_data  # Decorador para cachear los datos y mejorar rendimiento
def fetch_sismos_data():
    """
    Obtiene los datos de sismos desde la base de datos Supabase.
    
    Esta función:
    1. Se conecta a la base de datos usando las credenciales proporcionadas
    2. Recupera los datos mediante paginación (importante para grandes conjuntos de datos)
    3. Procesa las columnas de fecha y hora para un manejo más fácil
    4. Retorna un DataFrame con los datos procesados
    
    Retorna:
        DataFrame: Datos de sismos con columnas procesadas
    """
    try:
        # Credenciales de acceso a la base de datos
        SUPABASE_URL = "https://dmgashfrjnhaduiifabr.supabase.co"
        SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRtZ2FzaGZyam5oYWR1aWlmYWJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4OTc5MDMsImV4cCI6MjA2MjQ3MzkwM30.vEld_xzy8Vcsz-0wBzZpTviWOKWi_OklLfTNP7JXDfo"
        
        # Crear cliente para conectarse a Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Configuración de paginación para manejar grandes conjuntos de datos
        page_size = 1000  # Cantidad de registros a recuperar en cada solicitud
        offset = 0  # Punto de inicio para la recuperación de datos
        all_data = []  # Lista para almacenar todos los registros
        
        # Bucle para recuperar todos los datos mediante paginación
        while True:
            # Realizar consulta a la base de datos
            response = supabase.from_('sismos').select(
                "fecha, hora, latitud, longitud, profundidad, magnitud"
            ).order("fecha", desc=True).order("hora", desc=True).range(offset, offset + page_size - 1)
            
            # Obtener datos de la respuesta
            data = response.execute().data
            
            # Si no hay más datos, salir del bucle
            if not data:
                break
                
            # Agregar los datos obtenidos a la lista acumulativa
            all_data.extend(data)
            # Avanzar al siguiente lote de datos
            offset += page_size
        
        # Crear DataFrame de pandas con todos los datos
        df = pd.DataFrame(all_data)
        
        # Procesar datos si el DataFrame no está vacío
        if not df.empty:
            # Convertir columna 'fecha' a tipo datetime
            df['fecha'] = pd.to_datetime(df['fecha'])
            # Convertir columna 'hora' a objeto time
            df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S').dt.time
            # Crear columna combinada de fecha y hora
            df['fecha_hora'] = pd.to_datetime(
                df['fecha'].astype(str) + ' ' + df['hora'].astype(str)
            )
        
        return df
        
    except Exception as e:
        # Mostrar mensaje de error si ocurre algún problema
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()  # Retornar DataFrame vacío en caso de error

# =============================================================================
# CARGA DE DATOS Y VERIFICACIÓN
# =============================================================================
# Cargar datos de sismos usando la función definida
sismos_df = fetch_sismos_data()

# Verificar si hay datos disponibles
if sismos_df.empty:
    st.warning("No se encontraron datos de sismos.")
    st.stop()  # Detener la ejecución si no hay datos

# =============================================================================
# INTERFAZ DE USUARIO - ORGANIZADA EN PESTAÑAS
# =============================================================================
# Crear tres pestañas para diferentes tipos de análisis espaciales
tab1, tab2, tab3 = st.tabs([
    "Mapa de Calor Geográfico", 
    "Profundidad vs. Ubicación", 
    "Clústeres Espaciales"
])

# =============================================================================
# PESTAÑA 1: MAPA DE CALOR GEOGRÁFICO
# =============================================================================
with tab1:
    st.header("Mapa de Calor de Sismos")
    st.markdown("""
        **¿Qué muestra este mapa?**  
        Este mapa visualiza la densidad de sismos en la provincia de Córdoba. 
        Las áreas con mayor concentración de actividad sísmica aparecen en colores más cálidos (rojo/amarillo), 
        mientras que las áreas con menor actividad aparecen en colores más fríos (verde/azul).
        
        **¿Para qué sirve?**  
        Ayuda a identificar rápidamente las zonas de mayor riesgo sísmico en la región.
    """)
    
    # Crear mapa base centrado en la provincia de Córdoba
    m = folium.Map(location=[-32.2935, -64.1810], zoom_start=6)
    
    # Preparar datos para el mapa de calor: lista de [latitud, longitud]
    heat_data = [[row['latitud'], row['longitud']] for _, row in sismos_df.iterrows()]
    
    # Añadir capa de calor al mapa
    # El parámetro 'radius' controla el tamaño de la zona de influencia de cada punto
    HeatMap(heat_data, radius=15).add_to(m)
    
    # Mostrar el mapa en la aplicación
    folium_static(m, width=1000, height=600)

# =============================================================================
# PESTAÑA 2: PROFUNDIDAD VS. UBICACIÓN
# =============================================================================
with tab2:
    st.header("Relación entre Profundidad y Ubicación Geográfica")
    st.markdown("""
        **¿Qué muestra este mapa?**  
        Cada círculo representa un sismo, coloreado según su profundidad:
        - **🔴 Rojo**: Sismos superficiales (0-30 km)
        - **🟠 Naranja**: Sismos intermedios (30-70 km)
        - **🟡 Amarillo**: Sismos profundos (>70 km)
        
        **¿Para qué sirve?**  
        Permite visualizar cómo se distribuyen los sismos de diferentes profundidades 
        a lo largo de la geografía de Córdoba.
    """)
    
    # Crear mapa base centrado en la provincia de Córdoba
    m = folium.Map(location=[-32.2935, -64.1810], zoom_start=6)
    
    # Función para determinar el color del marcador según la profundidad
    def get_color(profundidad):
        """Asigna un color basado en la profundidad del sismo"""
        if profundidad < 30:
            return 'red'  # Sismos superficiales
        elif profundidad < 70:
            return 'orange'  # Sismos intermedios
        else:
            return 'yellow'  # Sismos profundos
    
    # Añadir marcadores al mapa para cada sismo
    for _, row in sismos_df.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],  # Ubicación del sismo
            radius=3,  # Tamaño del marcador
            popup=f"Prof: {row['profundidad']} km | Mag: {row['magnitud']}",  # Información emergente
            color=get_color(row['profundidad']),  # Color del borde
            fill=True,  # Rellenar el círculo
            fill_color=get_color(row['profundidad']),  # Color de relleno
            fill_opacity=0.7  # Transparencia del relleno
        ).add_to(m)
    
    # Mostrar el mapa
    folium_static(m, width=1000, height=600)
    
    # =====================================
    # GRÁFICO ADICIONAL: DISPERSIÓN DE PROFUNDIDADES
    # =====================================
    st.subheader("Relación Geográfica de Profundidades")
    st.markdown("""
        **¿Qué muestra este gráfico?**  
        Representa la ubicación de cada sismo en un plano geográfico (longitud vs latitud),
        donde el color indica la profundidad y el tamaño del punto representa la magnitud.
        
        **¿Para qué sirve?**  
        Permite identificar patrones espaciales en la distribución de profundidades
        y su relación con la magnitud de los sismos.
    """)
    
    # Crear figura para el gráfico
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Crear gráfico de dispersión
    scatter = ax.scatter(
        sismos_df['longitud'],  # Eje X: Longitud
        sismos_df['latitud'],   # Eje Y: Latitud
        c=sismos_df['profundidad'],  # Color basado en profundidad
        cmap='viridis',  # Mapa de colores
        alpha=0.6,  # Transparencia de los puntos
        s=sismos_df['magnitud'] * 10  # Tamaño basado en magnitud
    )
    
    # Configurar etiquetas y título
    ax.set_xlabel('Longitud')  # Etiqueta del eje X
    ax.set_ylabel('Latitud')   # Etiqueta del eje Y
    ax.set_title('Distribución de Profundidad de Sismos')  # Título del gráfico
    
    # Añadir barra de colores para profundidad
    cbar = plt.colorbar(scatter)
    cbar.set_label('Profundidad (km)')  # Etiqueta de la barra de colores
    
    # Añadir cuadrícula para mejor lectura
    plt.grid(True, alpha=0.2)
    
    # Mostrar el gráfico en la aplicación
    st.pyplot(fig)

# =============================================================================
# PESTAÑA 3: CLÚSTERES ESPACIALES
# =============================================================================
with tab3:
    st.header("Identificación de Agrupamientos Sísmicos")
    st.markdown("""
        **¿Qué muestra esta sección?**  
        Utiliza el algoritmo DBSCAN para identificar zonas de alta densidad sísmica (clústeres).
        Cada color representa un grupo diferente de actividad sísmica.
        
        **¿Para qué sirve?**  
        Ayuda a identificar áreas con actividad sísmica recurrente, lo que puede indicar:
        - Fallas geológicas activas
        - Zonas de mayor riesgo sísmico
        - Patrones de actividad que merecen mayor estudio
    """)
    
    # Preparar datos para clustering (solo coordenadas)
    coords = sismos_df[['latitud', 'longitud']].values
    
    # Normalizar datos (importante para algoritmos de clustering)
    scaler = StandardScaler()
    coords_scaled = scaler.fit_transform(coords)
    
    # =====================================
    # INTERFAZ PARA AJUSTAR PARÁMETROS
    # =====================================
    st.subheader("Ajuste de Parámetros del Algoritmo")
    st.markdown("""
        **¿Qué hacen estos parámetros?**  
        - **Radio de búsqueda (eps)**: Determina qué tan cerca deben estar los puntos para considerarse parte del mismo grupo.
        - **Mínimo de muestras**: Número mínimo de sismos cercanos para formar un grupo.
        
        **Consejo:** Experimenta con diferentes valores para obtener los grupos más significativos.
    """)
    
    # Controles deslizantes para ajustar parámetros del algoritmo
    eps = st.slider("Radio de búsqueda (eps)", 0.01, 1.0, 0.2, 0.01)
    min_samples = st.slider("Mínimo de muestras por clúster", 1, 50, 10)
    
    # Aplicar algoritmo DBSCAN con los parámetros seleccionados
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(coords_scaled)
    labels = db.labels_  # Obtener etiquetas de grupo para cada sismo
    
    # Calcular número de grupos identificados (excluyendo "ruido")
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    st.info(f"Se identificaron {n_clusters} zonas de alta actividad sísmica.")
    
    # Añadir etiquetas de grupo al DataFrame
    sismos_df['cluster'] = labels
    
    # =====================================
    # MAPA DE CLÚSTERES
    # =====================================
    st.subheader("Visualización de Agrupamientos")
    
    # Crear mapa base
    m = folium.Map(location=[-32.2935, -64.1810], zoom_start=6)
    
    # Paleta de colores para los diferentes grupos
    colors = [
        'red', 'blue', 'green', 'purple', 'orange', 
        'darkred', 'lightblue', 'pink', 'darkblue', 'gray'
    ]
    
    # Añadir marcadores al mapa, coloreados por grupo
    for _, row in sismos_df.iterrows():
        cluster_id = row['cluster']
        # Asignar color: negro para puntos que no pertenecen a ningún grupo
        if cluster_id == -1:
            color = 'black'  # "Ruido" - puntos aislados
        else:
            color = colors[cluster_id % len(colors)]  # Asignar color del grupo
        
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=3,
            popup=f"Cluster: {cluster_id} | Mag: {row['magnitud']}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7
        ).add_to(m)
    
    # Mostrar el mapa
    folium_static(m, width=1000, height=600)
    
    # =====================================
    # ESTADÍSTICAS DE LOS GRUPOS IDENTIFICADOS
    # =====================================
    st.subheader("Características de los Agrupamientos")
    
    if n_clusters > 0:
        # Calcular estadísticas para cada grupo
        cluster_stats = sismos_df[sismos_df['cluster'] != -1].groupby('cluster').agg({
            'latitud': 'mean',  # Latitud promedio del grupo
            'longitud': 'mean',  # Longitud promedio del grupo
            'magnitud': ['mean', 'max'],  # Magnitud media y máxima
            'profundidad': ['mean', 'min', 'max'],  # Estadísticas de profundidad
            'fecha': 'count'  # Cantidad de sismos en el grupo
        }).reset_index()
        
        # Renombrar columnas para mejor comprensión
        cluster_stats.columns = [
            'Cluster', 'Latitud Promedio', 'Longitud Promedio', 
            'Magnitud Media', 'Magnitud Máxima',
            'Profundidad Media', 'Profundidad Mínima', 'Profundidad Máxima',
            'Cantidad de Sismos'
        ]
        
        # Mostrar estadísticas ordenadas por cantidad de sismos
        st.dataframe(cluster_stats.sort_values('Cantidad de Sismos', ascending=False))
    else:
        st.warning("No se identificaron zonas de alta densidad sísmica con los parámetros actuales.")

# =============================================================================
# BOTÓN PARA VOLVER AL INICIO
# =============================================================================
# Este botón aparece en la barra lateral y permite regresar a la página principal
with st.sidebar:
    if st.button("🏠 Volver al Inicio"):
        # Usar la función switch_page para cambiar a app.py
        st.switch_page("app.py")
