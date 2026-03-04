import streamlit as st
import folium
from folium.plugins import SideBySideLayers
from streamlit_folium import st_folium
import rasterio
import numpy as np
import pandas as pd
import plotly.express as px
from matplotlib.colors import to_rgba
import json
from folium import Element

# 1. Configuração da Página
st.set_page_config(page_title="LCZ Bangalore Dashboard", layout="wide")

# --- CATEGORIAS LCZ & CORES ---
lcz_legend = {
    "1: Compact highrise": "#910613", "2: Compact midrise": "#D9081C", "3: Compact lowrise": "#FF0A22",
    "4: Open highrise": "#C54F1E", "5: Open midrise": "#FF6628", "6: Open lowrise": "#FF985E",
    "7: Lightweight low-rise": "#FDED3F", "8: Large lowrise": "#BBBBBB", "9: Sparsely built": "#FFCBAB",
    "10: Heavy Industry": "#565656", "11: Dense trees": "#006A18", "12: Scattered trees": "#00A926",
    "13: Bush, scrub": "#628432", "14: Low plants": "#B5DA7F", "15: Bare rock or paved": "#000000",
    "16: Bare soil or sand": "#FCF7B1", "17: Water": "#656BFA"
}

geojson_path = 'Bengalore_Boundaries.geojson'
tif_path = 'lcz_clipped_mask.tif'

# --- PROCESSAMENTO DOS DADOS ---
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

# --- LAYOUT PRINCIPAL ---
st.title("🗺️ Local Climate Zones Dashboard - Bangalore")
st.markdown("Overview of the urban climate distribution. Swipe to compare LCZ (Left) with Satellite imagery (Right).")

col_map, col_chart = st.columns([2.5, 1])

with col_map:
    # 1. Prepara a imagem LCZ colorida
    colored_img = np.zeros((img_array.shape[0], img_array.shape[1], 4))
    for idx, (name, hex_color) in enumerate(lcz_legend.items()):
        class_number = idx + 1 
        r, g, b, _ = to_rgba(hex_color)
        colored_img[img_array == class_number] = [r, g, b, 1.0]

    # 2. Inicia o mapa (Sem parâmetros que causem tela preta)
    m = folium.Map(location=[12.9716, 77.5946], zoom_start=11)

    # ==============================================================
    # 3. A MÁGICA: Injeção de JS para evitar o crash da tela preta!
    # Isso ensina a ferramenta de Swipe a entender e cortar imagens.
    # ==============================================================
    js_fix = """
    if (typeof L !== 'undefined' && L.ImageOverlay) {
        L.ImageOverlay.prototype.getContainer = function() {
            return this.getElement();
        };
    }
    """
    m.get_root().script.add_child(Element(js_fix))

    # 4. LADO DIREITO: Imagem de Satélite
    right_sat = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite View (Right)',
        overlay=True,
        control=True
    ).add_to(m)

    # 5. LADO ESQUERDO: Zonas Climáticas Locais (Nossa Imagem)
    lcz_layer = folium.raster_layers.ImageOverlay(
        image=colored_img,
        bounds=bounds,
        name='Local Climate Zones (Left)',
        overlay=True,
        control=True
    ).add_to(m)

    # 6. Aplica o SWIPE (Que agora vai funcionar perfeitamente)
    SideBySideLayers(layer_left=lcz_layer, layer_right=right_sat).add_to(m)

    # 7. Fronteiras de Bangalore
    try:
        with open(geojson_path, 'r') as f:
            geo_data = json.load(f)
        folium.GeoJson(
            geo_data,
            name="Bangalore Boundaries",
            style_function=lambda x: {'fillOpacity': 0, 'color': 'white', 'weight': 3},
            control=True
        ).add_to(m)
    except Exception as e:
        st.error("Erro ao carregar os limites. Verifique o arquivo GeoJSON.")

    # 8. Habilita o menu de Ligar/Desligar Camadas no canto
    folium.LayerControl(position='topright').add_to(m)

    # 9. Renderiza
    st_folium(m, width="100%", height=650, returned_objects=[])

# --- GRÁFICO E LEGENDA ---
with col_chart:
    st.subheader("Distribution & Legend")
    
    class_names = list(lcz_legend.keys())
    hex_colors = list(lcz_legend.values())
    df_stats['Name'] = df_stats['Class_ID'].apply(lambda x: class_names[x-1] if x <= len(class_names) else "Other")
    df_stats['Color'] = df_stats['Class_ID'].apply(lambda x: hex_colors[x-1] if x <= len(hex_colors) else "#000000")
    df_plot = df_stats.sort_values(by='Pixels', ascending=False).head(8)
    
    fig = px.bar(df_plot, x='Pixels', y='Name', orientation='h', color='Name',
                 color_discrete_sequence=df_plot['Color'].tolist())
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("**Complete Classes Legend:**")
    for name, color in lcz_legend.items():
        st.markdown(
            f'<div style="display: flex; align-items: center; margin-bottom: 4px;">'
            f'<div style="width: 16px; height: 16px; background-color: {color}; margin-right: 12px; border: 1px solid #ccc; border-radius: 2px;"></div>'
            f'<span style="font-size: 0.85rem; color: #eee;">{name}</span></div>', 
            unsafe_allow_html=True
        )
