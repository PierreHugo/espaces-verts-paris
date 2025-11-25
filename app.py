import streamlit as st
import pandas as pd
import json
import pydeck as pdk
import base64

def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

st.set_page_config(
    page_title="Espaces verts à Paris",
    page_icon="🌿",
    layout="wide",
)

@st.cache_data
def load_data():
    # CSV déjà nettoyé (9999 -> NaN)
    return pd.read_csv("src/espaces_verts_normalized.csv", sep=";")

df = load_data()

# =========================
# 🏙️ arrondissement depuis le code postal
# =========================
df["arrondissement"] = (
    df["code_postal"]
    .astype(str)
    .str.zfill(5)
    .str[-2:]
)

CP_OUTSIDE = {
    "92220": "Bagneux (92)",
    "93210": "Saint-Denis (93)",
    "93400": "Saint-Ouen (93)",
    "93500": "Pantin (93)",
    "94200": "Ivry-sur-Seine (94)",
    "94300": "Vincennes (94)",
    "94320": "Thiais (94)",
}

def format_arrondissement_row(row):
    cp = str(row.get("code_postal", "")).strip()
    arr = str(row.get("arrondissement", "")).strip()

    if cp in CP_OUTSIDE:
        return CP_OUTSIDE[cp]

    if cp.startswith("75") and len(arr) == 2 and arr.isdigit():
        n = int(arr)
        return "1er" if n == 1 else f"{n}e"

    # fallback commune
    if "commune" in row and str(row["commune"]).strip().lower() not in ["", "nan", "none"]:
        return str(row["commune"]).strip()

    return cp

df["arrondissement_affiche"] = df.apply(format_arrondissement_row, axis=1)

st.title("🌿 Espaces verts à Paris")

# =========================
# ONGlets principaux
# =========================
tab_carte_typo, tab_carte_hist, tab_data, tab_stats = st.tabs(
    ["🧭 Carte typologique", "📜 Carte historique", "📋 Données", "📈 Statistiques"]
)

