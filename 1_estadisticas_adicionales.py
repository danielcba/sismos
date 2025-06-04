import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import random
from supabase import create_client
from datetime import datetime, time

# Función para mostrar mensajes de estado
def mostrar_mensaje_estado(resultado, tipo_filtro=None):
    if resultado.empty:
        mensaje = "No se encontraron sismos"
        if tipo_filtro:
            mensaje += f" que cumplan con los criterios de {tipo_filtro}"
        st.warning(mensaje)
        return False
    return True

# Configuración de la página
st.set_page_config(
    page_title="Estadísticas Adicionales",
    page_icon="📊",
    layout="wide"
)

st.title("Estadísticas Adicionales")

# USAR LAS MISMAS CREDENCIALES QUE EN APP.PY
SUPABASE_URL = "https://dmgashfrjnhaduiifabr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRtZ2FzaGZyam5oYWR1aWlmYWJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4OTc5MDMsImV4cCI6MjA2MjQ3MzkwM30.vEld_xzy8Vcsz-0wBzZpTviWOKWi_OklLfTNP7JXDfo"

# Función para obtener todos los datos
def fetch_all_sismos_data():
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
        
        # Procesar datos como en app.py
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['hora'] = pd.to_datetime(df['hora']).dt.time
            df['hora_num'] = df['hora'].apply(lambda x: x.hour + x.minute/60)
        
        return df
        
    except Exception as e:
        st.error(f"Error al cargar todos los datos: {str(e)}")
        return pd.DataFrame()

# Función para calcular el conteo por hora
def calcular_conteo_por_hora(df):
    if df.empty:
        return pd.DataFrame()
    
    # Crear una columna con la hora como entero
    df['hora_entero'] = df['hora'].apply(lambda x: x.hour)
    
    # Contar sismos por hora
    conteo = df['hora_entero'].value_counts().reset_index()
    conteo.columns = ['hora', 'cantidad']
    
    # Rellenar horas faltantes (0-23)
    horas_completas = pd.DataFrame({'hora': range(24)})
    conteo_completo = horas_completas.merge(conteo, on='hora', how='left').fillna(0)
    
    return conteo_completo

# Inicializar datos en session_state
if 'sismos_filtro' not in st.session_state:
    st.session_state.sismos_filtro = fetch_all_sismos_data()

# Calcular conteo por hora
if 'sismos_por_hora' not in st.session_state:
    if not st.session_state.sismos_filtro.empty:
        st.session_state.sismos_por_hora = calcular_conteo_por_hora(st.session_state.sismos_filtro)
    else:
        st.session_state.sismos_por_hora = pd.DataFrame()

# Si no hay datos reales, usar datos de muestra
if st.session_state.sismos_por_hora.empty or st.session_state.sismos_filtro.empty:
    st.warning("Usando datos de muestra para desarrollo")
    
    # Generar datos completos de muestra
    fechas = pd.date_range(start='2020-01-01', end='2023-12-31', periods=1000)
    horas_list = [time(hour=random.randint(0, 23), minute=random.randint(0, 59)) for _ in range(1000)]
    
    st.session_state.sismos_filtro = pd.DataFrame({
        'fecha': fechas,
        'hora': horas_list,
        'latitud': np.random.uniform(-33.0, -31.0, 1000),
        'longitud': np.random.uniform(-65.0, -63.0, 1000),
        'magnitud': np.random.uniform(0.5, 6.0, 1000),
        'profundidad': np.random.uniform(5, 200, 1000),
        'hora_num': [h.hour + h.minute/60 for h in horas_list]
    })
    
    # Calcular conteo por hora para los datos de muestra
    st.session_state.sismos_por_hora = calcular_conteo_por_hora(st.session_state.sismos_filtro)

