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
import plotly.graph_objects as go  # Para gráficos interactivos

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

def fetch_sismos_mismas_coordenadas():
    """Obtiene los sismos que ocurrieron en las mismas coordenadas."""
    try:
        # Obtener todos los datos y procesar localmente
        st.info("Obteniendo y procesando datos de sismos...")
        df = fetch_sismos_data()
        
        if not df.empty:
            # Redondear coordenadas a 4 decimales para agrupar ubicaciones cercanas
            df['lat_rounded'] = df['latitud'].round(4)
            df['lon_rounded'] = df['longitud'].round(4)
            
            # Contar sismos por ubicación redondeada
            coord_counts = df.groupby(['lat_rounded', 'lon_rounded']).size().reset_index(name='count')
            
            # Filtrar solo ubicaciones con más de un sismo
            duplicated_coords = coord_counts[coord_counts['count'] > 1][['lat_rounded', 'lon_rounded']]
            
            if not duplicated_coords.empty:
                # Unir con los datos originales para obtener todos los campos
                result = pd.merge(
                    df, 
                    duplicated_coords, 
                    left_on=['lat_rounded', 'lon_rounded'],
                    right_on=['lat_rounded', 'lon_rounded']
                )
                
                # Ordenar por ubicación, fecha y hora
                result = result.sort_values(by=['lat_rounded', 'lon_rounded', 'fecha', 'hora'])
                
                # Eliminar columnas temporales
                result = result.drop(columns=['lat_rounded', 'lon_rounded'])
                
                return result
            
        st.warning("No se encontraron ubicaciones con múltiples sismos.")
        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error al procesar sismos en las mismas coordenadas: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return pd.DataFrame()

# Mostrar mensaje si no hay datos
if sismos_df.empty:
    st.warning("No se encontraron datos de sismos.")
    st.stop()

