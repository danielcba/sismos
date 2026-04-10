import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import psycopg2
from shapely import wkt
from shapely.geometry import Point
from supabase import create_client
import json
import plotly.express as px

# Configuración de la página
st.set_page_config(
    page_title="Mapa de Departamentos",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Mapa de Departamentos de Córdoba")

# Credenciales de Supabase (mismas que en app.py)
SUPABASE_URL = "https://db.dmgashfrjnhaduiifabr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRtZ2FzaGZyam5oYWR1aWlmYWJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4OTc5MDMsImV4cCI6MjA2MjQ3MzkwM30.vEld_xzy8Vcsz-0wBzZpTviWOKWi_OklLfTNP7JXDfo"

# Función para obtener datos de departamentos
def fetch_departamentos_data():
    try:
        # Conexión directa a PostgreSQL para datos geográficos
        conn = psycopg2.connect(
            dbname='postgres',
            user='postgres',
            password='Ozzy153624+$',
            host='dmgashfrjnhaduiifabr.supabase.co',
            port='5432'
        )
        cur = conn.cursor()
        
        # Obtener departamentos
        cur.execute("SELECT nombre, ST_AsText(geom) FROM departamentos;")
        departamentos_rows = cur.fetchall()
        
        # Obtener cabeceras
        cur.execute("SELECT departamento, cabecera, ST_AsText(geom) FROM cabeceras;")
        cabeceras = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Crear diccionario de cabeceras para fácil acceso
        cabeceras_dict = {depto: cabecera for depto, cabecera, _ in cabeceras}
        
        departamentos = []
        for nombre, geom_wkt in departamentos_rows:
            try:
                geom = wkt.loads(geom_wkt)
                
                # Para polígonos, obtener coordenadas del exterior
                if hasattr(geom, 'exterior'):
                    coords = [(x, y) for x, y in geom.exterior.coords]
                    center_lat = sum(y for x, y in coords) / len(coords)
                    center_lon = sum(x for x, y in coords) / len(coords)
                else:
                    # Para otros tipos de geometría
                    if hasattr(geom, 'coords'):
                        coords = list(geom.coords)
                        center_lat = sum(y for x, y in coords) / len(coords)
                        center_lon = sum(x for x, y in coords) / len(coords)
                    else:
                        continue
                
                departamentos.append({
                    'nombre': nombre,
                    'coords': coords,
                    'center': [center_lat, center_lon],
                    'geom': geom,
                    'cabecera': cabeceras_dict.get(nombre, 'Sin cabecera')
                })
                
            except Exception as e:
                continue
        
        return departamentos, cabeceras
        
    except Exception as e:
        st.error(f"Error al cargar datos de departamentos: {str(e)}")
        return [], []

# Función para obtener sismos
def fetch_sismos_data():
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Usar paginación como en app.py
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
        
        # Procesar datos
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['hora'] = pd.to_datetime(df['hora']).dt.time
        
        return df
        
    except Exception as e:
        st.error(f"Error al cargar datos de sismos: {str(e)}")
        return pd.DataFrame()

# Cargar datos
departamentos, cabeceras = fetch_departamentos_data()
sismos_df = fetch_sismos_data()

# Sidebar para filtros
st.sidebar.header("Filtros del Mapa")

# Filtro de magnitud
mag_min = st.sidebar.slider("Magnitud mínima", 0.0, 10.0, 0.0, 0.1)
mag_max = st.sidebar.slider("Magnitud máxima", 0.0, 10.0, 10.0, 0.1)

# Filtro de profundidad
prof_min = st.sidebar.slider("Profundidad mínima (km)", 0, 500, 0, 10)
prof_max = st.sidebar.slider("Profundidad máxima (km)", 0, 500, 500, 10)

# Opciones de visualización
mostrar_sismos = st.sidebar.checkbox("Mostrar sismos", value=True)
mostrar_cabeceras = st.sidebar.checkbox("Mostrar cabeceras", value=True)
mostrar_nombres = st.sidebar.checkbox("Mostrar nombres de departamentos", value=True)

# Filtrar sismos
sismos_filtrados = pd.DataFrame()
if not sismos_df.empty and mostrar_sismos:
    sismos_filtrados = sismos_df[
        (sismos_df['magnitud'] >= mag_min) & 
        (sismos_df['magnitud'] <= mag_max) &
        (sismos_df['profundidad'] >= prof_min) & 
        (sismos_df['profundidad'] <= prof_max)
    ].copy()

# Crear mapa centrado en Córdoba
if departamentos:
    m = folium.Map(
        location=[-32.2935, -63.7111],
        zoom_start=7,
        tiles='OpenStreetMap'
    )
    
        
    # Agregar marcadores en cabeceras con información unificada
    marcadores_agregados = 0
    for depto in departamentos:
        try:
            # Calcular cuántos sismos hay en este departamento
            depto_sismos_count = 0
            if not sismos_df.empty:
                depto_sismos = sismos_df[
                    sismos_df.apply(lambda row: depto['geom'].intersects(Point(row['longitud'], row['latitud'])), axis=1)
                ]
                depto_sismos_count = len(depto_sismos)
            
            # Mapeo manual para resolver discrepancias de nombres
            mapeo_nombres = {
                'colon': 'Colón',
                'general-rocca': 'General Roca',
                'general-san-martin': 'General San Martín',
                'ischilin': 'Ischilín',
                'juarez-celman': 'Juárez Celman',
                'marcos-juarez': 'Marcos Juárez',
                'presidente-roque-saenz-peña': 'Presidente Roque Sáenz Peña',
                'rio-cuarto': 'Río Cuarto',
                'rio-primero': 'Río Primero',
                'rio-seco': 'Río Seco',
                'rio-segundo': 'Río Segundo',
                'santa-maria': 'Santa María',
                'union': 'Unión'
            }
            
            # Obtener coordenadas de la cabecera
            cabecera_coords = None
            cabecera_nombre = None
            
            # Primero intentar coincidencia directa, luego usar mapeo
            depto_normalizado = depto['nombre'].lower().replace('-', '').replace('_', ' ')
            
            for departamento, cabecera, geom_wkt in cabeceras:
                # Normalizar nombre de la cabecera
                cab_depto_normalizado = departamento.lower().replace('-', '').replace('_', ' ')
                
                # Múltiples formas de comparación
                if (cab_depto_normalizado == depto_normalizado or
                    cab_depto_normalizado.replace(' ', '') == depto_normalizado.replace(' ', '') or
                    departamento.lower() == depto['nombre'].lower() or
                    departamento.replace('-', ' ').lower() == depto['nombre'].replace('-', ' ').lower()):
                    
                    punto = wkt.loads(geom_wkt)
                    cabecera_coords = [punto.y, punto.x]  # [lat, lon] para Folium
                    cabecera_nombre = cabecera
                    break
            
            # Si no se encontró, intentar con el mapeo manual
            if not cabecera_coords and depto['nombre'] in mapeo_nombres:
                nombre_buscado = mapeo_nombres[depto['nombre']]
                for departamento, cabecera, geom_wkt in cabeceras:
                    if departamento == nombre_buscado:
                        punto = wkt.loads(geom_wkt)
                        cabecera_coords = [punto.y, punto.x]
                        cabecera_nombre = cabecera
                        break
            
            if not cabecera_coords:
                continue
            
            # Color del marcador basado en la cantidad de sismos
            if depto_sismos_count == 0:
                marker_color = 'blue'
            elif depto_sismos_count < 10:
                marker_color = 'green'
            elif depto_sismos_count < 50:
                marker_color = 'orange'
            else:
                marker_color = 'red'
            
            # Crear popup con información unificada
            popup_content = f"""
            <div style="font-family: Arial, sans-serif; min-width: 250px;">
                <h4 style="margin: 0 0 10px 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">
                    {depto['nombre'].replace('-', ' ').title()}
                </h4>
                <p style="margin: 5px 0; font-size: 14px;">
                    <strong>Cabecera:</strong> {cabecera_nombre.replace('-', ' ').title() if cabecera_nombre else 'No disponible'}
                </p>
                <p style="margin: 5px 0; font-size: 14px;">
                    <strong>Sismos registrados:</strong> 
                    <span style="color: {'#e74c3c' if depto_sismos_count > 50 else '#f39c12' if depto_sismos_count > 10 else '#27ae60'}; font-weight: bold;">
                        {depto_sismos_count}
                    </span>
                </p>
                <p style="margin: 8px 0 0 0; font-size: 12px; color: #7f8c8d; font-style: italic;">
                    Coordenadas: [{cabecera_coords[0]:.4f}, {cabecera_coords[1]:.4f}]
                </p>
            </div>
            """
            
            # Crear marcador en la cabecera
            marker = folium.Marker(
                location=cabecera_coords,
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"{depto['nombre'].title()} | {depto_sismos_count} sismos" if mostrar_nombres else None,
                icon=folium.Icon(
                    color=marker_color,
                    icon='info-sign',
                    prefix='fa'
                )
            )
            marker.add_to(m)
            
            # Agregar etiqueta de nombre si está activado
            if mostrar_nombres:
                label_marker = folium.Marker(
                    location=cabecera_coords,
                    icon=folium.DivIcon(
                        html=f'''
                        <div style="
                            font-size: 12px; 
                            font-weight: bold; 
                            color: #2c3e50; 
                            background: rgba(255,255,255,0.9);
                            padding: 3px 6px;
                            border-radius: 4px;
                            border: 1px solid #3498db;
                            white-space: nowrap;
                            margin-top: -35px;
                            margin-left: 15px;
                        ">
                            {depto["nombre"].replace('-', ' ').title()}<br>
                            <small style="color: #7f8c8d;">({depto_sismos_count} sismos)</small>
                        </div>
                        ''',
                        icon_size=(150, 40),
                        icon_anchor=(0, 40)
                    )
                )
                label_marker.add_to(m)
                
        except Exception as e:
            continue
    
        
    # Agregar sismos
    if not sismos_filtrados.empty:
        for _, sismo in sismos_filtrados.iterrows():
            # Color según magnitud
            if sismo['magnitud'] < 2.5:
                color = 'green'
            elif sismo['magnitud'] < 3.5:
                color = 'orange'
            else:
                color = 'red'
            
            # Tamaño según magnitud
            radius = max(3, min(15, sismo['magnitud'] * 2))
            
            folium.CircleMarker(
                location=[sismo['latitud'], sismo['longitud']],
                radius=radius,
                popup=f"""
                <b>Sismo #{sismo['id']}</b><br>
                Fecha: {sismo['fecha'].strftime('%Y-%m-%d')}<br>
                Hora: {sismo['hora']}<br>
                Magnitud: {sismo['magnitud']}<br>
                Profundidad: {sismo['profundidad']} km
                """,
                color=color,
                fillColor=color,
                fillOpacity=0.4,
                opacity=0.7,
                weight=1
            ).add_to(m)
    
    # Mostrar mapa
    st.subheader("Mapa Interactivo")
    folium_static(m, width=1000, height=600)
    
    # Mostrar estadísticas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Departamentos", len(departamentos))
    
    with col2:
        st.metric("Cabeceras", len(cabeceras))
    
    with col3:
        if not sismos_filtrados.empty:
            st.metric("Sismos visibles", len(sismos_filtrados))
        else:
            st.metric("Sismos visibles", 0)
    
        
    # Tabla de sismos por departamento
    st.subheader("📊 Sismos por Departamento")
    
    if not sismos_df.empty and departamentos:
        # Función para asignar departamento a cada sismo
        def asignar_departamento(sismo_row):
            punto = Point(sismo_row['longitud'], sismo_row['latitud'])
            for depto in departamentos:
                if depto['geom'].intersects(punto):
                    return depto['nombre']
            return 'Sin departamento'
        
        # Crear una copia de los sismos y asignar departamento
        sismos_con_depto = sismos_df.copy()
        sismos_con_depto['departamento'] = sismos_con_depto.apply(asignar_departamento, axis=1)
        
        # Contar sismos por departamento
        sismos_por_depto = sismos_con_depto['departamento'].value_counts().reset_index()
        sismos_por_depto.columns = ['Departamento', 'Total de Sismos']
        
        # Calcular estadísticas adicionales
        stats_por_depto = sismos_con_depto.groupby('departamento').agg({
            'magnitud': ['mean', 'max', 'min'],
            'profundidad': 'mean'
        }).round(2)
        
        stats_por_depto.columns = ['Magnitud Promedio', 'Magnitud Máxima', 'Magnitud Mínima', 'Profundidad Promedio']
        stats_por_depto = stats_por_depto.reset_index()
        stats_por_depto.rename(columns={'departamento': 'Departamento'}, inplace=True)
        
        # Unir conteo con estadísticas
        tabla_completa = sismos_por_depto.merge(stats_por_depto, on='Departamento', how='left')
        
        # Ordenar por total de sismos (descendente)
        tabla_completa = tabla_completa.sort_values('Total de Sismos', ascending=False)
        
        # Mostrar tabla completa
        st.dataframe(
            tabla_completa,
            height=400,
            use_container_width=True
        )
        
        # Gráfico de barras de sismos por departamento
        st.subheader("📈 Distribución de Sismos por Departamento")
        
        # Tomar los 15 departamentos con más sismos para mejor visualización
        top_15_deptos = tabla_completa.head(15)
        
        fig = px.bar(
            top_15_deptos,
            x='Total de Sismos',
            y='Departamento',
            orientation='h',
            title='Top 15 Departamentos con Más Sismos',
            template='plotly_dark',
            color='Total de Sismos',
            color_continuous_scale='viridis'
        )
        
        fig.update_layout(
            height=600,
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title='Total de Sismos',
            yaxis_title='Departamento'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Estadísticas generales por departamento
        col1, col2, col3 = st.columns(3)
        
        with col1:
            depto_mas_sismos = tabla_completa.iloc[0]
            st.metric(
                "Departamento con más sismos",
                depto_mas_sismos['Departamento'],
                f"{depto_mas_sismos['Total de Sismos']} sismos"
            )
        
        with col2:
            promedio_por_depto = tabla_completa['Total de Sismos'].mean()
            st.metric(
                "Promedio de sismos por departamento",
                f"{promedio_por_depto:.1f}"
            )
        
        with col3:
            deptos_con_sismos = len(tabla_completa[tabla_completa['Total de Sismos'] > 0])
            st.metric(
                "Departamentos con sismos",
                f"{deptos_con_sismos}/{len(departamentos)}"
            )
    
else:
    st.error("No se pudieron cargar los datos de departamentos. Por favor, verifica la conexión a la base de datos.")
