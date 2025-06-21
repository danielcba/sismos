import streamlit as st
import pandas as pd
import numpy as np
import folium
import plotly.express as px
from folium.plugins import HeatMap
from streamlit_folium import folium_static
from supabase import create_client
from shapely import wkt
import geopandas as gpd
from shapely.geometry import Point, LineString

# Configuración de la página
st.set_page_config(
    page_title="Segmentación por Zonas",
    page_icon="🗺️",
    layout="wide"
)

st.title("Segmentación por Zonas")

# =============================================
# CONEXIÓN A LA BASE DE DATOS SUPABASE
# =============================================

# Credenciales de Supabase (base de datos PostgreSQL en la nube)
SUPABASE_URL = "https://dmgashfrjnhaduiifabr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRtZ2FzaGZyam5oYWR1aWlmYWJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4OTc5MDMsImV4cCI6MjA2MjQ3MzkwM30.vEld_xzy8Vcsz-0wBzZpTviWOKWi_OklLfTNP7JXDfo"

# Crear cliente de Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Función para obtener datos de fallas geológicas
def fetch_fallas_geologicas():
    """Obtiene los datos de fallas geológicas desde Supabase"""
    try:
        # Obtener datos de fallas
        response = supabase.table('fallas_geologicas').select('*').execute()
        
        if not response.data:
            return pd.DataFrame()
            
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error al cargar datos de fallas: {str(e)}")
        return pd.DataFrame()

# Función para obtener los nombres y ubicaciones de las fallas
def fetch_fallas_nombres():
    """Obtiene los nombres y ubicaciones de las fallas desde Supabase"""
    try:
        response = supabase.table('fallas_nombres').select('*').execute()
        
        if not response.data:
            return pd.DataFrame()
            
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error al cargar nombres de fallas: {str(e)}")
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error al cargar datos de fallas: {str(e)}")
        return pd.DataFrame()

# Función para obtener datos de sismos
def fetch_sismos_data():
    try:
        # Paginación para obtener todos los datos
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
        
        # Asegurar que las columnas necesarias existen y tienen el formato correcto
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S').dt.time
            
        return df
        
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return pd.DataFrame()

# Función para dividir en cuadrantes
def dividir_en_cuadrantes(df, n_divisiones=5):
    """Divide el área en n_divisiones x n_divisiones cuadrantes"""
    # Hacer una copia para no modificar el DataFrame original
    df = df.copy()
    
    # Eliminar filas con coordenadas nulas
    df = df.dropna(subset=['latitud', 'longitud'])
    
    if df.empty:
        return df, [], []
    
    min_lat, max_lat = df['latitud'].min(), df['latitud'].max()
    min_lon, max_lon = df['longitud'].min(), df['longitud'].max()
    
    # Ajustar los límites para incluir todo Córdoba con un pequeño margen
    lat_step = (max_lat - min_lat) / n_divisiones
    lon_step = (max_lon - min_lon) / n_divisiones
    
    # Crear límites de los cuadrantes
    lat_bins = [min_lat + i * lat_step for i in range(n_divisiones + 1)]
    lon_bins = [min_lon + i * lon_step for i in range(n_divisiones + 1)]
    
    # Asignar cada sismo a un cuadrante
    df['cuadrante_lat'] = pd.cut(df['latitud'], bins=lat_bins, labels=False, include_lowest=True)
    df['cuadrante_lon'] = pd.cut(df['longitud'], bins=lon_bins, labels=False, include_lowest=True)
    
    # Eliminar filas donde no se pudo asignar un cuadrante
    df = df.dropna(subset=['cuadrante_lat', 'cuadrante_lon'])
    
    # Convertir a enteros y crear etiqueta de cuadrante
    df['cuadrante_lat'] = df['cuadrante_lat'].astype(int)
    df['cuadrante_lon'] = df['cuadrante_lon'].astype(int)
    df['cuadrante'] = df['cuadrante_lat'].astype(str) + '_' + df['cuadrante_lon'].astype(str)
    
    return df, lat_bins, lon_bins