# Crear pestañas para los diferentes análisis
tab1, tab2, tab3, tab4 = st.tabs([
    "Mapa de Calor Geográfico", 
    "Profundidad vs. Ubicación", 
    "Clústeres Espaciales",
    "Sismos en Coordenadas Iguales"
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
    m = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
    
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
        - **🟢 Verde**: Sismos profundos (>70 km)
    """)
    
    # Crear mapa base
    m = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
    
    # Función para determinar color según profundidad
    def get_color(profundidad):
        if profundidad < 30:
            return 'red'
        elif profundidad < 70:
            return 'orange'
        else:
            return 'green'
    
    # Añadir marcadores circulares para cada sismo
    for _, row in sismos_df.iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            # Radio proporcional a la magnitud
            radius=2 + row['magnitud'] * 1.2,
            # Popup con información detallada
            popup=f"""
                Fecha:{row['fecha'].strftime('%Y-%m-%d')}<br>
                Hora:{row['hora']}<br>
                Magnitud:{row['magnitud']}<br>
                Profundidad:{row['profundidad']}km
                Latitud:{row['latitud']}<br>
                Longitud:{row['longitud']}<br>
            """,
            color=get_color(row['profundidad']),  # Color del borde según profundidad
            fill=True,                            # Rellenar el círculo
            fill_color=get_color(row['profundidad']),  # Color de relleno según profundidad
            fill_opacity=0.3,                     # Transparencia del relleno
            weight=0.5                            # Grosor del borde
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
# Pestaña 3: Clústeres Espaciales
# =============================================

with tab3:
    st.header("Identificación de Agrupamientos Sísmicos")
    st.markdown("""
        Se aplica el algoritmo DBSCAN para identificar zonas de alta densidad sísmica (clústeres).
        
        **Leyenda de colores:**
        - **Cada color**: Representa un cluster diferente de actividad sísmica
        - **⚫ Negro**: Sismos aislados que no pertenecen a ningún cluster
        
        **Parámetros:**
        - **Radio de búsqueda (km-fórmula de Haversine)**: Distancia máxima entre sismos para considerarlos parte del mismo cluster
        - **Mínimo de muestras**: Número mínimo de sismos cercanos para formar un cluster
    """)
    
    # Función para calcular distancia en km entre coordenadas (Haversine)
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

    # Preparamos los datos para clustering
    coords = sismos_df[['latitud', 'longitud']].values
    
    # Parámetros ajustables por el usuario (EN KILÓMETROS)
    eps_km = st.slider("Radio de búsqueda (km)", 0.1, 50.0, 11.0, 0.1)
    min_samples = st.slider("Mínimo de muestras por cluster", 1, 50, 4)
    
    # SOLUCIÓN AL PROBLEMA: Usar una implementación más eficiente de DBSCAN con métrica de Haversine
    if len(coords) > 0:
        with st.spinner("Identificando clusters de sismos..."):
            # Crear matriz de distancias (solo si hay menos de 2000 puntos para evitar sobrecarga)
            if len(coords) < 2000:
                # Calcular matriz de distancias
                dist_matrix = np.zeros((len(coords), len(coords)))
                for i in range(len(coords)):
                    for j in range(i+1, len(coords)):
                        dist = haversine_distance(
                            coords[i, 0], coords[i, 1],
                            coords[j, 0], coords[j, 1]
                        )
                        dist_matrix[i, j] = dist
                        dist_matrix[j, i] = dist
                
                # Aplicar DBSCAN con la matriz de distancias
                db = DBSCAN(eps=eps_km, min_samples=min_samples, metric="precomputed").fit(dist_matrix)
                labels = db.labels_
            else:
                # Para grandes conjuntos de datos, usar una aproximación más eficiente
                # Convertir a radianes para usar la métrica de Haversine directamente
                coords_rad = np.radians(coords)
                db = DBSCAN(eps=eps_km/6371, min_samples=min_samples, 
                            metric='haversine', algorithm='ball_tree').fit(coords_rad)
                labels = db.labels_
    else:
        labels = np.array([])
    
    # Número de clusters encontrados (excluyendo ruido)
    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
    
    # Contar sismos por cluster
    cluster_counts = {label: np.sum(labels == label) for label in unique_labels if label != -1}
    
    # Filtrar clusters que realmente tienen el mínimo de muestras requerido
    valid_clusters = [label for label, count in cluster_counts.items() if count >= min_samples]
    n_valid_clusters = len(valid_clusters)
    
    # Información estadística
    n_ruido = np.sum(labels == -1)
    n_sismos_grupos = len(labels) - n_ruido
    
    st.info(f"""
        **Resultados:**
        - clusters identificados: {n_valid_clusters}
        - Sismos en clusters: {n_sismos_grupos}
        - Sismos aislados (negros): {n_ruido}
    """)
    
    # Añadir etiquetas al DataFrame
    sismos_df['cluster'] = labels
    
    # Crear mapa
    m = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
    
    # Paleta de colores para los clusters
    colors = [
        'red', 'blue', 'green', 'purple', 'orange', 
        'darkred', 'darkblue', 'darkgreen', 'magenta', 'cyan',
        'lime', 'teal', 'navy', 'maroon', 'olive'
    ]
    
    # Añadir marcadores por cluster
    for _, row in sismos_df.iterrows():
        cluster_id = row['cluster']
        
        # Solo mostrar clusters válidos (que cumplen con min_samples)
        if cluster_id == -1 or cluster_id not in valid_clusters:
            color = 'black'
            popup_text = "Sismo aislado"
        else:
            # Usar colores cíclicos para cualquier número de clusters
            color_idx = cluster_id % len(colors)
            color = colors[color_idx]
            popup_text = f"cluster:{cluster_id}<br>Sismos:{cluster_counts[cluster_id]}"
        
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            # Radio proporcional a la magnitud (igual que en la página principal)
            radius=2 + row['magnitud'] * 1.2,
            popup=f"""
                {popup_text}<br>
                Fecha:{row['fecha'].strftime('%Y-%m-%d')}<br>
                Hora:{row['hora']}<br>
                Magnitud:{row['magnitud']}<br>
                Profundidad:{row['profundidad']}km
                Latitud:{row['latitud']}<br>
                Longitud:{row['longitud']}<br>
            """,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.3,  # Misma opacidad que en la página principal
            weight=0.5  # Mismo grosor de borde que en la página principal
        ).add_to(m)
    
    # Mostrar mapa
    folium_static(m, width=1000, height=600)
    
    # Estadísticas de clusters
    st.subheader("Características de los Agrupamientos")
    if n_valid_clusters > 0:
        # Filtrar solo clusters válidos
        clusters_validos = sismos_df[sismos_df['cluster'].isin(valid_clusters)]
        
        cluster_stats = clusters_validos.groupby('cluster').agg({
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
        
        # Mostrar distribución de sismos por cluster con estilo mejorado
        cluster_counts = clusters_validos['cluster'].value_counts().sort_index()
        
        fig = go.Figure()
        
        # Agregar barras con colores según el cluster
        for i, (cluster_id, count) in enumerate(cluster_counts.items()):
            color_idx = cluster_id % len(colors)
            color = colors[color_idx]
            
            fig.add_trace(go.Bar(
                x=[f'Cluster {int(cluster_id)}'],
                y=[count],
                name=f'Cluster {int(cluster_id)}',
                marker_color=color,
                marker_line=dict(color='white', width=1),
                hovertemplate='<b>%{x}</b><br>Sismos: %{y}<extra></extra>',
                showlegend=False
            ))
        
        # Calcular y agregar línea de promedio
        promedio = cluster_counts.mean()
        fig.add_hline(
            y=promedio,
            line_dash="dash",
            line_color='green',
            line_width=1,
            annotation_text=f'Promedio: {promedio:.1f} sismos/cluster',
            annotation_position="top right"
        )
        
        # Personalizar layout
        fig.update_layout(
            title='Distribución de Sismos por Cluster',
            xaxis=dict(title='Cluster'),
            yaxis=dict(title='Número de Sismos'),
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            hovermode='x unified',
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.warning("No se identificaron zonas de alta densidad sísmica con los parámetros actuales.")

# =============================================
# Pestaña 4: Sismos en Mismas Coordenadas
# =============================================

with tab4:
    st.header("Sismos en las Mismas Coordenadas")
    st.markdown("""
        Este mapa muestra los sismos que han ocurrido en las mismas coordenadas geográficas.
        Cada grupo de sismos en la misma ubicación está conectado visualmente.
    """)
    
    # Obtener datos de sismos en las mismas coordenadas
    sismos_mismas_coords = fetch_sismos_mismas_coordenadas()
    
    if sismos_mismas_coords.empty:
        st.warning("No se encontraron sismos en las mismas coordenadas.")
    else:
        # Crear mapa centrado en Córdoba
        m = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
        
        # Función para obtener un color único por ubicación
        def get_location_color(lat, lon):
            # Usar una combinación de lat y lon para generar un color único
            return f'#{hash(f"{lat}_{lon}") % 0xFFFFFF:06x}'
        
        # Redondear coordenadas para agrupar ubicaciones cercanas
        sismos_mismas_coords['lat_rounded'] = sismos_mismas_coords['latitud'].round(4)
        sismos_mismas_coords['lon_rounded'] = sismos_mismas_coords['longitud'].round(4)
        
        # Agrupar por coordenadas redondeadas
        grouped = sismos_mismas_coords.groupby(['lat_rounded', 'lon_rounded'])
        
        for (lat, lon), group in grouped:
            count = len(group)
            if count < 2:  # Solo mostrar ubicaciones con al menos 2 sismos
                continue
                
            location_color = get_location_color(lat, lon)
            
            # Ordenar por fecha y hora
            group = group.sort_values(by=['fecha', 'hora'])
            
            # Crear contenido del popup para esta ubicación
            popup_content = """
            <div style='max-width: 300px; max-height: 400px; overflow-y: auto;'>
                <div style='padding: 10px; background-color: #f8f9fa; border-radius: 5px;'>
                    <h4 style='margin: 0 0 10px 0; color: #2c3e50;'>Sismos en esta ubicación</h4>
                    <p style='margin: 5px 0;'><strong>Coordenadas:</strong> {lat:.4f}°, {lon:.4f}°</p>
                    <p style='margin: 5px 0;'><strong>Total de sismos:</strong> {count}</p>
                    <hr style='margin: 10px 0;'>
                    <div style='margin-top: 10px;'>
            """.format(lat=lat, lon=lon, count=count)
            
            # Agregar cada sismo al popup
            for _, sismo in group.iterrows():
                # Asegurar que la fecha y hora sean cadenas
                fecha_str = str(sismo['fecha']).split()[0] if pd.notnull(sismo['fecha']) else 'N/A'
                hora_str = str(sismo['hora']).split()[-1] if pd.notnull(sismo['hora']) else 'N/A'
                
                # Usar un color de borde consistente para todos los sismos de esta ubicación
                border_color = location_color.lstrip('#')
                border_style = f'4px solid #{border_color}'
                
                # Crear el contenido del sismo usando solo .format() para evitar problemas
                sismo_html = """
                    <div style='margin-bottom: 12px; padding: 8px; background-color: #ffffff; 
                                border-left: 4px solid {color}; 
                                border-radius: 0 4px 4px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);'>
                        <div style='font-weight: bold; color: #2c3e50; margin-bottom: 4px;'>
                            {fecha} a las {hora}
                        </div>
                        <div style='display: flex; justify-content: space-between;'>
                            <span><strong>Magnitud:</strong> {mag:.1f}</span>
                            <span><strong>Profundidad:</strong> {prof} km</span>
                        </div>
                    </div>
                """.format(
                    color=location_color,
                    fecha=fecha_str,
                    hora=hora_str,
                    mag=sismo['magnitud'],
                    prof=sismo['profundidad']
                )
                popup_content += sismo_html
            
            popup_content += """
                    </div>
                </div>
            </div>
            """
            
            # Obtener la magnitud máxima del grupo
            magnitud_maxima = group['magnitud'].max()
            
            # Calcular radio basado en la magnitud (misma fórmula que en otras pestañas)
            radio = 2 + magnitud_maxima * 1.2
            
            # Crear marcador con popup que solo se activa al hacer clic
            marker = folium.CircleMarker(
                location=[lat, lon],
                radius=radio,  # Radio proporcional a la magnitud
                popup=folium.Popup(popup_content, max_width=350),
                color=location_color,  # Color único por ubicación
                fill=True,
                fill_color=location_color,  # Mismo color para el relleno
                fill_opacity=3,  # 70% de opacidad para el relleno
                weight=0.5,  # Borde más fino para mejor apariencia
                tooltip=None  # Sin tooltip al pasar el mouse
            )
            marker.add_to(m)
        
        # Mostrar el mapa
        folium_static(m, width=1000, height=600)
        
        # Mostrar tabla con los datos
        with st.expander("Ver datos detallados", expanded=False):
            st.subheader("Datos de sismos en las mismas coordenadas")
            
            # Crear una versión resumida para la tabla
            resumen = sismos_mismas_coords.groupby(
                ['latitud', 'longitud']
            ).agg({
                'fecha': ['count', 'min', 'max'],
                'magnitud': ['min', 'max', 'mean'],
                'profundidad': ['min', 'max', 'mean']
            }).reset_index()
            
            # Aplanar el MultiIndex de columnas
            resumen.columns = ['_'.join(col).strip('_') for col in resumen.columns.values]
            
            # Renombrar columnas para mejor legibilidad
            resumen = resumen.rename(columns={
                'latitud_': 'Latitud',
                'longitud_': 'Longitud',
                'fecha_count': 'Total Sismos',
                'fecha_min': 'Primera Fecha',
                'fecha_max': 'Última Fecha',
                'magnitud_min': 'Mín. Magnitud',
                'magnitud_max': 'Máx. Magnitud',
                'magnitud_mean': 'Prom. Magnitud',
                'profundidad_min': 'Mín. Prof. (km)',
                'profundidad_max': 'Máx. Prof. (km)',
                'profundidad_mean': 'Prom. Prof. (km)'
            })
            
            # Formatear fechas
            resumen['Primera Fecha'] = pd.to_datetime(resumen['Primera Fecha']).dt.strftime('%Y-%m-%d')
            resumen['Última Fecha'] = pd.to_datetime(resumen['Última Fecha']).dt.strftime('%Y-%m-%d')
            
            # Mostrar tabla
            st.dataframe(
                resumen.sort_values('Total Sismos', ascending=False),
                column_config={
                    'Latitud': st.column_config.NumberColumn(format='%.4f'),
                    'Longitud': st.column_config.NumberColumn(format='%.4f'),
                    'Prom. Magnitud': st.column_config.NumberColumn(format='%.2f'),
                    'Prom. Prof. (km)': st.column_config.NumberColumn(format='%.1f')
                }
            )
