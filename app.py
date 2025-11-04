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

# =========================
# 🏙️ arrondissement depuis le code postal (technique)
# =========================
df["arrondissement"] = (
    df["code_postal"]
    .astype(str)
    .str.zfill(5)
    .str[-2:]
)

st.title("🌿 Espaces verts à Paris")

# =========================
# 🔽 FILTRES
# =========================
st.subheader("Filtres")

cats = sorted(df["categorie"].dropna().unique())
arrs = sorted(df["arrondissement"].dropna().unique())

col1, col2, col3, col4 = st.columns(4)

with col1:
    categories_sel = st.multiselect(
        "Catégories",
        options=cats,
        default=[],
        placeholder="Choisir une ou plusieurs catégories",
    )

with col2:
    arrondissements_sel = st.multiselect(
        "Arrondissement",
        options=arrs,
        default=[],
        placeholder="Ex: 01, 08, 20…",
    )

with col3:
    h24_sel = st.selectbox(
        "Ouverture 24/24",
        options=["Tous", "Oui", "Non"],
        index=0,
    )

with col4:
    cloture_sel = st.selectbox(
        "Clôturé",
        options=["Tous", "Oui", "Non"],
        index=0,
    )

# ======================
# Application des filtres
# ======================
filtered_df = df.copy()

if categories_sel:
    filtered_df = filtered_df[filtered_df["categorie"].isin(categories_sel)]

if arrondissements_sel:
    filtered_df = filtered_df[filtered_df["arrondissement"].isin(arrondissements_sel)]

if h24_sel != "Tous" and "ouverture_24h" in filtered_df.columns:
    want_open = (h24_sel == "Oui")
    filtered_df = filtered_df[filtered_df["ouverture_24h"] == want_open]

if cloture_sel != "Tous" and "presence_cloture" in filtered_df.columns:
    want_cloture = (cloture_sel == "Oui")
    filtered_df = filtered_df[filtered_df["presence_cloture"] == want_cloture]

st.caption(f"{len(filtered_df)} ligne(s) après filtrage.")

# =========================
# 📊 KPI
# =========================
k1, k2, k3 = st.columns(3)
k1.metric("Espaces affichés", len(filtered_df))
k2.metric("Catégories sélectionnées", len(categories_sel))
if "surface_totale_reelle_m2" in filtered_df.columns:
    total_surface = int(filtered_df["surface_totale_reelle_m2"].sum())
    total_surface_fmt = f"{total_surface:,}".replace(",", " ")
    k3.metric("Surface totale (m²)", total_surface_fmt)
else:
    k3.metric("Surface totale (m²)", "—")

# =========================
# 🗂️ ONGlets
# =========================
tab_map, tab_data, tab_charts = st.tabs(["🗺️ Carte", "📋 Données", "📈 Graphiques"])

