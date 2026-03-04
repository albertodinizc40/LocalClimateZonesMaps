import streamlit as st
import leafmap.foliumap as leafmap
import folium
from folium.plugins import SideBySideLayers
import rasterio
import numpy as np
import pandas as pd
import plotly.express as px
from matplotlib.colors import to_rgba

# 1. Page Configuration (No more sidebar expanded by default)
st.set_page_config(page_title="LCZ Bangalore Dashboard", layout="wide")

# --- LCZ CATEGORIES & COLORS ---
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

# --- DATA PROCESSING ---
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


# --- MAIN LAYOUT (Full Width, No Sidebar) ---
st.title("🗺️ Local Climate Zones Dashboard - Bangalore")
st.markdown("Overview of the urban climate distribution. Interact with the map and the charts below.")

col_map, col_chart = st.columns([2.5, 1]) # O mapa fica um pouco mais largo agora

with col_map:
    # Prepare LCZ image
    colored_img = np.zeros((img_array.shape[0], img_array.shape[1], 4))
    for idx, (name, hex_color) in enumerate(lcz_legend.items()):
        class_number = idx + 1 
        r, g, b, _ = to_rgba(hex_color)
        colored_img[img_array == class_number] = [r, g, b, 1.0]

    # Initialize map
    m = leafmap.Map(center=[12.9716, 77.5946], zoom=10, draw_control=False)

    # RIGHT LAYER: Satellite imagery
    sat_layer = folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri Satellite',
        name='Satellite View',
        control=True
    ).add_to(m)

    # LEFT LAYER: Local Climate Zones
    lcz_layer = folium.raster_layers.ImageOverlay(
        image=colored_img,
        bounds=bounds,
        name='Local Climate Zones',
        control=True
    ).add_to(m)
    
    # Apply Swipe Plugin (Side by Side)
    SideBySideLayers(layer_left=lcz_layer, layer_right=sat_layer).add_to(m)

    # Boundaries
    m.add_geojson(geojson_path, layer_name="City Boundaries", fill_colors=['transparent'], weight=2, color="white")
    
    # FORÇA O MENU DE CAMADAS A APARECER
    folium.LayerControl(position="topright").add_to(m)

    m.to_streamlit(height=650)


with col_chart:
    st.subheader("Distribution & Legend")
    
    # 1. Plotly Chart
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
    
    # 2. Fixed Legend (Cleaned up)
    st.markdown("**Complete Classes Legend:**")
    
    # Usando HTML leve para gerar a legenda compacta e elegante embaixo do gráfico
    for name, color in lcz_legend.items():
        st.markdown(
            f'<div style="display: flex; align-items: center; margin-bottom: 4px;">'
            f'<div style="width: 16px; height: 16px; background-color: {color}; margin-right: 12px; border: 1px solid #ccc; border-radius: 2px;"></div>'
            f'<span style="font-size: 0.85rem; color: #eee;">{name}</span></div>', 
            unsafe_allow_html=True
        )
