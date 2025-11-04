import pandas as pd

# chemin vers le fichier déjà nettoyé
FILE_PATH = "src/espaces_verts_normalized.csv"

df = pd.read_csv(FILE_PATH, sep=";", encoding="utf-8")

print("✅ Fichier chargé")
print("📏 Shape :", df.shape)
print("\n--- Aperçu ---")
print(df.head())

# 1. infos générales
print("\n=== Info ===")
print(df.info())

# 2. valeurs manquantes
print("\n=== Valeurs manquantes par colonne ===")
print(df.isna().sum().sort_values(ascending=False))

# 3. répartition par catégorie
print("\n=== Répartition par catégorie ===")
print(df["categorie"].value_counts())

# 4. top 10 des plus grandes surfaces (si la colonne existe)
surface_cols = ["surface_totale_reelle_m2", "surface_calculee_m2", "surface_horticole_m2"]
for col in surface_cols:
    if col in df.columns:
        print(f"\n=== Top 10 par {col} ===")
        print(
            df[["nom", "categorie", col]]
            .sort_values(by=col, ascending=False)
            .head(10)
        )

# 5. vérif coordonnées
if {"latitude", "longitude"}.issubset(df.columns):
    nb_na_lat = df["latitude"].isna().sum()
    nb_na_lon = df["longitude"].isna().sum()
    print("\n=== Coordonnées ===")
    print(f"lignes sans latitude : {nb_na_lat}")
    print(f"lignes sans longitude : {nb_na_lon}")

# 6. lieux hors Paris (code postal ne commençant pas par 75)
if "code_postal" in df.columns:
    df["code_postal_str"] = df["code_postal"].astype(str).str.strip()
    hors_paris = df[~df["code_postal_str"].str.startswith("75", na=False)].copy()

    print("\n=== Lieux hors Paris (code postal ne commençant pas par 75) ===")
    print(f"Nombre de lignes hors Paris : {len(hors_paris)}")

    if len(hors_paris):
        # on récupère aussi les colonnes d'adresse si elles existent
        adresse_cols = [c for c in df.columns if "adresse" in c.lower()]
        cols = ["nom", "code_postal", "commune"] if "commune" in df.columns else ["nom", "code_postal"]
        cols = cols + adresse_cols

        # on évite de planter si certaines colonnes manquent
        cols = [c for c in cols if c in hors_paris.columns]

        print(hors_paris[cols].sort_values("code_postal").to_string(index=False))
else:
    print("\n⚠️ Pas de colonne 'code_postal', impossible de détecter les lieux hors Paris.")
