import streamlit as st
import folium
import streamlit.components.v1 as components
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
        bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]
    
    unique, counts = np.unique(img_array, return_counts=True)
    df_stats = pd.DataFrame({'Class_ID': unique, 'Pixels': counts})
    df_stats = df_stats[df_stats['Class_ID'] > 0] 
    
    return img_array, bounds, df_stats

img_array, bounds, df_stats = process_spatial_data(tif_path)

# ==========================================
# 4. LAYOUT PRINCIPAL
# ==========================================
st.title("🗺️ Local Climate Zones Dashboard - Bangalore")
st.markdown("Overview of the urban climate distribution. Use the top-right menu on the map to toggle layers.")

col_map, col_chart = st.columns([2.5, 1])

with col_map:
    # Prepara a imagem LCZ colorida
    colored_img = np.zeros((img_array.shape[0], img_array.shape[1], 4))
    for class_id, info in lcz_lookup.items():
        r, g, b, _ = to_rgba(info["color"])
        colored_img[img_array == class_id] = [r, g, b, 0.8] # Fixei a opacidade em 0.8 para ver um pouco o fundo

    # Inicia o Mapa Base
    m = folium.Map(location=[12.9716, 77.5946], zoom_start=10, tiles=None)

    # 1. Adiciona o Mapa de Satélite
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Base Satellite',
        control=False
    ).add_to(m)

    # 2. Adiciona a Camada LCZ (Imagem)
    folium.raster_layers.ImageOverlay(
        image=colored_img,
        bounds=bounds,
        name='Local Climate Zones',
        show=True
    ).add_to(m)

    # 3. Adiciona os Limites (Boundaries)
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
        pass

    # 4. Adiciona o controle de camadas
    folium.LayerControl(position='topright').add_to(m)

    # Renderiza de forma estática (SEM O PONTO AZUL)
    components.html(m.get_root().render(), height=650)

with col_chart:
    st.subheader("Distribution & Legend")
    
    # Gráfico
    df_stats['Name'] = df_stats['Class_ID'].map(lambda x: lcz_lookup.get(x, {}).get("name", "Other"))
    df_stats['Color'] = df_stats['Class_ID'].map(lambda x: lcz_lookup.get(x, {}).get("color", "#000000"))
    df_plot = df_stats.sort_values(by='Pixels', ascending=False).head(8)
    
    color_map = {row['Name']: row['Color'] for _, row in df_plot.iterrows()}
    
    fig = px.bar(
        df_plot, x='Pixels', y='Name', orientation='h', color='Name', color_discrete_map=color_map
    )
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    # Legenda restaurada para o seu formato original que funciona bem no Streamlit
    st.markdown("**Complete Classes Legend:**")
    for name, color in lcz_legend.items():
        st.markdown(
            f'<div style="display: flex; align-items: center; margin-bottom: 4px;">'
            f'<div style="width: 16px; height: 16px; background-color: {color}; margin-right: 12px; border: 1px solid #ccc; border-radius: 2px;"></div>'
            f'<span style="font-size: 0.85rem; color: #eee;">{name}</span></div>', 
            unsafe_allow_html=True
        )