# Función para crear el mapa de calor por cuadrantes
def crear_mapa_cuadrantes(df, lat_bins, lon_bins):
    """Crea un mapa de calor por cuadrantes"""
    # Calcular centro del mapa
    center_lat = df['latitud'].mean()
    center_lon = df['longitud'].mean()
    
    # Crear mapa base
    m = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
    
    # Agregar capa de calor
    heat_data = [[row['latitud'], row['longitud']] for _, row in df.iterrows()]
    HeatMap(heat_data, radius=10).add_to(m)
    
    # Agregar líneas de cuadrícula
    for lat in lat_bins:
        folium.PolyLine(
            locations=[[lat, lon] for lon in [df['longitud'].min(), df['longitud'].max()]],
            color='gray',
            weight=2.0,  # Aumentado de 0.5 a 2.0 para mayor visibilidad
            opacity=0.8  # Aumentada la opacidad para mejor visibilidad
        ).add_to(m)
    
    for lon in lon_bins:
        folium.PolyLine(
            locations=[[lat, lon] for lat in [df['latitud'].min(), df['latitud'].max()]],
            color='gray',
            weight=1.5,  # Aumentado de 0.5 a 2.0 para mayor visibilidad
            opacity=0.8  # Aumentada la opacidad para mejor visibilidad
        ).add_to(m)
    
    return m

# Función para mostrar estadísticas por zona
def mostrar_estadisticas_por_zona(df):
    """Muestra estadísticas por zona"""
    if 'cuadrante' not in df.columns:
        st.warning("Primero debe dividir los datos en cuadrantes")
        return
    
    # Calcular estadísticas por cuadrante
    stats = df.groupby('cuadrante').agg({
        'magnitud': ['count', 'mean', 'max'],
        'profundidad': 'mean'
    }).round(2)
    
    stats.columns = ['Cantidad de Sismos', 'Magnitud Promedio', 'Magnitud Máxima', 'Profundidad Promedio']
    
    # Mostrar estadísticas
    st.subheader("Estadísticas por Zona")
    st.dataframe(stats.sort_values('Cantidad de Sismos', ascending=False))
    
    # Gráfico de barras de cantidad de sismos por zona
    st.subheader("Cantidad de Sismos por Zona")
    fig = px.bar(
        stats.sort_values('Cantidad de Sismos', ascending=False).reset_index(),
        x='cuadrante',
        y='Cantidad de Sismos',
        title='Cantidad de Sismos por Zona'
    )
    st.plotly_chart(fig, use_container_width=True)

# Cargar datos
sismos_df = fetch_sismos_data()