# --- CARTE ---
with tab_map:
    st.subheader("🗺️ Carte des espaces verts (polygones)")

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
        color_map = {
            "Bois": [0, 100, 0, 120],
            "Parc": [46, 204, 113, 120],
            "Square": [52, 152, 219, 120],
            "Jardin": [241, 196, 15, 120],
            "Jardin partage": [230, 126, 34, 120],
            "Pelouse": [39, 174, 96, 120],
            "Mail": [142, 68, 173, 120],
            "Promenade": [26, 188, 156, 120],
            "Terrain de boules": [192, 57, 43, 120],
            "Forêt urbaine": [0, 128, 0, 120],
            "Ile": [52, 73, 94, 120],
            "Cimetière": [149, 165, 166, 120],
        }

        features = []
        for _, row in geo_df.iterrows():
            fill = color_map.get(row["categorie"], [127, 140, 141, 120])
            features.append({
                "type": "Feature",
                "properties": {
                    "nom": row["nom"],
                    "categorie": row["categorie"],
                    "fill_color": fill,
                },
                "geometry": row["geometry"],
            })

        geojson_obj = {"type": "FeatureCollection", "features": features}

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

    view_df = filtered_df.copy()

    # ----- colonne surface -----
    surface = None
    if "surface_totale_reelle_m2" in view_df.columns:
        surface = view_df["surface_totale_reelle_m2"]
        if "surface_calculee_m2" in view_df.columns:
            surface = surface.fillna(view_df["surface_calculee_m2"])
        elif "surface_calculee" in view_df.columns:
            surface = surface.fillna(view_df["surface_calculee"])
    else:
        if "surface_calculee_m2" in view_df.columns:
            surface = view_df["surface_calculee_m2"]
        elif "surface_calculee" in view_df.columns:
            surface = view_df["surface_calculee"]

    view_df["surface"] = surface if surface is not None else None

    # ----- colonne surface affichée (espaces entre milliers) -----
    def format_surface(x):
        if pd.isna(x):
            return ""
        try:
            x = int(float(x))
            return f"{x:,}".replace(",", " ")
        except Exception:
            return str(x)

    view_df["surface_affichee"] = view_df["surface"].apply(format_surface)

    # ----- colonne adresse -----
    addr_cols = [c for c in view_df.columns if "adresse" in c.lower()]
    if addr_cols:
        addr_df = view_df[addr_cols]

        def join_addr(row):
            parts = []
            for v in row.tolist():
                if pd.isna(v):
                    continue
                s = str(v).strip()
                if s == "" or s.lower() == "nan":
                    continue
                parts.append(s)
            joined = " ".join(parts)
            return " ".join(joined.split())

        view_df["adresse"] = addr_df.apply(join_addr, axis=1)
    else:
        view_df["adresse"] = view_df.get("code_postal", "").astype(str)

    # ----- arrondissement affiché -----
    CP_OUTSIDE = {
        "92220": "Bagneux (92)",
        "93210": "Saint-Denis (93)",
        "93400": "Saint-Ouen (93)",
        "93500": "Pantin (93)",
        "94200": "Ivry-sur-Seine (94)",
        "94300": "Vincennes (94)",
        "94320": "Thiais (94)",
    }

    def format_arrondissement(row):
        cp = str(row.get("code_postal", "")).strip()
        arr = str(row.get("arrondissement", "")).strip()

        # si c'est un des cas hors Paris identifiés
        if cp in CP_OUTSIDE:
            return CP_OUTSIDE[cp]

        # si c'est Paris
        if cp.startswith("75") and len(arr) == 2 and arr.isdigit():
            n = int(arr)
            if n == 1:
                return "1er"
            else:
                return f"{n}e"

        # fallback: commune si dispo
        if "commune" in row and str(row["commune"]).strip().lower() not in ["", "nan", "none"]:
            return str(row["commune"]).strip()

        # dernier fallback: code postal complet
        return cp

    view_df["arrondissement_affiche"] = view_df.apply(format_arrondissement, axis=1)

    # ----- colonnes à afficher (ordre demandé) -----
    cols_to_show = [
        "nom",                     # Lieu
        "categorie",               # Catégorie
        "adresse",                 # Adresse
        "arrondissement_affiche",  # Arrondissement (ou ville)
        "surface_affichee",        # Surface (m²)
    ]

    if "annee_ouverture" in view_df.columns:
        cols_to_show.append("annee_ouverture")
    if "presence_cloture" in view_df.columns:
        cols_to_show.append("presence_cloture")
    if "ouverture_24h" in view_df.columns:
        cols_to_show.append("ouverture_24h")

    # on vire les colonnes d'identifiant de l'affichage
    id_cols = [c for c in view_df.columns if c.lower() in ["id", "identifiant", "index"]]
    cols_to_show = [c for c in cols_to_show if c not in id_cols]

    # ---- alias d'affichage ----
    rename_display = {
        "nom": "Lieu",
        "categorie": "Catégorie",
        "adresse": "Adresse",
        "arrondissement_affiche": "Arrondissement",
        "surface_affichee": "Surface (m²)",
        "annee_ouverture": "Année d'ouverture",
        "presence_cloture": "Clôturé",
        "ouverture_24h": "Ouvert 24h/24",
    }

    df_display = (
        view_df[cols_to_show]
        .rename(columns=rename_display)
        .reset_index(drop=True)
    )

    st.dataframe(df_display, width="stretch", hide_index=True)

    # export CSV (surface numérique + arrondissement technique)
    export_cols = [
        "nom",
        "categorie",
        "adresse",
        "arrondissement",        # info brute
        "code_postal",           # utile pour retrouver la ville
        "surface",
    ]
    if "annee_ouverture" in view_df.columns:
        export_cols.append("annee_ouverture")
    if "presence_cloture" in view_df.columns:
        export_cols.append("presence_cloture")
    if "ouverture_24h" in view_df.columns:
        export_cols.append("ouverture_24h")

    st.download_button(
        "⬇️ Télécharger les données filtrées (CSV)",
        data=view_df[export_cols].to_csv(index=False, sep=";"),
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