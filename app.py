import streamlit as st
import folium
import streamlit.components.v1 as components
import rasterio
import numpy as np
import pandas as pd
import plotly.express as px
from matplotlib.colors import to_rgba
import json

from folium.plugins import Fullscreen
from branca.element import Element

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="LCZ Bangalore Dashboard", layout="wide")

# ==========================================
# 2. DADOS E VARIÁVEIS GERAIS
# ==========================================
geojson_path = "Bengalore_Boundaries.geojson"
tif_path = "lcz_clipped_mask.tif"

lcz_legend = {
    "1: Compact highrise": "#910613", "2: Compact midrise": "#D9081C", "3: Compact lowrise": "#FF0A22",
    "4: Open highrise": "#C54F1E", "5: Open midrise": "#FF6628", "6: Open lowrise": "#FF985E",
    "7: Lightweight low-rise": "#FDED3F", "8: Large lowrise": "#BBBBBB", "9: Sparsely built": "#FFCBAB",
    "10: Heavy Industry": "#565656", "11: Dense trees": "#006A18", "12: Scattered trees": "#00A926",
    "13: Bush, scrub": "#628432", "14: Low plants": "#B5DA7F", "15: Bare rock or paved": "#000000",
    "16: Bare soil or sand": "#FCF7B1", "17: Water": "#656BFA"
}

lcz_lookup = {
    int(key.split(":")[0]): {"name": key, "color": color}
    for key, color in lcz_legend.items()
}

# ==========================================
# 3. PROCESSAMENTO DE DADOS (CACHED)
# ==========================================
@st.cache_data
def process_spatial_data(_tif_path: str):
    with rasterio.open(_tif_path) as src:
        img_array = src.read(1)
        bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]

    unique, counts = np.unique(img_array, return_counts=True)
    df_stats = pd.DataFrame({"Class_ID": unique, "Pixels": counts})
    df_stats = df_stats[df_stats["Class_ID"] > 0]
    return img_array, bounds, df_stats

@st.cache_data
def build_colored_rgba(_img_array: np.ndarray, _lcz_lookup: dict):
    colored = np.zeros((_img_array.shape[0], _img_array.shape[1], 4), dtype=np.float32)
    for class_id, info in _lcz_lookup.items():
        r, g, b, _ = to_rgba(info["color"])
        colored[_img_array == class_id] = [r, g, b, 1.0]
    return colored

img_array, bounds, df_stats = process_spatial_data(tif_path)
colored_img = build_colored_rgba(img_array, lcz_lookup)

# ==========================================
# 4. LAYOUT PRINCIPAL
# ==========================================
st.title("Local Climate Zones Dashboard - Bangalore")
st.markdown("Overview of the urban climate distribution. Use the top-right menu on the map to toggle layers.")

# mais espaço para o mapa + alinhamento melhor
col_map, col_chart = st.columns([3.3, 1])