# ---------------------------------------------------------------------
# 1. CARTE TYPOLOGIQUE (avec filtres + KPI)
# ---------------------------------------------------------------------
with tab_carte_typo:
    st.subheader("🧭 Carte typologique")

    # ===== FILTRES =====
    st.markdown("### Filtres")

    cats = sorted(df["categorie"].dropna().unique())
   
    # 1. on récupère tous les arrondissements affichés uniques
    arr_unique = df[["arrondissement_affiche", "code_postal"]].drop_duplicates()

    # 2. on sépare Paris (75xxx) du reste
    paris = arr_unique[arr_unique["code_postal"].astype(str).str.startswith("75")]
    hors_paris = arr_unique[~arr_unique["code_postal"].astype(str).str.startswith("75")]

    # 3. ordre pour Paris : 1er, 2e, 3e, ..., 20e
    paris_order = []
    for i in range(1, 21):
        if i == 1:
            paris_order.append("1er")
        else:
            paris_order.append(f"{i}e")

    # on garde seulement ceux qui existent vraiment dans le df
    paris_sorted = [a for a in paris_order if a in set(paris["arrondissement_affiche"])]

    # 4. pour le hors Paris : on trie par code postal (donc 92..., puis 93..., puis 94...)
    hors_paris_sorted = (
        hors_paris.sort_values("code_postal")["arrondissement_affiche"].tolist()
    )

    # 5. on concatène
    arrs = paris_sorted + hors_paris_sorted


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
            placeholder="1er, 2e, ...",
        )

    with col3:
        h24_sel = st.selectbox(
            "Ouverture 24h/24",
            options=["Tous", "Oui", "Non"],
            index=0,
        )

    with col4:
        cloture_sel = st.selectbox(
            "Clôturé",
            options=["Tous", "Oui", "Non"],
            index=0,
        )

    # ===== Application des filtres =====
    filtered_df = df.copy()

    if categories_sel:
        filtered_df = filtered_df[filtered_df["categorie"].isin(categories_sel)]
    # si aucune catégorie sélectionnée → on garde tout
    else:
        filtered_df = filtered_df.copy()


    if arrondissements_sel:
        filtered_df = filtered_df[filtered_df["arrondissement_affiche"].isin(arrondissements_sel)]

    if h24_sel != "Tous" and "ouverture_24h" in filtered_df.columns:
        want_open = (h24_sel == "Oui")
        filtered_df = filtered_df[filtered_df["ouverture_24h"] == want_open]

    if cloture_sel != "Tous" and "presence_cloture" in filtered_df.columns:
        want_cloture = (cloture_sel == "Oui")
        filtered_df = filtered_df[filtered_df["presence_cloture"] == want_cloture]

    # ===== KPI =====
    k1, k2, k3 = st.columns(3)
    k1.metric("Espaces affichés", len(filtered_df))
    k2.metric("Catégories sélectionnées", len(categories_sel) if categories_sel else len(cats))

    if "surface_totale_reelle_m2" in filtered_df.columns:
        total_surface = filtered_df["surface_totale_reelle_m2"].sum(min_count=1)
        # s'il y a encore des NaN -> ignore
        if pd.isna(total_surface):
            total_surface_fmt = "—"
        else:
            total_surface = int(total_surface)
            total_surface_fmt = f"{total_surface:,}".replace(",", " ")
        k3.metric("Surface totale (m²)", total_surface_fmt)
    else:
        k3.metric("Surface totale (m²)", "—")

    # ===== Carte typologique =====
    geo_df = filtered_df[filtered_df["geo_shape"].notna()].copy()

    def parse_geojson(x):
        try:
            return json.loads(x)
        except Exception:
            return None

    geo_df["geometry"] = geo_df["geo_shape"].apply(parse_geojson)
    geo_df = geo_df[geo_df["geometry"].notna()]

    if geo_df.empty:
        st.warning("Aucun espace vert ne correspond à vos critères de recherches.")
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
                    "ouverture_24h": "Oui" if row.get("ouverture_24h") else "Non",
                    "presence_cloture": "Oui" if row.get("presence_cloture") else "Non",
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
            tooltip={
                "text": "{nom}\n{categorie}\nOuvert 24h/24 : {ouverture_24h}\nClôturé : {presence_cloture}"
            }
        )

        st.pydeck_chart(r)

# ---------------------------------------------------------------------
# 2. CARTE HISTORIQUE
# ---------------------------------------------------------------------

