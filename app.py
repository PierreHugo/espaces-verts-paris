import pandas as pd
import streamlit as st

# -----------------------
# CONFIG APP
# -----------------------
st.set_page_config(
    page_title="Espaces verts à Paris",
    page_icon="🌿",
    layout="wide"
)

@st.cache_data
def load_data():
    df = pd.read_csv("src/espaces_verts_normalized.csv", sep=";")
    return df

df = load_data()

st.title("🌿 Espaces verts à Paris")
st.markdown("Petit tableau de bord interactif basé sur le dataset nettoyé.")

# -----------------------
# SIDEBAR
# -----------------------
st.sidebar.header("Filtres")

# filtre catégorie
categories = sorted(df["categorie"].dropna().unique())
selected_categories = st.sidebar.multiselect(
    "Catégories à afficher",
    options=categories,
    default=categories  # tout coché par défaut
)

# filtre surface minimale (optionnel)
surface_min = st.sidebar.number_input(
    "Surface minimale (m²) – basé sur surface_totale_reelle_m2",
    min_value=0,
    value=0,
    step=50
)

# appliquer filtres
filtered_df = df[df["categorie"].isin(selected_categories)].copy()

if "surface_totale_reelle_m2" in filtered_df.columns:
    filtered_df = filtered_df[
        (filtered_df["surface_totale_reelle_m2"].isna()) |
        (filtered_df["surface_totale_reelle_m2"] >= surface_min)
    ]

# -----------------------
# KPIs
# -----------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Nombre d'espaces", len(filtered_df))
with col2:
    st.metric("Catégories sélectionnées", len(selected_categories))
with col3:
    # surface totale affichée
    if "surface_totale_reelle_m2" in filtered_df.columns:
        total_surface = filtered_df["surface_totale_reelle_m2"].sum()
        st.metric("Surface totale (m²)", f"{int(total_surface):,}".replace(",", " "))
    else:
        st.metric("Surface totale (m²)", "—")

# -----------------------
# CARTE
# -----------------------
st.subheader("🗺️ Carte des espaces verts")
if {"latitude", "longitude"}.issubset(filtered_df.columns):
    st.map(
        filtered_df,
        latitude="latitude",
        longitude="longitude",
        size=50
    )
else:
    st.info("Pas de coordonnées disponibles pour la carte.")

# -----------------------
# TABLEAU
# -----------------------
st.subheader("📋 Données")
st.dataframe(
    filtered_df[
        [
            "nom",
            "categorie",
            "typologie",
            "surface_totale_reelle_m2",
            "latitude",
            "longitude"
        ]
    ].sort_values(by="categorie"),
    use_container_width=True,
)