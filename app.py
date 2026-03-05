import streamlit as st
import folium
from streamlit_folium import st_folium
import rasterio
import numpy as np
import pandas as pd
import plotly.express as px
from matplotlib.colors import to_rgba

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="LCZ Bangalore Dashboard", layout="wide")

# ==========================================
# 2. DADOS E VARIÁVEIS GERAIS
# ==========================================
geojson_path = 'Bengalore_Boundaries.geojson'
tif_path = 'lcz_clipped_mask.tif'

lcz_legend = {
    "1: Compact highrise": "#910613", "2: Compact midrise": "#D9081C", "3: Compact lowrise": "#FF0A22",
    "4: Open highrise": "#C54F1E", "5: Open midrise": "#FF6628", "6: Open lowrise": "#FF985E",
    "7: Lightweight low-rise": "#FDED3F", "8: Large lowrise": "#BBBBBB", "9: Sparsely built": "#FFCBAB",
    "10: Heavy Industry": "#565656", "11: Dense trees": "#006A18", "12: Scattered trees": "#00A926",
    "13: Bush, scrub": "#628432", "14: Low plants": "#B5DA7F", "15: Bare rock or paved": "#000000",
    "16: Bare soil or sand": "#FCF7B1", "17: Water": "#656BFA"
}

# Criar um dicionário de busca rápida para facilitar o cruzamento de dados depois
lcz_lookup = {
    int(key.split(':')[0]): {"name": key, "color": color} 
    for key, color in lcz_legend.items()
}

# ==========================================
# 3. PROCESSAMENTO DE DADOS (CACHED)
# ==========================================
@st.cache_data
def process_spatial_data(tif_path):
    with rasterio.open(tif_path) as src:
        img_array = src.read(1)
        # Formato de bounds exigido pelo Folium: [[lat_min, lon_min], [lat_max, lon_max]]
        bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]
    
    unique, counts = np.unique(img_array, return_counts=True)
    df_stats = pd.DataFrame({'Class_ID': unique, 'Pixels': counts})
    df_stats = df_stats[df_stats['Class_ID'] > 0] 
    
    return img_array, bounds, df_stats

# Carrega os dados
img_array, bounds, df_stats = process_spatial_data(tif_path)

# ==========================================
# 4. LAYOUT PRINCIPAL
# ==========================================
st.title("🗺️ Local Climate Zones Dashboard - Bangalore")
st.markdown("Overview of the urban climate distribution. Use the slider to adjust transparency and the top-right menu to toggle layers.")

col_map, col_chart = st.columns([2.5, 1])

# --- COLUNA ESQUERDA: MAPA ---
with col_map:
    # Controle de Opacidade no topo do mapa
    layer_opacity = st.slider("Ajustar Transparência da Camada LCZ", min_value=0.0, max_value=1.0, value=0.75, step=0.05)

    # Prepara a imagem LCZ colorida
    colored_img = np.zeros((img_array.shape[0], img_array.shape[1], 4))
    for class_id, info in lcz_lookup.items():
        r, g, b, _ = to_rgba(info["color"])
        colored_img[img_array == class_id] = [r, g, b, 1.0] # Mantém alpha=1.0 aqui, a opacidade geral é controlada no Folium

    # Inicia o Mapa Base
    m = folium.Map(location=[12.9716, 77.5946], zoom_start=10, tiles=None)

    # 1. Adiciona o Mapa de Satélite
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Base Satellite',
        control=False
    ).add_to(m)

    # 2. Adiciona a Camada LCZ (Imagem) com controle de opacidade e nome para o menu
    folium.raster_layers.ImageOverlay(
        image=colored_img,
        bounds=bounds,
        opacity=layer_opacity,
        name='Local Climate Zones',
        show=True
    ).add_to(m)

    # 3. Adiciona os Limites (Boundaries)
    # Usando folium.GeoJson puro, que é mais estável
    try:
        folium.GeoJson(
            geojson_path,
            name="Bangalore Boundaries",
            style_function=lambda feature: {
                'fillColor': 'transparent',
                'color': 'white',
                'weight': 2
            }
        ).add_to(m)
    except Exception as e:
        st.warning(f"Não foi possível carregar as bordas: {e}")

    # 4. Adiciona o controle de camadas (Permite ligar/desligar a LCZ e o Boundary)
    folium.LayerControl(position='topright').add_to(m)

    # Renderiza o mapa usando st_folium
    # returned_objects=[] evita lentidão ao mover o mapa
    st_folium(m, use_container_width=True, height=600, returned_objects=[])

# --- COLUNA DIREITA: GRÁFICOS E LEGENDA ---
with col_chart:
    st.subheader("Distribution & Legend")
    
    # Prepara o DataFrame para o Gráfico usando o lookup seguro
    df_stats['Name'] = df_stats['Class_ID'].map(lambda x: lcz_lookup.get(x, {}).get("name", "Other"))
    df_stats['Color'] = df_stats['Class_ID'].map(lambda x: lcz_lookup.get(x, {}).get("color", "#000000"))
    df_plot = df_stats.sort_values(by='Pixels', ascending=False).head(8)
    
    # Gráfico Plotly
    # color_discrete_map garante que o Plotly use a cor exata correspondente ao nome, evitando dessincronização
    color_map = {row['Name']: row['Color'] for _, row in df_plot.iterrows()}
    
    fig = px.bar(
        df_plot, 
        x='Pixels', 
        y='Name', 
        orientation='h', 
        color='Name',
        color_discrete_map=color_map
    )
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    # Legenda Fixa e Alinhada
    st.markdown("**Complete Classes Legend:**")
    
    # Monta a legenda em HTML garantindo espaçamento e alinhamento consistentes
    legend_html = '<div style="display: flex; flex-direction: column; gap: 6px;">'
    for name, color in lcz_legend.items():
        legend_html += f"""
            <div style="display: flex; align-items: center;">
                <div style="width: 16px; height: 16px; background-color: {color}; margin-right: 12px; border: 1px solid #ccc; border-radius: 2px; flex-shrink: 0;"></div>
                <span style="font-size: 0.85rem; color: #eee; line-height: 1;">{name}</span>
            </div>
        """
    legend_html += '</div>'
    
    st.markdown(legend_html, unsafe_allow_html=True)