# Mostrar estadísticas generales
if not st.session_state.sismos_por_hora.empty:
    total_sismos = int(st.session_state.sismos_por_hora['cantidad'].sum())
    idxmax = st.session_state.sismos_por_hora['cantidad'].idxmax()
    hora_pico = st.session_state.sismos_por_hora.loc[idxmax]
    hora_pico_valor = int(hora_pico['hora'])
    hora_pico_cantidad = int(hora_pico['cantidad'])
    
    st.info(f"**Estadísticas generales:** {total_sismos} sismos registrados | Hora pico: {hora_pico_valor}:00 ({hora_pico_cantidad} sismos)")

# Distribución horaria de sismos

with st.expander("Distribución Horaria de Sismos", expanded=True):
    st.subheader("Distribución Horaria de Sismos")
    
    if not st.session_state.sismos_por_hora.empty:
        datos = st.session_state.sismos_por_hora.copy()
        
        fig = go.Figure()
        
        # Agregar barras (igual que antes)
        fig.add_trace(go.Bar(
            x=datos['hora'],
            y=datos['cantidad'],
            name='Sismos por hora',
            marker_color='#ff7f0e',
            marker_line=dict(color='white', width=1),
            hovertemplate='<b>Hora: %{x}:00</b><br>Sismos: %{y}<extra></extra>'
        ))
        
        # Calcular línea de tendencia REAL con suavizado
        window_size = 3  # Tamaño de la ventana para el suavizado
        datos['tendencia'] = datos['cantidad'].rolling(
            window=window_size,
            center=True,
            min_periods=1
        ).mean()
        
        # Agregar VERDADERA línea de tendencia
        fig.add_trace(go.Scatter(
            x=datos['hora'],
            y=datos['tendencia'],
            mode='lines',
            name='Tendencia',
            line=dict(color='cyan', width=1),
            hovertemplate='<b>Hora: %{x}:00</b><br>Tendencia: %{y:.1f} sismos<extra></extra>'
        ))
        
        # Agregar línea de promedio general
        promedio = datos['cantidad'].mean()
        fig.add_hline(
            y=promedio,
            line_dash="dash",
            line_color='green',
            line_width=1,
            annotation_text=f'Promedio: {promedio:.1f} sismos/hora',
            annotation_position="top right"
        )
        
        # Personalizar layout (igual que antes)
        fig.update_layout(
            title='Distribución de Sismos por Hora del Día',
            xaxis=dict(title='Hora del día', tickvals=list(range(0, 24))),
            yaxis=dict(title='Número de Sismos'),
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)

# Sección adicional para análisis detallado
with st.expander("Análisis Detallado por Hora"):
    if not st.session_state.sismos_por_hora.empty:
        st.subheader("Datos por Hora")
        
        # Mostrar tabla con datos
        st.dataframe(st.session_state.sismos_por_hora.rename(columns={
            'hora': 'Hora',
            'cantidad': 'Cantidad de Sismos'
        }).style.format({'Hora': '{:.0f}'}), height=300)
        
        # Estadísticas avanzadas
        st.subheader("Estadísticas Avanzadas")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            idx_max = st.session_state.sismos_por_hora['cantidad'].idxmax()
            hora_max = int(st.session_state.sismos_por_hora.loc[idx_max]['hora'])
            cantidad_max = int(st.session_state.sismos_por_hora.loc[idx_max]['cantidad'])
            st.metric(
                "Hora con más sismos", 
                f"{hora_max}:00 - {hora_max+1}:00",
                delta=f"{cantidad_max} sismos"
            )
        
        with col2:
            idx_min = st.session_state.sismos_por_hora['cantidad'].idxmin()
            hora_min = int(st.session_state.sismos_por_hora.loc[idx_min]['hora'])
            cantidad_min = int(st.session_state.sismos_por_hora.loc[idx_min]['cantidad'])
            st.metric(
                "Hora con menos sismos", 
                f"{hora_min}:00 - {hora_min+1}:00",
                delta=f"{cantidad_min} sismos"
            )
        
        with col3:
            promedio = float(st.session_state.sismos_por_hora['cantidad'].mean())
            st.metric(
                "Promedio por hora", 
                value=f"{promedio:.1f} sismos/hora"
            )