with tab_carte_hist:
    st.subheader("📜 Carte historique")

    if "annee_ouverture" not in df.columns:
        st.warning("Pas de colonne 'annee_ouverture' dans les données.")
    else:
        years_series = pd.to_numeric(df["annee_ouverture"], errors="coerce").dropna()
        if years_series.empty:
            st.warning("Aucune année d'ouverture renseignée.")
        else:
            min_year = int(years_series.min())
            max_year = int(years_series.max())

            st.markdown("""
                <style>
                /* Centrage + largeur contrôlée */
                div[data-baseweb="slider"] {
                    width: 90% !important;
                    margin: 0 auto;
                }

                /* Barre de fond (inactive) */
                .stSlider [role="presentation"] > div:first-child {
                    height: 0.4rem !important;
                    background-color: rgba(255, 255, 255, 0.15);
                }

                /* Barre active (valeur sélectionnée) */
                .stSlider [role="presentation"] > div:nth-child(2) {
                    height: 0.4rem !important;
                    background-color: #2ecc71 !important;
                }

                /* Bouton circulaire */
                .stSlider [role="slider"] {
                    width: 1.2rem !important;
                    height: 1.2rem !important;
                    background-color: #2ecc71 !important;
                    border: 2px solid white !important;
                }
                </style>
            """, unsafe_allow_html=True)

            # après selected_year = st.slider(...)
            selected_year = st.slider(
                "Sélectionner une année",
                min_value=min_year,
                max_value=max_year,
                value=max_year,
                step=1,
                label_visibility="collapsed",
            )

            # fonction de mapping année -> image
            def get_image_for_year(year: int) -> str:

                # 1. 1688–1715 : Louis XIV
                if year <= 1715:
                    return "src/assets/louis-xiv.png"

                # 2. 1716–1788 : Lumières
                elif year <= 1788:
                    return "src/assets/place-louis-xv.jpg"

                # 3. 1789–1799 : Révolution
                elif year <= 1799:
                    return "src/assets/rev.jpg"

                # 4. 1800–1815 : Premier Empire
                elif year <= 1815:
                    return "src/assets/napoleon.jpeg"

                # 5. 1816–1852 : Restauration / Monarchie de Juillet
                elif year <= 1852:
                    return "src/assets/monarchie-de-juillet.jpg"

                # 6. 1853–1870 : Haussmann
                elif year <= 1870:
                    return "src/assets/grands-boulevards.jpg"

                # 7. 1871 : Commune
                elif year == 1871:
                    return "src/assets/commune-paris.jpg"

                # 8. 1872–1900 : Belle Époque
                elif year <= 1900:
                    return "src/assets/eiffel.jpg"

                # 9. 1901–1918 : modernité + WW1
                elif year <= 1918:
                    return "src/assets/paris-1916.jpg"

                # 10. 1919–1939 : entre-deux-guerres
                elif year <= 1939:
                    return "src/assets/paris-1930.jpeg"

                # 11. 1940–1944 : occupation
                elif year <= 1944:
                    return "src/assets/paris-1940.jpeg"
                
                # 12. 1945 : libération
                elif year <= 1945:
                    return "src/assets/paris-liberation.jpeg"

                # 13. 1946–1970 : reconstruction & modernisation
                elif year <= 1970:
                    return "src/assets/trente-glorieuses.jpg"

                # 14. 1971–2000 : Paris contemporain
                elif year <= 2000:
                    return "src/assets/paris-1980.jpg"

                # 15. 2001-2010 : Paris contemporain
                elif year <= 2010:
                    return "src/assets/paris-2000.jpeg"
                
                # 16. 2011–2025 : Paris durable
                else:
                    return "src/assets/paris-2025.jpg"

            image_path = get_image_for_year(selected_year)


            # filtrage une seule fois
            year_col = pd.to_numeric(df["annee_ouverture"], errors="coerce")
            mask_year = year_col.notna() & (year_col <= selected_year)
            hist_df = df[mask_year].copy()
            hist_geo = hist_df[hist_df["geo_shape"].notna()].copy()
            hist_geo["geometry"] = hist_geo["geo_shape"].apply(
                lambda x: json.loads(x) if pd.notna(x) else None
            )
            hist_geo = hist_geo[hist_geo["geometry"].notna()]
            nb_ev = len(hist_geo)

            # 🟩 mise en page 2 colonnes pour tout le reste
            left_col, right_col = st.columns([1, 2])

            with left_col:
                # titre centré
                st.markdown(
                    f"""
                    <h3 style="text-align:center; margin-top:0;">
                        En
                        <span style="font-size:2.6rem; font-weight:1000; color:#2ecc71;">
                            {selected_year}
                        </span>
                    </h3>
                    """,
                    unsafe_allow_html=True,
                )

                # 3 sous-colonnes pour centrer l'image
                c1, c2, c3 = st.columns([1, 6, 1])
                with c2:
                    st.image(image_path, width=800)

                # 3 sous-colonnes pour centrer le texte
                t1, t2, t3 = st.columns([1, 2, 1])
                with t2:
                    pluriel = nb_ev > 1
                    texte = (
                        f"Il y avait déjà <span style='color:#2ecc71; font-size:1.8rem; font-weight:800;'>{nb_ev}</span> espaces verts qui existent encore aujourd'hui."
                        if pluriel
                        else f"Il y avait déjà <span style='color:#2ecc71; font-size:1.8rem; font-weight:800;'>{nb_ev}</span> espace vert qui existe encore aujourd'hui."
                    )
                    st.markdown(
                        f"""
                        <p style="
                            text-align:center;
                            font-weight:600;
                            font-size:1.1rem;
                            margin-top:1.2rem;
                        ">
                            {texte}
                        </p>
                        """,
                        unsafe_allow_html=True,
                    )

            with right_col:
                if hist_geo.empty:
                    st.warning("Aucun espace à afficher pour cette année.")
                else:
                    features = []

                    for _, row in hist_geo.iterrows():
                        year_val = pd.to_numeric(row.get("annee_ouverture", None), errors="coerce")
                        year_val = int(year_val) if pd.notna(year_val) else ""
                        features.append({
                            "type": "Feature",
                            "properties": {
                                "nom": row["nom"],
                                "annee_ouverture": year_val,
                                "fill_color": [46, 204, 113, 140],
                            },
                            "geometry": row["geometry"],
                        })

                    geojson_obj = {
                        "type": "FeatureCollection",
                        "features": features,
                    }

                    if {"latitude", "longitude"}.issubset(hist_geo.columns):
                        geo_pts = hist_geo[hist_geo["latitude"].notna() & hist_geo["longitude"].notna()]

                        if len(geo_pts) == 1:
                            # un seul lieu -> on zoom fort dessus
                            lat_center = float(geo_pts.iloc[0]["latitude"])
                            lon_center = float(geo_pts.iloc[0]["longitude"])
                            zoom_level = 14
                        elif len(geo_pts) > 1:
                            lat_min = geo_pts["latitude"].min()
                            lat_max = geo_pts["latitude"].max()
                            lon_min = geo_pts["longitude"].min()
                            lon_max = geo_pts["longitude"].max()

                            lat_center = (lat_min + lat_max) / 2
                            lon_center = (lon_min + lon_max) / 2

                            # on regarde à quel point c’est étalé pour adapter le zoom
                            span = max(lat_max - lat_min, lon_max - lon_min)
                            if span < 0.005:
                                zoom_level = 14
                            elif span < 0.01:
                                zoom_level = 13
                            elif span < 0.05:
                                zoom_level = 12
                            else:
                                zoom_level = 11
                        else:
                            # pas de coordonnées exploitables → vue Paris
                            lat_center = 48.8566
                            lon_center = 2.3522
                            zoom_level = 15
                    else:
                        # fallback si pas de colonnes latitude/longitude
                        lat_center = 48.8566
                        lon_center = 2.3522
                        zoom_level = 11

                    # si on est avant 1791 → zoom dynamique
                    if selected_year < 1791 and {"latitude", "longitude"}.issubset(hist_geo.columns):
                        pts = hist_geo[hist_geo["latitude"].notna() & hist_geo["longitude"].notna()]
                        if len(pts) >= 1:
                            lat_center = float(pts.iloc[0]["latitude"])
                            lon_center = float(pts.iloc[0]["longitude"])
                            zoom_level = 14
                        else:
                            # fallback paris
                            lat_center = 48.8566
                            lon_center = 2.3522
                            zoom_level = 11
                    else:
                        # à partir de 1791 on garde le zoom paris
                        lat_center = 48.8566
                        lon_center = 2.3522
                        zoom_level = 11

                    view_state = pdk.ViewState(
                        latitude=lat_center,
                        longitude=lon_center,
                        zoom=zoom_level,
                        pitch=0,
                    )

                    geojson_layer = pdk.Layer(
                        "GeoJsonLayer",
                        data=geojson_obj,
                        get_fill_color="properties.fill_color",
                        get_line_color=[0, 0, 0],
                        line_width_min_pixels=1,
                        pickable=True,
                    )

                    r = pdk.Deck(
                        layers=[geojson_layer],
                        initial_view_state=view_state,
                        tooltip={"text": "{nom}\nOuvert en {annee_ouverture}"},
                    )

                    st.pydeck_chart(r)


