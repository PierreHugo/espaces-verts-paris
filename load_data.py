import sys
import csv
import pandas as pd

# pour éviter l'erreur "field larger than field limit"
csv.field_size_limit(sys.maxsize)

INPUT_PATH = "src/espaces_verts.csv"
OUTPUT_PATH = "src/espaces_verts_normalized.csv"

# 1. lire le csv brut
df = pd.read_csv(
    INPUT_PATH,
    sep=";",
    encoding="utf-8",
    engine="python",
    on_bad_lines="skip"
)

# 2. renommer les colonnes -> snake_case
rename_map = {
    "Identifiant espace vert": "id_espace_vert",
    "Nom de l'espace vert": "nom",
    "Typologie d'espace vert": "typologie",
    "Catégorie": "categorie",
    "Adresse - Numéro": "adresse_numero",
    "Adresse - Complément": "adresse_complement",
    "Adresse - type voie": "adresse_type_voie",
    "Adresse - Libellé voie": "adresse_libelle_voie",
    "Code postal": "code_postal",
    "Surface calculée": "surface_calculee_m2",
    "Superficie totale réelle": "surface_totale_reelle_m2",
    "Surface horticole": "surface_horticole_m2",
    "Présence cloture": "presence_cloture",
    "Périmètre": "perimetre_m",
    "Année de l'ouverture": "annee_ouverture",
    "Année de rénovation": "annee_renovation",
    "Ancien nom de l'espace vert": "ancien_nom",
    "Année de changement de nom": "annee_changement_nom",
    "Nombre d'entités": "nb_entites",
    "Ouverture 24h_24h": "ouverture_24h",
    "ID_DIVISION": "id_division",
    "ID_ATELIER_HORTICOLE": "id_atelier_horticole",
    "IDA3D_ENB": "ida3d_enb",
    "SITE_VILLES": "site_villes",
    "ID_EQPT": "id_eqpt",
    "Compétence": "competence",
    "Geo Shape": "geo_shape",
    "URL_PLAN": "url_plan",
    "Geo point": "geo_point",
    "last_edited_user": "last_edited_user",
    "last_edited_date": "last_edited_date",
}
df = df.rename(columns=rename_map)

# 2bis. supprimer les colonnes inutiles
cols_to_drop = [
    "id_division",
    "id_atelier_horticole",
    "ida3d_enb",
    "site_villes",
    "id_eqpt",
    "competence",
    "url_plan",
    "last_edited_user",
    "last_edited_date",
]
df = df.drop(columns=cols_to_drop, errors="ignore")

# 2ter. séparer la colonne geo_point en latitude et longitude
if "geo_point" in df.columns:
    try:
        df[["latitude", "longitude"]] = df["geo_point"].str.split(",", expand=True)
        df["latitude"] = df["latitude"].astype(str).str.strip().astype(float)
        df["longitude"] = df["longitude"].astype(str).str.strip().astype(float)
    except Exception as e:
        print(f"⚠️ Impossible de séparer geo_point : {e}")

# 3. normaliser les champs oui/non
def normalize_yes_no(val):
    if pd.isna(val):
        return pd.NA
    v = str(val).strip().lower()
    if v in ("oui", "o", "yes", "y", "true"):
        return True
    if v in ("non", "n", "no", "f", "false"):
        return False
    return pd.NA

if "presence_cloture" in df.columns:
    df["presence_cloture"] = df["presence_cloture"].apply(normalize_yes_no)

if "ouverture_24h" in df.columns:
    df["ouverture_24h"] = df["ouverture_24h"].apply(normalize_yes_no)

# 4. enlever les années "9999" qui sont des placeholders
year_like_cols = [
    "annee_ouverture",
    "annee_renovation",
    "annee_changement_nom",
]
for col in year_like_cols:
    if col in df.columns:
        # on met en numérique pour choper les 9999 même s'ils sont en str
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df.loc[df[col] == 9999, col] = pd.NA

# 4bis. si jamais surface est 9999 (ça peut arriver), on les vire aussi
surface_like_cols = [
    "surface_totale_reelle_m2",
    "surface_calculee_m2",
    "surface_horticole_m2",
]
for col in surface_like_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df.loc[df[col] == 9999, col] = pd.NA

# 5. recaster quelques colonnes numériques
for col in [
    "id_espace_vert",
    "adresse_numero",
    "code_postal",
    "annee_ouverture",
    "annee_renovation",
    "annee_changement_nom",
    "nb_entites",
]:
    if col in df.columns:
        df[col] = df[col].astype("Int64")

# 6. filtrer les catégories pertinentes
categories_a_garder = [
    "Bois",
    "Parc",
    "Square",
    "Jardin",
    "Jardin partage",
    "Promenade",
    "Mail",
    "Pelouse",
    "Terrain de boules",
    "Foret urbaine",   # <- sans accent comme dans le CSV
    "Ile",
    "Cimetière",
]

nb_total = len(df)
df = df[df["categorie"].isin(categories_a_garder)]
nb_filtre = len(df)

print(f"✅ Filtrage appliqué : {nb_filtre} / {nb_total} lignes conservées ({nb_filtre/nb_total:.1%})")
print("📚 Catégories conservées :", ", ".join(categories_a_garder))

# 7. corriger les nb_entites incohérents (0, NaN -> 1)
if "nb_entites" in df.columns:
    df["nb_entites"] = df["nb_entites"].apply(
        lambda x: 1 if pd.isna(x) or x <= 0 else x
    )

# 8. compter les cellules vides / NaN par colonne (après nettoyage des 9999)
print("\n=== Valeurs manquantes après nettoyage (y compris 9999) ===")
na_counts = df.isna().sum().sort_values(ascending=False)
print(na_counts)

# 9. sauvegarder
df.to_csv(OUTPUT_PATH, index=False, sep=";", encoding="utf-8")

print("✅ Fichier nettoyé écrit dans :", OUTPUT_PATH)
print("📏 Lignes / colonnes :", df.shape)
