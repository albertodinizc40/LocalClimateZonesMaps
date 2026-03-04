import streamlit as st
import leafmap.foliumap as leafmap

# 1. Configuração da página do site
st.set_page_config(page_title="LCZ Bangalore", layout="wide")
st.title("🗺️ Zonas Climáticas Locais (LCZ) - Bangalore")
st.markdown("Mapa interativo exibindo as classificações climáticas urbanas sobrepostas à imagem de satélite.")

# 2. Caminhos dos arquivos
# ATENÇÃO: Os nomes aqui precisam ser EXATAMENTE iguais aos dos arquivos que você subiu no GitHub!
geojson_path = 'Bengalore_Boundaries.geojson'
tif_path = 'lcz_clipped_mask.tif'

# 3. Legenda e Cores oficiais (Baseado no readme.txt)
lcz_legend = {
    "1: Compact highrise": "#910613",
    "2: Compact midrise": "#D9081C",
    "3: Compact lowrise": "#FF0A22",
    "4: Open highrise": "#C54F1E",
    "5: Open midrise": "#FF6628",
    "6: Open lowrise": "#FF985E",
    "7: Lightweight low-rise": "#FDED3F",
    "8: Large lowrise": "#BBBBBB",
    "9: Sparsely built": "#FFCBAB",
    "10: Heavy Industry": "#565656",
    "11: Dense trees": "#006A18",
    "12: Scattered trees": "#00A926",
    "13: Bush, scrub": "#628432",
    "14: Low plants": "#B5DA7F",
    "15: Bare rock or paved": "#000000",
    "16: Bare soil or sand": "#FCF7B1",
    "17: Water": "#656BFA"
}
lcz_colors = list(lcz_legend.values())

# 4. Criação do mapa
# center=[latitude, longitude] aproxima a câmera de Bangalore logo ao abrir o site
m = leafmap.Map(center=[12.9716,
