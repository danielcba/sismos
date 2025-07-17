import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium, folium_static
import plotly.express as px
import plotly.graph_objs as go
import numpy as np
import math
import re


# --- Parámetros científicos y eventos de comparación ---
eventos = {
    "Rayo": 1e9,
    "1 tonelada de TNT": 4.2e9,
    "Bomba de Hiroshima": 6.3e13,
    "Erupción volcánica": 1e15,
    "Sismo M7": 2e15,
    "Sismo M8.5": 1e18
}

def energia_liberada(magnitud):
    """
    Calcula la energía liberada por un sismo en Joules usando la fórmula de Gutenberg-Richter:
    log10(E) = 1.5*M + 4.8
    donde E es la energía en Joules y M es la magnitud del sismo.
    
    Referencia: Kanamori, H. (1977). The energy release in great earthquakes. 
    Journal of Geophysical Research, 82(20), 2981-2987.
    """
    return 10 ** (1.5 * magnitud + 4.8)

# --- Cargar datos de sismos ---
from app import fetch_sismos_data

# Inicializar el estado de la sesión
if 'sismo_seleccionado' not in st.session_state:
    st.session_state.sismo_seleccionado = None
if 'last_processed_popup' not in st.session_state:
    st.session_state.last_processed_popup = None

sismos_df = fetch_sismos_data()

# Agregar ID único a cada sismo
sismos_df['id'] = sismos_df.index.astype(str)

st.title("🌋 Energía Liberada por Sismos")

st.markdown("""
Esta herramienta permite comparar la energía liberada por un sismo con eventos naturales y artificiales conocidos.
Selecciona un sismo en el mapa de la izquierda para ver su representación y comparación energética.

**Nota:** Cada aumento de 1 unidad en magnitud representa una liberación de energía 32 veces mayor.
""")

col1, col2 = st.columns(2)

# --- Mapa de la izquierda: todos los sismos ---
with col1:
    st.subheader("Mapa de Sismos Registrados")
    m1 = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
    
    # Añadir todos los sismos con IDs únicos
    for idx, sismo in sismos_df.iterrows():
        # Color basado en la magnitud
        if sismo['magnitud'] < 2.5:
            color = 'green'
        elif sismo['magnitud'] < 3.5:
            color = 'orange'
        else:
            color = 'red'
            
        # Tamaño basado en la magnitud
        size = 2 + sismo['magnitud']
        
        folium.CircleMarker(
            location=[sismo['latitud'], sismo['longitud']],
            name=str(sismo['id']),  # Clave para la selección directa
            radius=size,
            color=color,         # Color del borde basado en magnitud
            fill=True,           # Rellenar el círculo
            fill_color=color,    # Color de relleno basado en magnitud
            fill_opacity=0.4,    # Transparencia del relleno
            opacity=0.7,         # Opacidad del borde
            weight=1,            # Grosor del borde
            popup=f"""                
                <div style='font-size:11px;'>
                    <b>ID:</b> {sismo['id']}<br>
                    <b>Fecha:</b> {sismo['fecha'].strftime('%Y-%m-%d')}<br>
                    <b>Hora:</b> {sismo['hora']}<br>
                    <b>Magnitud:</b> {sismo['magnitud']:.1f}<br>
                    <b>Profundidad:</b> {sismo['profundidad']} km<br>
                    <b>Latitud:</b> {sismo['latitud']:.4f}<br>
                    <b>Longitud:</b> {sismo['longitud']:.4f}
                </div>
            """,
            tooltip=folium.Tooltip(
                f"<div style='font-size:11px;'>Sismo M{sismo['magnitud']:.1f} - Click para seleccionar</div>",
                sticky=False,
                parse_html=True
            )
        ).add_to(m1)
    
    # Usamos st_folium para obtener el clic en el popup de un objeto
    folium_data = st_folium(
        m1,
        width=500,
        height=610,
        key="mapa_izq",
        returned_objects=["last_object_clicked_popup"]
    )

    # --- Lógica de Selección con Depuración ---
    clicked_popup_html = folium_data.get("last_object_clicked_popup")

    if clicked_popup_html and clicked_popup_html != st.session_state.last_processed_popup:
        st.session_state.last_processed_popup = clicked_popup_html

        st.markdown("--- DEBUG INFO ---")
        st.write("**1. Popup HTML recibido:**")
        st.code(clicked_popup_html, language='html')

        # Regex más robusta para extraer el ID (soporta HTML o texto plano)
        match = re.search(r"ID[:\s]*([0-9A-Za-z_.-]+)", clicked_popup_html)
        
        if match:
            clicked_sismo_id = match.group(1)
            st.write(f"**2. ID extraído:** `{clicked_sismo_id}`")
            
            sismo_sel_series = sismos_df[sismos_df['id'] == clicked_sismo_id]

            if not sismo_sel_series.empty:
                sismo_sel = sismo_sel_series.iloc[0].to_dict()
                st.session_state.sismo_seleccionado = sismo_sel
                st.success("**3. Resultado:** ¡Sismo encontrado y seleccionado!")
            else:
                st.session_state.sismo_seleccionado = None
                st.error(f"**3. Resultado:** Error, el sismo con ID `{clicked_sismo_id}` no se encontró en los datos.")
        else:
            st.session_state.sismo_seleccionado = None
            st.error("**2. Resultado:** No se pudo extraer el ID del popup.")
        
        st.rerun()

    # Botón para limpiar selección
    if st.session_state.sismo_seleccionado:
        if st.button("Limpiar selección", key="btn_limpiar_seleccion"):
            st.session_state.sismo_seleccionado = None
            st.rerun()

