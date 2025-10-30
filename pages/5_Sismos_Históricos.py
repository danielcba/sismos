import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import numpy as np
from datetime import datetime
import math
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Sismos Históricos de Córdoba",
    page_icon="📜",
    layout="wide"
)

st.title("Sismos Históricos Destacados de Córdoba")
st.markdown("""
Mapa de los sismos históricos más significativos registrados en la provincia de Córdoba.
Estos eventos representan los terremotos más importantes de la historia sísmica de la región.
""")

# Función para calcular energía liberada (consistente con 3_Energía_Liberada.py)
def energia_liberada(magnitud):
    """
    Calcula la energía liberada por un sismo en Joules usando la fórmula de Gutenberg-Richter:
    log10(E) = 1.5*M + 4.8
    """
    return 10 ** (1.5 * magnitud + 4.8)

# Función para formatear energía en notación simplificada
def formatear_energia_simplificada(joules):
    """
    Convierte joules a notación simplificada: B (Billones), T (Trillones)
    """
    if joules >= 1e12:
        return f"{joules/1e12:.0f}T"
    elif joules >= 1e9:
        return f"{joules/1e9:.0f}B"
    else:
        return f"{joules:.2e}"

# Parámetros científicos y eventos de comparación (consistentes con 3_Energía_Liberada.py)
eventos_comparacion = {
    "Rayo": 1e9,
    "1 tonelada de TNT": 4.2e9,
    "Bomba de Hiroshima": 6.3e13,
    "Erupción volcánica": 1e15,
    "Sismo M7": 2e15,
    "Sismo M8.5": 1e18
}

# Datos históricos de sismos (del CSV proporcionado)
DATOS_HISTORICOS = [
    {
        'fecha': '22/09/1908',
        'hora': '17:00:00',
        'latitud': -30.983,
        'longitud': -64.917,
        'profundidad': 100,
        'magnitud': 6.5,
        'descripcion': 'Terremoto de Cruz del Eje - Uno de los más destructivos'
    },
    {
        'fecha': '10/06/1934',
        'hora': '23:07:09',
        'latitud': -33.833,
        'longitud': -64.833,
        'profundidad': 30,
        'magnitud': 6.0,
        'descripcion': 'Terremoto de Sampacho'
    },
    {
        'fecha': '16/01/1947',
        'hora': '02:37:00',
        'latitud': -31.1,
        'longitud': -64.5,
        'profundidad': 50,
        'magnitud': 5.5,
        'descripcion': 'Sismo moderado con daños significativos'
    },
    {
        'fecha': '28/05/1955',
        'hora': '06:20:00',
        'latitud': -31.05,
        'longitud': -64.497,
        'profundidad': 25,
        'magnitud': 7.3,
        'descripcion': 'Terremoto de Villa Giardino - El más potente registrado'
    }
]

# Crear DataFrame
sismos_historicos_df = pd.DataFrame(DATOS_HISTORICOS)

# Procesar fechas y calcular energía
sismos_historicos_df['fecha_dt'] = pd.to_datetime(sismos_historicos_df['fecha'], format='%d/%m/%Y', errors='coerce')
sismos_historicos_df['energia_joules'] = sismos_historicos_df['magnitud'].apply(energia_liberada)

# Sidebar con información general
st.sidebar.header("Información Histórica")
st.sidebar.write(f"Total de sismos históricos: {len(sismos_historicos_df)}")

# Verificar que tenemos fechas válidas antes de calcular el rango
fechas_validas = sismos_historicos_df['fecha_dt'].notna()
if fechas_validas.any():
    min_year = sismos_historicos_df.loc[fechas_validas, 'fecha_dt'].min().year
    max_year = sismos_historicos_df.loc[fechas_validas, 'fecha_dt'].max().year
    st.sidebar.write(f"Rango de años: {min_year} - {max_year}")
else:
    st.sidebar.write("Rango de años: No disponible")

st.sidebar.write(f"Magnitud máxima: {sismos_historicos_df['magnitud'].max():.1f}")
st.sidebar.write(f"Magnitud mínima: {sismos_historicos_df['magnitud'].min():.1f}")