if not sismos_df.empty:
    # Crear pestañas
    tab1, tab2 = st.tabs(["Análisis por Cuadrantes", "Fallas Tectónicas"])
    
    with tab1:
        st.header("Análisis por Cuadrantes")
        st.markdown("""
            Este análisis divide la provincia de Córdoba en cuadrantes para analizar la distribución 
            espacial de la actividad sísmica. Cada cuadrante muestra la frecuencia y características 
            de los sismos en esa zona.
        """)
        
        # Dividir en cuadrantes
        n_divisiones = st.slider("Número de divisiones por eje", 3, 10, 5)
        sismos_df, lat_bins, lon_bins = dividir_en_cuadrantes(sismos_df, n_divisiones)
        
        # Mostrar mapa de calor por cuadrantes
        st.subheader("Mapa de Calor por Cuadrantes")
        mapa_calor = crear_mapa_cuadrantes(sismos_df, lat_bins, lon_bins)
        folium_static(mapa_calor, width=1000, height=600)
        
        # Mostrar estadísticas por zona
        mostrar_estadisticas_por_zona(sismos_df)
    
    with tab2:
        st.header("Fallas Tectónicas")
        st.markdown("""
            Visualización de las fallas tectónicas conocidas en la provincia de Córdoba.
            Los círculos rojos representan sismos, mientras que las líneas azules representan fallas.
        """)
        
        # Crear mapa base centrado en Córdoba
        m = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
        
        # Agregar sismos al mapa
        for _, sismo in sismos_df.iterrows():
            folium.CircleMarker(
                location=[sismo['latitud'], sismo['longitud']],
                radius=2 + sismo['magnitud'],
                color='red',
                fill=True,
                fill_opacity=0.3,
                weight=1,
                popup=f"""
                    Magnitud:{sismo['magnitud']:.1f}<br>
                    Profundidad:{sismo['profundidad']}km<br>
                    Fecha:{sismo['fecha'].strftime('%Y-%m-%d')}<br>
                    Hora:{sismo['hora']}<br>
                    Magnitud:{sismo['magnitud']}<br>
                    Profundidad:{sismo['profundidad']}km
                    Latitud:{sismo['latitud']}<br>
                    Longitud:{sismo['longitud']}<br>
                """
            ).add_to(m)
        
        # Cargar fallas geológicas
        fallas_df = fetch_fallas_geologicas()
        # Ya no es necesario cargar ni procesar fallas_nombres
        # Los nombres están en la columna 'nombre_falla' de fallas_df
        

        
        if not fallas_df.empty:
            # Crear un grupo de capas para las fallas
            fg_fallas = folium.FeatureGroup(name="Fallas Geológicas", show=True)
            
            # Procesar cada falla
            for _, falla in fallas_df.iterrows():
                if not falla['geom']:
                    continue
                    
                try:
                    # Verificar si hay datos de geometría
                    if pd.isna(falla.get('geom')) or not falla['geom']:
                        continue
                        
                    # Manejar diferentes formatos de geometría
                    geom = falla['geom']
                    
                    # Si es un diccionario
                    if isinstance(geom, dict):
                        geom_type = geom.get('type', '').upper()
                        
                        if geom_type == 'LINESTRING':
                            coords = geom.get('coordinates', [])
                            if coords and len(coords) >= 2:
                                # Convertir coordenadas a formato Folium (lat, lon)
                                folium_coords = [(lat, lon) for lon, lat in coords]
                                folium.PolyLine(
                                    locations=folium_coords,
                                    color='blue',
                                    weight=1,
                                    opacity=0.9,
                                    popup=falla.get('nombre_falla', 'Falla sin nombre')
                                ).add_to(fg_fallas)
                                continue
                    
                    # Si no es un diccionario o no se pudo procesar, intentar como string
                    geom_str = str(geom).strip().upper()
                    st.write(f"Geometría en crudo: {geom_str[:100]}..." if len(geom_str) > 100 else f"Geometría en crudo: {geom_str}")
                    
                    # Extraer coordenadas del WKT (asumiendo formato POINT o LINESTRING)
                    if 'POINT' in geom_str:
                        # Para puntos
                        try:
                            coords_str = geom_str.split('(')[-1].replace(')', '').strip()
                            coords = [c.strip() for c in coords_str.split() if c.strip()]
                            if len(coords) >= 2:
                                lon, lat = map(float, coords[:2])
                                folium.CircleMarker(
                                    location=[lat, lon],
                                    radius=5,  # Aumentado para mejor visibilidad
                                    color='blue',
                                    fill=True,
                                    fill_opacity=0.9,
                                    popup=falla.get('nombre_falla', 'Falla sin nombre')
                                ).add_to(fg_fallas)
                                st.success(f"Punto añadido en {lat}, {lon}")
                            else:
                                st.warning(f"Formato de POINT inválido: {geom_str}")
                        except Exception as e:
                            st.error(f"Error procesando POINT: {str(e)}")
                    
                    elif 'LINESTRING' in geom_str:
                        # Para líneas
                        try:
                            coords_part = geom_str.split('(', 1)[1].rsplit(')', 1)[0]
                            coords_str = coords_part.split('(', 1)[-1].rsplit(')', 1)[0]
                            coords = []
                            for coord_pair in coords_str.split(','):
                                parts = [c.strip() for c in coord_pair.strip().split() if c.strip()]
                                if len(parts) >= 2:
                                    coords.append((float(parts[0]), float(parts[1])))
                            
                            if len(coords) >= 2:
                                folium_coords = [(lat, lon) for lon, lat in coords]
                                folium.PolyLine(
                                    locations=folium_coords,
                                    color='blue',
                                    weight=3,  # Aumentado para mejor visibilidad
                                    opacity=0.9,
                                    popup=falla.get('nombre_falla', 'Falla sin nombre')
                                ).add_to(fg_fallas)
                                st.success(f"Línea añadida con {len(folium_coords)} puntos")
                            else:
                                st.warning(f"No hay suficientes coordenadas en LINESTRING: {geom_str}")
                        except Exception as e:
                            st.error(f"Error procesando LINESTRING: {str(e)}")
                    else:
                        st.warning(f"Tipo de geometría no soportado: {geom_str.split(' ')[0] if geom_str else 'vacío'}")
                
                except Exception as e:
                    st.warning(f"Error al procesar falla: {str(e)}")
                    continue
            
            # Añadir el grupo de fallas al mapa
            fg_fallas.add_to(m)
            

            
            # Añadir control de capas
            folium.LayerControl().add_to(m)
        else:
            st.warning("No se encontraron datos de fallas geológicas.")
        
        # Mostrar el mapa
        folium_static(m, width=1000, height=600)
        

else:
    st.warning("No se pudieron cargar los datos de sismos. Por favor, intente más tarde.")
