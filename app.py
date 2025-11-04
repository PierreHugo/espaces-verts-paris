import streamlit as st
import pandas as pd
import json
import pydeck as pdk

st.set_page_config(
    page_title="Espaces verts à Paris",
    page_icon="🌿",
    layout="wide",
)

@st.cache_data
def load_data():
    return pd.read_csv("src/espaces_verts_normalized.csv", sep=";")

df = load_data()

st.title("🌿 Espaces verts à Paris")

# =========================
# 🔽 FILTRES (une seule fois)
# =========================
st.subheader("Filtres")

cols = st.columns(3)

with cols[0]:
    categories = sorted(df["categorie"].dropna().unique())
    selected_categories = st.multiselect(
        "Catégories",
        options=categories,
        default=categories,
    )

with cols[1]:
    surface_min = st.number_input(
        "Surface minimale (m²)",
        min_value=0,
        value=0,
        step=50,
    )

with cols[2]:
    only_geo = st.checkbox("Seulement avec coordonnées", value=True)

# appliquer les filtres une fois
filtered_df = df[df["categorie"].isin(selected_categories)].copy()

if "surface_totale_reelle_m2" in filtered_df.columns:
    filtered_df = filtered_df[
        (filtered_df["surface_totale_reelle_m2"].isna())
        | (filtered_df["surface_totale_reelle_m2"] >= surface_min)
    ]

if only_geo and {"latitude", "longitude"}.issubset(filtered_df.columns):
    filtered_df = filtered_df[
        filtered_df["latitude"].notna() & filtered_df["longitude"].notna()
    ]

st.caption(f"{len(filtered_df)} ligne(s) après filtrage.")

# =========================
# 📊 KPI
# =========================
k1, k2, k3 = st.columns(3)
k1.metric("Espaces affichés", len(filtered_df))
k2.metric("Catégories sélectionnées", len(selected_categories))
if "surface_totale_reelle_m2" in filtered_df.columns:
    k3.metric(
        "Surface totale (m²)",
        f"{int(filtered_df['surface_totale_reelle_m2'].sum()):,}".replace(",", " "),
    )
else:
    k3.metric("Surface totale (m²)", "—")

# =========================
# 🗂️ ONGlets
# =========================
tab_map, tab_data, tab_charts = st.tabs(["🗺️ Carte", "📋 Données", "📈 Graphiques"])

# --- CARTE ---
with tab_map:
    st.subheader("🗺️ Carte des espaces verts (polygones)")

    # on garde seulement les lignes qui ont un geo_shape non vide
    geo_df = filtered_df[filtered_df["geo_shape"].notna()].copy()

    def parse_geojson(x):
        try:
            return json.loads(x)
        except Exception:
            return None

    geo_df["geometry"] = geo_df["geo_shape"].apply(parse_geojson)
    geo_df = geo_df[geo_df["geometry"].notna()]

    if geo_df.empty:
        st.warning("Aucune géométrie exploitable dans les données filtrées.")
    else:
        
        # palette simple
        color_map = {
            "Bois": [0, 100, 0, 120],             # vert foncé
            "Parc": [46, 204, 113, 120],          # vert clair
            "Square": [52, 152, 219, 120],        # bleu doux
            "Jardin": [241, 196, 15, 120],        # jaune doré
            "Jardin partage": [230, 126, 34, 120],# orange
            "Pelouse": [39, 174, 96, 120],        # vert moyen
            "Mail": [142, 68, 173, 120],          # violet
            "Promenade": [26, 188, 156, 120],     # turquoise
            "Terrain de boules": [192, 57, 43, 120], # rouge terre battue
            "Forêt urbaine": [0, 128, 0, 120],    # vert forêt
            "Ile": [52, 73, 94, 120],             # gris bleuté
            "Cimetière": [149, 165, 166, 120],    # gris clair
        }

        # construire une liste de features GeoJSON
        features = []
        for _, row in geo_df.iterrows():
            fill = color_map.get(row["categorie"], [127, 140, 141, 120])  # couleur par défaut
            features.append({
                "type": "Feature",
                "properties": {
                    "nom": row["nom"],
                    "categorie": row["categorie"],
                    "fill_color": fill,
                },
                "geometry": row["geometry"],
            })

        geojson_obj = {
            "type": "FeatureCollection",
            "features": features,
        }


        geojson_layer = pdk.Layer(
            "GeoJsonLayer",
            data=geojson_obj,
            get_fill_color="properties.fill_color",
            get_line_color=[0, 0, 0],
            line_width_min_pixels=1,
            pickable=True,
        )

        view_state = pdk.ViewState(
            latitude=48.8566,
            longitude=2.3522,
            zoom=11,
            pitch=0,
        )

        r = pdk.Deck(
            layers=[geojson_layer],
            initial_view_state=view_state,
            tooltip={"text": "{nom}\n{categorie}"},
        )

        st.pydeck_chart(r)

# --- DONNÉES ---
with tab_data:
    st.subheader("📋 Données")
    st.dataframe(
        filtered_df[
            [
                "nom",
                "categorie",
                "typologie",
                "surface_totale_reelle_m2",
                "latitude",
                "longitude",
            ]
        ].sort_values("categorie"),
        width="stretch",
    )
    st.download_button(
        "⬇️ Télécharger les données filtrées (CSV)",
        data=filtered_df.to_csv(index=False, sep=";"),
        file_name="espaces_verts_filtres.csv",
        mime="text/csv",
    )

# --- GRAPHIQUES ---
with tab_charts:
    st.subheader("📈 Répartition par catégorie")
    counts = (
        filtered_df["categorie"]
        .value_counts()
        .rename_axis("categorie")
        .reset_index(name="nb")
    )
    st.bar_chart(counts, x="categorie", y="nb")
    st.caption("On pourra remplacer ce chart par Altair pour un rendu plus clean.")