# Filtro por magnitud mínima
magnitud_minima = st.sidebar.slider(
    "Filtrar por magnitud mínima:",
    min_value=float(sismos_historicos_df['magnitud'].min()),
    max_value=float(sismos_historicos_df['magnitud'].max()),
    value=4.0,
    step=0.1
)

# Aplicar filtro
sismos_filtrados = sismos_historicos_df[sismos_historicos_df['magnitud'] >= magnitud_minima].copy()

# Resetear índice para evitar filas vacías
sismos_filtrados.reset_index(drop=True, inplace=True)

# Crear mapa
st.header("Mapa de Sismos Históricos")

if not sismos_filtrados.empty:
    # Crear mapa centrado en Córdoba
    m = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
    
    # Añadir marcadores para cada sismo histórico
    for _, sismo in sismos_filtrados.iterrows():
        # Color basado en la magnitud (misma escala que app.py)
        if sismo['magnitud'] < 2.5:
            color = 'green'
        elif sismo['magnitud'] < 3.5:
            color = 'orange'
        elif sismo['magnitud'] < 5.0:
            color = 'red'
        else:
            color = 'red'  # Color especial para sismos muy fuertes
            
        # Tamaño basado en la magnitud (fórmula consistente)
        size = 5 + (sismo['magnitud'])  # Más grandes para mejor visibilidad histórica
        
        # Formatear energía en notación científica legible
        energia_formateada = f"{sismo['energia_joules']:.2e}"
        
        # Crear popup con información detallada
        popup_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 300px;">
            <h4 style="color: {color}; margin-bottom: 10px;">Sismo Histórico</h4>
            <p style="margin: 5px 0;"><b>Fecha:</b> {sismo['fecha']}</p>
            <p style="margin: 5px 0;"><b>Hora:</b> {sismo['hora']}</p>
            <p style="margin: 5px 0;"><b>Magnitud:</b> {sismo['magnitud']:.1f}</p>
            <p style="margin: 5px 0;"><b>Profundidad:</b> {sismo['profundidad']} km</p>
            <p style="margin: 5px 0;"><b>Latitud:</b> {sismo['latitud']:.3f}°</p>
            <p style="margin: 5px 0;"><b>Longitud:</b> {sismo['longitud']:.3f}°</p>
            <p style="margin: 5px 0;"><b>Energía liberada:</b> {energia_formateada} J</p>
            <hr style="margin: 10px 0;">
            <p style="margin: 5px 0; font-style: italic;">{sismo['descripcion']}</p>
        </div>
        """
        
        folium.CircleMarker(
            location=[sismo['latitud'], sismo['longitud']],
            radius=size,
            popup=folium.Popup(popup_content, max_width=350),
            tooltip=f"Sismo M{sismo['magnitud']:.1f} - {sismo['fecha']}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            opacity=0.8,
            weight=2
        ).add_to(m)
    
    # Mostrar el mapa
    folium_static(m, width=1000, height=600)
    
    # Mostrar tabla de datos
    st.subheader("Datos de Sismos Históricos")
    
    # Preparar datos para la tabla - SOLO LAS COLUMNAS NECESARIAS
    columnas_mostrar = ['fecha', 'hora', 'latitud', 'longitud', 'profundidad', 'magnitud', 'descripcion']
    tabla_datos = sismos_filtrados[columnas_mostrar].copy()
    
    # Agregar energía formateada
    tabla_datos['energia_joules'] = sismos_filtrados['energia_joules'].apply(lambda x: f"{x:.2e}")
    
    # Renombrar columnas para mejor visualización
    tabla_datos = tabla_datos.rename(columns={
        'fecha': 'Fecha',
        'hora': 'Hora',
        'latitud': 'Latitud',
        'longitud': 'Longitud',
        'profundidad': 'Profundidad (km)',
        'magnitud': 'Magnitud',
        'descripcion': 'Descripción',
        'energia_joules': 'Energía (Joules)'
    })
    
    # Calcular altura dinámica basada en el número de filas
    num_filas = len(tabla_datos)
    altura_tabla = min(400, max(200, (num_filas + 1) * 35))  # Mínimo 200px, máximo 400px
    
    st.dataframe(
        tabla_datos.sort_values('Magnitud', ascending=False),
        use_container_width=True,
        height=altura_tabla
    )
    
    # Mostrar contador de registros
    st.caption(f"Mostrando {num_filas} sismo(s) histórico(s)")
    
    # GRÁFICO DE COMPARACIÓN DE ENERGÍA LIBERADA
    st.subheader("🔬 Comparación de Energía Liberada")
    
    # Crear diccionario de comparación que incluya eventos de referencia y sismos históricos
    eventos_comp = eventos_comparacion.copy()
    
    # Agregar cada sismo histórico al diccionario de comparación
    for _, sismo in sismos_filtrados.iterrows():
        nombre_sismo = f"Sismo {sismo['fecha'][-4:]} M{sismo['magnitud']:.1f}"
        eventos_comp[nombre_sismo] = sismo['energia_joules']
    
    # Ordenar por energía
    eventos_comp = dict(sorted(eventos_comp.items(), key=lambda item: item[1]))
    
    # Crear gráfico comparativo
    fig = go.Figure()
    
    # Agregar barras al gráfico
    fig.add_trace(go.Bar(
        x=list(eventos_comp.keys()),
        y=list(eventos_comp.values()),
        marker_color=["#ff7f0e" if "Sismo" in k else "#1f77b4" for k in eventos_comp.keys()],
        text=[f"{v:.1e} J" for v in eventos_comp.values()],
        textposition='auto',
        hovertemplate="<b>%{x}</b><br>Energía: %{y:.2e} J<extra></extra>"
    ))
    
    # Configurar layout del gráfico
    fig.update_layout(
        yaxis_type="log",
        yaxis_title="Energía (Joules) - Escala Logarítmica",
        xaxis_title="Evento",
        title="Comparación de Energía: Sismos Históricos vs Eventos de Referencia",
        height=500,
        template="plotly_white",
        showlegend=False
    )
    
    # Rotar etiquetas del eje X para mejor legibilidad
    fig.update_xaxes(tickangle=45)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Explicación científica
    st.markdown("""
    ## 📚 Explicación Científica
    
    **Relación Magnitud-Energía:**
    \[ E = 10^{(1.5 \times M + 4.8)} \]
    
    Donde:
    - \( E \) = Energía en Joules
    - \( M \) = Magnitud del sismo
    
    **Interpretación:**
    - Cada aumento de 1 unidad en magnitud = 31.6 veces más energía
    - Un sismo de magnitud 6.0 libera aproximadamente 1000 veces más energía que uno de 4.0
    - La energía liberada por el terremoto de Villa Giardino (M7.3) es comparable a múltiples bombas atómicas
    
    **Notación de Energía:**
    - **B**: Billones (10⁹ Joules)
    - **T**: Trillones (10¹² Joules)
    """)
    
else:
    st.warning("No hay sismos históricos que cumplan con el filtro de magnitud aplicado.")

# Información adicional
st.markdown("---")
st.subheader("Contexto Histórico")
st.markdown("""
**Significado de estos eventos:**

- **1908 - Terremoto de Cruz del Eje**: Uno de los sismos más destructivos en la historia de Córdoba
- **1934 - Terremoto de Sampacho**: Importante sismo en la región sur de la provincia
- **1955 - Terremoto de Villa Giardino**: El sismo de mayor magnitud registrado en la provincia (7.3)

**Eventos de Comparación:**
- **Rayo**: Descarga eléctrica atmosférica típica
- **1 tonelada de TNT**: Explosivo convencional estándar
- **Bomba de Hiroshima**: Aproximadamente 15 kilotones de TNT
- **Erupción volcánica**: Evento eruptivo moderado
- **Sismo M7**: Terremoto significativo a nivel global
- **Sismo M8.5**: Megaterremoto devastador

Estos sismos históricos representan hitos importantes en la sismología de Córdoba y ayudan a entender
los patrones de actividad sísmica en la región a lo largo del tiempo.

**Nota:** La energía liberada se calcula usando la fórmula de Gutenberg-Richter:  
`log₁₀(E) = 1.5·M + 4.8` donde E es la energía en Joules y M es la magnitud del sismo.
""")
