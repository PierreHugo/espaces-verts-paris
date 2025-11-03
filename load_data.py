import sys
import csv
import pandas as pd

# augmenter la limite des champs pour le module csv
csv.field_size_limit(sys.maxsize)

# chemin vers ton fichier
file_path = "src/espaces_verts.csv"

try:
    df = pd.read_csv(
        file_path,
        sep=";",           # ton CSV est visiblement en ;
        encoding="utf-8",
        engine="python"
    )

    print("✅ Données chargées avec succès !")
    print("Shape :", df.shape)
    print("\nColonnes :")
    print(df.columns.tolist())
    print("\nAperçu :")
    print(df.head())

except FileNotFoundError:
    print(f"❌ Le fichier {file_path} est introuvable.")
except Exception as e:
    print(f"⚠️ Une erreur est survenue : {e}")
