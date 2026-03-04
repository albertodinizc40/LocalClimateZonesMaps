import streamlit as st
import leafmap.foliumap as leafmap
import folium
import rasterio
import numpy as np
from matplotlib.colors import to_rgba

# 1. Configuração da página
st.set_page_config(page_title="LCZ Bangalore", layout="wide")
st.title("🗺️ Local Climate Zones - Bangalore")
st.markdown("Testing a panel to analyze local climate zones")

geojson_path = 'Bengalore_Boundaries.geojson'
tif_path = 'lcz_clipped_mask.tif'

# 2. Legenda e Cores oficiais
lcz_legend = {
    "1: Compact highrise": "#910613", "2: Compact midrise": "#D9081C", "3: Compact lowrise": "#FF0A22",
    "4: Open highrise": "#C54F1E", "5: Open midrise": "#FF6628", "6: Open lowrise": "#FF985E",
    "7: Lightweight low-rise": "#FDED3F", "8: Large lowrise": "#BBBBBB", "9: Sparsely built": "#FFCBAB",
    "10: Heavy Industry": "#565656", "11: Dense trees": "#006A18", "12: Scattered trees": "#00A926",
    "13: Bush, scrub": "#628432", "14: Low plants": "#B5DA7F", "15: Bare rock or paved": "#000000",
    "16: Bare soil or sand": "#FCF7B1", "17: Water": "#656BFA"
}

# 3. Criação do mapa base
m = leafmap.Map(center=[12.9716, 77.5946], zoom=10)
m.add_basemap("SATELLITE")

# ==========================================
# O TRUQUE PARA A NUVEM: Imagem em Memória
# ==========================================
# Lemos os pixels do mapa direto do arquivo
with rasterio.open(tif_path) as src:
    img_array = src.read(1)
    # Pegamos as coordenadas reais do mundo para esticar a imagem no lugar certo
    bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]

# Criamos uma "tela em branco" invisível (com canal Alpha)
colored_img = np.zeros((img_array.shape[0], img_array.shape[1], 4))

# Pintamos pixel por pixel com a cor correta do LCZ
for idx, (name, hex_color) in enumerate(lcz_legend.items()):
    class_number = idx + 1 
    r, g, b, _ = to_rgba(hex_color)
    # Onde o pixel pertencer a essa classe, pintamos com 75% de opacidade
    colored_img[img_array == class_number] = [r, g, b, 0.75]

# Colamos a imagem pronta como uma camada sobre o mapa do Google
folium.raster_layers.ImageOverlay(
    image=colored_img,
    bounds=bounds,
    name='LCZ Bangalore',
).add_to(m)
# ==========================================

# Adiciona o limite da cidade e a legenda da mesma forma que antes
m.add_geojson(geojson_path, layer_name="Limites Bangalore", fill_colors=['transparent'], weight=3, color="white")
m.add_legend(title="Local Climate Zones", legend_dict=lcz_legend)

# Renderiza na tela
m.to_streamlit(height=600)