# --- Mapa de la derecha: sismo seleccionado ---
with col2:
    st.subheader("Visualización de Energía Liberada")
    m2 = folium.Map(location=[-32.2935, -63.7111], zoom_start=7)
    
    # Siempre mostrar algo en el mapa derecho
    if st.session_state.sismo_seleccionado:
        sismo_sel = st.session_state.sismo_seleccionado
        n_circulos = int(math.floor(sismo_sel['magnitud']))
        
        # Dibujar círculos concéntricos
        for i in range(1, n_circulos + 1):
            folium.Circle(
                location=[sismo_sel['latitud'], sismo_sel['longitud']],
                radius=i * 20000,  # Radio en metros (20 km por círculo)
                color='orange',
                fill=False,
                weight=2,
                opacity=0.7,
                popup=f"Anillo de energía {i} - Radio: {i*20} km"
            ).add_to(m2)
        
        # Marcador central
        folium.CircleMarker(
            location=[sismo_sel['latitud'], sismo_sel['longitud']],
            radius=8 + sismo_sel['magnitud'],
            color='red',
            fill=True,
            fill_opacity=0.7,
            weight=0.5,
            popup=f"""
                <div style='font-size:11px;'>
                    <b>Sismo M{sismo_sel['magnitud']:.1f}</b><br>
                    <b>Energía:</b>{energia_liberada(sismo_sel['magnitud']):.2e}J<br>
                    <b>Círculos:</b>{n_circulos} (1 por unidad de magnitud)
                </div>
            """
        ).add_to(m2)
        
        # Leyenda científica
        folium.Marker(
            [sismo_sel['latitud'] - 1.0, sismo_sel['longitud']],
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    background: white;
                    width: 180px;
                    padding: 8px;
                    border-radius: 5px;
                    box-shadow: 0 0 5px rgba(0,0,0,0.2);
                    font-family: Arial, sans-serif;
                ">
                    <div style="
                        color: #d62728;
                        font-weight: bold;
                        font-size: 13px;
                        margin-bottom: 4px;
                    ">
                        Sismo M{sismo_sel['magnitud']:.1f}
                    </div>
                    <div style="
                        font-size: 11px;
                        color: #333;
                        line-height: 1.3;
                    ">
                        Energía: {energia_liberada(sismo_sel['magnitud']):.2e} J
                    </div>
                </div>
                """
            )
        ).add_to(m2)
    else:
        # Vista por defecto cuando no hay selección
        folium.Marker(
            [-32.2935, -63.7111],
            popup="Selecciona un sismo en el mapa izquierdo",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m2)
        folium.Circle(
            location=[-32.2935, -63.7111],
            radius=50000,
            color='blue',
            fill=False,
            weight=0.5
        ).add_to(m2)
        # st.info("Selecciona un sismo en el mapa izquierdo para visualizar la energía liberada")
    
    st_folium(m2, width=500, height=610, key="mapa_der")

# --- Gráfico de comparación energética ---
if st.session_state.sismo_seleccionado:
    sismo_sel = st.session_state.sismo_seleccionado
    magnitud = sismo_sel['magnitud']
    energia_sismo = energia_liberada(magnitud)
    
    # Crear diccionario de comparación
    eventos_comp = eventos.copy()
    eventos_comp[f"Sismo M{magnitud:.1f}"] = energia_sismo
    
    # Ordenar por energía
    eventos_comp = dict(sorted(eventos_comp.items(), key=lambda item: item[1]))
    
    # Crear gráfico comparativo
    st.markdown(f"""
    ### 🔬 Comparación de Energía Liberada
    **Sismo seleccionado:** Magnitud {magnitud:.1f}  
    **Energía calculada:** {energia_sismo:.2e} Joules  
    """)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(eventos_comp.keys()),
        y=list(eventos_comp.values()),
        marker_color=["#ff7f0e" if f"Sismo M{magnitud:.1f}" in k else "#1f77b4" for k in eventos_comp.keys()],
        text=[f"{v:.1e} J" for v in eventos_comp.values()],
        textposition='auto',
        hovertemplate="<b>%{x}</b><br>Energía: %{y:.2e} J<extra></extra>"
    ))
    
    fig.update_layout(
        yaxis_type="log",
        yaxis_title="Energía (Joules) - Escala Logarítmica",
        xaxis_title="Evento",
        title=f"Comparación de Energía: Sismo M{magnitud:.1f} vs Eventos de Referencia",
        height=500,
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Explicación científica
    st.markdown("""
    ## 📚 Explicación
    
    **Relación Magnitud-Energía:**
    \[ E = 10^{(1.5 \t* M + 4.8)} \]
    
    Donde:
    - \( E \) = Energía en Joules
    - \( M \) = Magnitud del sismo
    
    **Interpretación:**
    - Cada aumento de 1 unidad en magnitud = 31.6 veces más energía
    - Un sismo de magnitud 6.0 libera 1000 veces más energía que uno de 4.0
    - Los círculos concéntricos representan la disipación de energía desde el epicentro
    """)
else:
    st.info("ℹ️ Selecciona un sismo en el mapa izquierdo para ver la comparación energética")

# --- Nota final ---
st.markdown("---")
st.caption("""
**Nota Técnica:** Los cálculos de energía son aproximaciones basadas en modelos sismológicos. 
La energía real puede variar según las características específicas de cada sismo.
""")

# Añadir después de la comparación energética
st.subheader("Acumulación Histórica de Energía")

if not sismos_df.empty:
    # Calcular energía acumulada
    sismos_df = sismos_df.sort_values('fecha_hora')
    sismos_df['energia_joules'] = 10**(1.5 * sismos_df['magnitud'] + 4.8)
    sismos_df['energia_acumulada'] = sismos_df['energia_joules'].cumsum()
    
    # Gráfico
    fig = px.line(
        sismos_df, 
        x='fecha_hora', 
        y='energia_acumulada',
        log_y=True,
        labels={'fecha_hora': 'Fecha', 'energia_acumulada': 'Energía Acumulada (Joules)'}
    )
    fig.update_layout(
        title='Energía Sísmica Acumulada (Escala Logarítmica)',
        yaxis_type="log"
    )
    st.plotly_chart(fig)
    
    # Anotar eventos importantes
    eventos_importantes = sismos_df.nlargest(5, 'magnitud')
    for i, row in eventos_importantes.iterrows():
        st.markdown(f"**M{row['magnitud']:.1f}** ({row['fecha'].strftime('%Y-%m-%d')}): "
                    f"{row['energia_joules']:.2e} Joules")