# ---------------------------------------------------------------------
# 3. ONGLET DONNÉES
# ---------------------------------------------------------------------
with tab_data:
    st.subheader("📋 Données")

    view_df = df.copy()

    # surface fusionnée
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

    def format_surface(x):
        if pd.isna(x):
            return ""
        try:
            x = int(float(x))
            return f"{x:,}".replace(",", " ")
        except Exception:
            return str(x)

    view_df["surface_affichee"] = view_df["surface"].apply(format_surface)

    # adresse
    addr_cols = [c for c in view_df.columns if "adresse" in c.lower()]
    if addr_cols:
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
        view_df["adresse"] = view_df[addr_cols].apply(join_addr, axis=1)
    else:
        view_df["adresse"] = view_df.get("code_postal", "").astype(str)

    # arrondissement affiché
    CP_OUTSIDE = {
        "92220": "Bagneux",
        "93210": "Saint-Denis",
        "93400": "Saint-Ouen",
        "93500": "Pantin",
        "94200": "Ivry-sur-Seine",
        "94300": "Vincennes",
        "94320": "Thiais",
    }

    def format_arrondissement(row):
        cp = str(row.get("code_postal", "")).strip()
        arr = str(row.get("arrondissement", "")).strip()

        if cp in CP_OUTSIDE:
            return CP_OUTSIDE[cp]

        if cp.startswith("75") and len(arr) == 2 and arr.isdigit():
            n = int(arr)
            if n == 1:
                return "1er"
            else:
                return f"{n}e"

        if "commune" in row and str(row["commune"]).strip().lower() not in ["", "nan", "none"]:
            return str(row["commune"]).strip()

        return cp

    view_df["arrondissement_affiche"] = view_df.apply(format_arrondissement, axis=1)

    cols_to_show = [
        "nom",
        "categorie",
        "adresse",
        "arrondissement_affiche",
        "surface_affichee",
    ]
    if "annee_ouverture" in view_df.columns:
        cols_to_show.append("annee_ouverture")
    if "presence_cloture" in view_df.columns:
        cols_to_show.append("presence_cloture")
    if "ouverture_24h" in view_df.columns:
        cols_to_show.append("ouverture_24h")

    id_cols = [c for c in view_df.columns if c.lower() in ["id", "identifiant", "index"]]
    cols_to_show = [c for c in cols_to_show if c not in id_cols]

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

    export_cols = [
        "nom",
        "categorie",
        "adresse",
        "arrondissement",
        "code_postal",
        "surface",
    ]
    if "annee_ouverture" in view_df.columns:
        export_cols.append("annee_ouverture")
    if "presence_cloture" in view_df.columns:
        export_cols.append("presence_cloture")
    if "ouverture_24h" in view_df.columns:
        export_cols.append("ouverture_24h")

    st.download_button(
        "⬇️ Télécharger les données (CSV)",
        data=view_df[export_cols].to_csv(index=False, sep=";"),
        file_name="espaces_verts_paris.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------------
# 4. ONGLET STATISTIQUES
# ---------------------------------------------------------------------
with tab_stats:
    import altair as alt

    st.subheader("📈 Statistiques")

    # Palettes
    green_palette = ["#2ecc71", "#27ae60", "#1e8449", "#16a085", "#58d68d"]
    multi_palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf"
    ]

    # ------------- DONUT CHART -------------
    st.markdown("## 🟩 Répartition du nombre d'espaces par catégorie")

    cat_counts = df["categorie"].value_counts().reset_index()
    cat_counts.columns = ["Catégorie", "Nb"]

    donut = alt.Chart(cat_counts).mark_arc(innerRadius=70).encode(
        theta="Nb:Q",
        color=alt.Color("Catégorie:N", scale=alt.Scale(range=multi_palette)),
        tooltip=["Catégorie", "Nb"]
    )

    st.altair_chart(donut, use_container_width=True)
    st.divider()

    # ------------- SURFACE PAR CATÉGORIE -------------
    st.markdown("## 🌿 Surface totale par catégorie")

    if "surface_totale_reelle_m2" in df.columns:
        surf = df.groupby("categorie")["surface_totale_reelle_m2"].sum().reset_index()
        surf.columns = ["Catégorie", "Surface totale"]

        bars = alt.Chart(surf).mark_bar(color="#27ae60").encode(
            x="Surface totale:Q",
            y=alt.Y("Catégorie:N", sort="-x"),
            tooltip=["Catégorie", "Surface totale"]
        )
        st.altair_chart(bars, use_container_width=True)
    else:
        st.info("Pas de surface disponible.")

    st.divider()

    # ------------- HEATMAP CAT × ARR -------------
    st.markdown("## 🗺️ Répartition par arrondissement")

    heat = (
        df.groupby(["arrondissement_affiche", "categorie"])
        .size()
        .reset_index(name="Nb")
    )

    heatmap = alt.Chart(heat).mark_rect().encode(
        x=alt.X("arrondissement_affiche:N", title="Arrondissement"),
        y=alt.Y("categorie:N", title="Catégorie"),
        color=alt.Color("Nb:Q", scale=alt.Scale(scheme="greens")),
        tooltip=["arrondissement_affiche", "categorie", "Nb"]
    )

    st.altair_chart(heatmap, use_container_width=True)
    st.divider()

    # ------------- OUVERT 24H/24 PAR CAT -------------
    st.markdown("## ⭐ Taux d'espaces ouverts 24h/24 par catégorie")

    if "ouverture_24h" in df.columns:
        open_rate = (
            df.groupby("categorie")["ouverture_24h"]
            .mean()
            .reset_index()
            .sort_values("ouverture_24h")
        )
        open_rate["Pourcentage"] = open_rate["ouverture_24h"] * 100

        scatter = alt.Chart(open_rate).mark_circle(size=200, color="#1e8449").encode(
            x=alt.X("Pourcentage:Q", title="% ouverts 24h/24"),
            y=alt.Y("categorie:N", title="Catégorie", sort="-x"),
            tooltip=["categorie", "Pourcentage"]
        )
        st.altair_chart(scatter, use_container_width=True)
    else:
        st.info("Données 24h/24 indisponibles.")

    st.divider()

    # ------------- COURBE + ZONE PAR DÉCENNIE -------------
    st.markdown("## 🕰️ Nombre d'espaces créés par décennie")

    if "annee_ouverture" in df.columns:
        years = pd.to_numeric(df["annee_ouverture"], errors="coerce").dropna()
        decades = ((years // 10) * 10).value_counts().sort_index().reset_index()
        decades.columns = ["Décennie", "Nombre"]

        # Filtrer pour éviter l'affichage inutile (max = dernière décennie réelle)
        last_decade = decades["Décennie"].max()
        decades = decades[decades["Décennie"] <= last_decade]

        area = alt.Chart(decades).mark_area(
            color="#2ecc71",
            opacity=0.4
        ).encode(
            x=alt.X("Décennie:Q"),
            y=alt.Y("Nombre:Q"),
            tooltip=["Décennie", "Nombre"]
        )

        line = alt.Chart(decades).mark_line(color="#1e8449").encode(
            x="Décennie:Q",
            y="Nombre:Q"
        )

        st.altair_chart(area + line, use_container_width=True)
    else:
        st.info("Pas d'années d'ouverture.")

    st.divider()

    # ------------- BOX PLOT DES SURFACES -------------
    st.markdown("## 📏 Distribution des surfaces par catégorie")

    if "surface_totale_reelle_m2" in df.columns:
        # Limiter à 300k pour visualisation
        df_box = df.copy()
        df_box["surface_totale_reelle_m2"] = df_box["surface_totale_reelle_m2"].clip(upper=300000)

        box = alt.Chart(df_box).mark_boxplot(extent="min-max").encode(
            x=alt.X("categorie:N", title="Catégorie"),
            y=alt.Y("surface_totale_reelle_m2:Q", title="Surface (m²)", scale=alt.Scale(domain=[0, 300000])),
            color=alt.Color("categorie:N", scale=alt.Scale(range=multi_palette)),
        )
        st.altair_chart(box, use_container_width=True)
    else:
        st.info("Pas de surfaces disponibles.")
