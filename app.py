import streamlit as st
import leafmap.foliumap as leafmap
import folium
import rasterio
import numpy as np
import pandas as pd
import plotly.express as px
from matplotlib.colors import to_rgba

# 1. Page Configuration (Must be the first command)
st.set_page_config(page_title="LCZ Bangalore Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- DICTIONARY & COLORS ---
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

# --- DATA PROCESSING (Cached for performance) ---
@st.cache_data
def process_spatial_data(tif_path):
    with rasterio.open(tif_path) as src:
        img_array = src.read(1)
        bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]
    
    # Count pixels for the chart (ignoring 0 which is transparent/background)
    unique, counts = np.unique(img_array, return_counts=True)
    df_stats = pd.DataFrame({'Class_ID': unique, 'Pixels': counts})
    df_stats = df_stats[df_stats['Class_ID'] > 0] 
    
    return img_array, bounds, df_stats

img_array, bounds, df_stats = process_spatial_data(tif_path)


# --- SIDEBAR MENU ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1865/1865313.png", width=50)
    st.title("Map Controls")
    st.markdown("Use the slider below to compare the Local Climate Zones with the real satellite imagery.")
    
    # Opacity Slider
    opacity = st.slider("LCZ Layer Opacity", min_value=0.0, max_value=1.0, value=0.75, step=0.05)
    
    st.markdown("---")
    st.markdown("**About the Project:**\nLocal Climate Zones (LCZ) analysis for urban planning and environmental monitoring.")


# --- MAIN LAYOUT (DASHBOARD) ---
st.title("🗺️ Local Climate Zones Dashboard - Bangalore")
st.markdown("Overview of the urban climate distribution. Interact with the map and the charts below.")

# Create two columns: Map (larger) and Chart (smaller)
col_map, col_chart = st.columns([2, 1])

with col_map:
    st.subheader("Interactive Map")
    
    # Create colored image using the sidebar opacity value
    colored_img = np.zeros((img_array.shape[0], img_array.shape[1], 4))
    for idx, (name, hex_color) in enumerate(lcz_legend.items()):
        class_number = idx + 1 
        r, g, b, _ = to_rgba(hex_color)
        colored_img[img_array == class_number] = [r, g, b, opacity] 

    # Build Map
    m = leafmap.Map(center=[12.9716, 77.5946], zoom=10)
    m.add_basemap("SATELLITE")
    
    folium.raster_layers.ImageOverlay(
        image=colored_img,
        bounds=bounds,
        name='LCZ Bangalore',
    ).add_to(m)

    m.add_geojson(geojson_path, layer_name="Bangalore Boundaries", fill_colors=['transparent'], weight=3, color="white")
    m.add_legend(title="Local Climate Zones", legend_dict=lcz_legend)
    
    # Render map
    m.to_streamlit(height=550)

with col_chart:
    st.subheader("Zone Distribution")
    
    # Prepare data for the chart
    class_names = list(lcz_legend.keys())
    hex_colors = list(lcz_legend.values())
    
    # Map IDs to proper Names and Colors in the DataFrame
    df_stats['Name'] = df_stats['Class_ID'].apply(lambda x: class_names[x-1] if x <= len(class_names) else "Other")
    df_stats['Color'] = df_stats['Class_ID'].apply(lambda x: hex_colors[x-1] if x <= len(hex_colors) else "#000000")
    
    # Sort and pick top 8 to keep the chart clean
    df_stats = df_stats.sort_values(by='Pixels', ascending=False).head(8)
    
    # Create modern bar chart with Plotly
    fig = px.bar(
        df_stats, 
        x='Pixels', 
        y='Name', 
        orientation='h',
        color='Name',
        color_discrete_sequence=df_stats['Color'].tolist(),
        title="Top 8 Predominant Classes"
    )
    
    # Clean up layout
    fig.update_layout(
        showlegend=False, 
        margin=dict(l=0, r=0, t=30, b=0), 
        yaxis={'categoryorder':'total ascending'}
    )
    
    # Render chart
    st.plotly_chart(fig, use_container_width=True)