with col_map:
    # Inicia o Mapa Base
    m = folium.Map(location=[12.9716, 77.5946], zoom_start=10, tiles=None)

    # Ajusta automaticamente o enquadramento ao raster
    try:
        m.fit_bounds(bounds)
    except Exception:
        pass

    # Botão de tela cheia
    Fullscreen(
        position="topleft",
        title="Expand map",
        title_cancel="Exit fullscreen",
        force_separate_button=True
    ).add_to(m)

    # 1) Base Satellite (mantém como fundo fixo)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Base Satellite",
        control=False
    ).add_to(m)

    # 2) Camada LCZ (opacidade padrão; slider será injetado no LayerControl)
    lcz_opacity_default = 0.80
    lcz_overlay = folium.raster_layers.ImageOverlay(
        image=colored_img,
        bounds=bounds,
        opacity=lcz_opacity_default,
        name="Local Climate Zones",
        show=True
    ).add_to(m)

    # 3) Limites do município (sem pontos)
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            geo_data = json.load(f)

        if "features" in geo_data:
            geo_data["features"] = [
                feat for feat in geo_data["features"]
                if feat.get("geometry", {}).get("type") not in ["Point", "MultiPoint"]
            ]

        folium.GeoJson(
            geo_data,
            name="Bangalore Boundaries",
            style_function=lambda feature: {
                "fillColor": "transparent",
                "color": "white",
                "weight": 2
            }
        ).add_to(m)
    except Exception as e:
        st.warning(f"Could not load boundaries: {e}")

    # 4) Layer control (aberto por padrão)
    lc = folium.LayerControl(position="topright", collapsed=False)
    lc.add_to(m)

    # ==========================================
    # 5) INJETAR SLIDER DE OPACIDADE "DENTRO" DO LayerControl
    #    - tecnicamente adiciona HTML no container do LayerControl (Leaflet)
    # ==========================================
    lcz_var = lcz_overlay.get_name()  # nome da variável JS do overlay

    inject_opacity_slider = f"""
    <script>
    (function() {{
      function addOpacitySlider() {{
        // Container do LayerControl
        var lc = document.querySelector('.leaflet-control-layers');
        if (!lc) return;

        // Evita duplicar
        if (lc.querySelector('#lcz-opacity-wrap')) return;

        // Cria bloco
        var wrap = document.createElement('div');
        wrap.id = 'lcz-opacity-wrap';
        wrap.style.padding = '8px 10px';
        wrap.style.borderTop = '1px solid rgba(255,255,255,0.15)';
        wrap.style.marginTop = '6px';

        var label = document.createElement('div');
        label.textContent = 'LCZ opacity';
        label.style.fontSize = '12px';
        label.style.fontWeight = 'bold';
        label.style.marginBottom = '6px';
        label.style.color = '#eaeaea';

        var row = document.createElement('div');
        row.style.display = 'flex';
        row.style.alignItems = 'center';
        row.style.gap = '8px';

        var input = document.createElement('input');
        input.type = 'range';
        input.min = 0;
        input.max = 1;
        input.step = 0.05;
        input.value = {lcz_opacity_default};
        input.style.width = '140px';

        var val = document.createElement('span');
        val.textContent = input.value;
        val.style.fontSize = '12px';
        val.style.minWidth = '32px';
        val.style.color = '#eaeaea';

        input.addEventListener('input', function(e) {{
          var v = parseFloat(e.target.value);
          val.textContent = v.toFixed(2);

          // Aplica opacidade no overlay LCZ
          try {{
            if (window.{lcz_var} && window.{lcz_var}.setOpacity) {{
              window.{lcz_var}.setOpacity(v);
            }}
          }} catch (err) {{}}
        }});

        row.appendChild(input);
        row.appendChild(val);
        wrap.appendChild(label);
        wrap.appendChild(row);

        // Insere no fim do LayerControl
        lc.appendChild(wrap);
      }}

      // Tenta algumas vezes porque o Leaflet monta DOM depois
      var tries = 0;
      var timer = setInterval(function() {{
        tries++;
        addOpacitySlider();
        if (document.querySelector('.leaflet-control-layers #lcz-opacity-wrap') || tries > 20) {{
          clearInterval(timer);
        }}
      }}, 250);
    }})();
    </script>
    """
    m.get_root().html.add_child(Element(inject_opacity_slider))

    # Renderiza o mapa
    components.html(m.get_root().render(), height=720)

with col_chart:
    st.subheader("Distribution & Legend")

    # Gráfico
    df_stats["Name"] = df_stats["Class_ID"].map(lambda x: lcz_lookup.get(x, {}).get("name", "Other"))
    df_stats["Color"] = df_stats["Class_ID"].map(lambda x: lcz_lookup.get(x, {}).get("color", "#000000"))

    df_plot = df_stats.sort_values(by="Pixels", ascending=False).head(8)
    color_map = {row["Name"]: row["Color"] for _, row in df_plot.iterrows()}

    fig = px.bar(
        df_plot,
        x="Pixels",
        y="Name",
        orientation="h",
        color="Name",
        color_discrete_map=color_map
    )
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=320)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Legenda completa
    st.markdown("Complete Classes Legend:")
    for name, color in lcz_legend.items():
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; margin-bottom:4px;">
              <div style="width:16px; height:16px; background-color:{color};
                          margin-right:12px; border:1px solid #ccc; border-radius:2px;"></div>
              <span style="font-size:0.85rem; color:#eee;">{name}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
