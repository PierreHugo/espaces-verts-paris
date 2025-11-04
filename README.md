# 🌿 Data Visualization – Espaces Verts

Projet individuel réalisé dans le cadre du cours **Data Visualization** (EFREI – ING2-APP-BDML1).  
L’objectif est d’explorer et de visualiser les **espaces verts de Paris** afin de mieux comprendre leur répartition et leurs caractéristiques via une application **Streamlit** interactive.

---

## 📊 Description
Le projet s’appuie sur un jeu de données répertoriant les espaces verts de la Ville de Paris (parcs, jardins, squares, cimetières, etc.).  
Les données ont été nettoyées et normalisées pour permettre une visualisation fluide dans un tableau de bord Streamlit.

---

## 📁 Structure du projet
```
espaces-verts-paris/
├── src/
│   ├── espaces_verts.csv                # Jeu de données brut
│   ├── espaces_verts_normalized.csv     # Jeu de données nettoyé
│   └── load_data.py                     # Script de nettoyage
├── app.py                               # Application Streamlit
├── inspect_data.py                      # Script d'exploration rapide
├── requirements.txt                     # Dépendances Python
└── README.md
```

---

## ⚙️ Installation & Exécution

### 🔸 1. Cloner le projet
```bash
git clone <url-du-repo>
cd espaces-verts-paris
```

---

### 🔸 2. Créer et activer l’environnement virtuel

#### 💻 Sur macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 🪟 Sur Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 🔸 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

---

### 🔸 4. Lancer l’application Streamlit
```bash
streamlit run app.py
```

Puis ouvre ton navigateur sur l’adresse affichée (en général http://localhost:8501).

---

## 🧩 Technologies utilisées
- **Python 3.11+**
- **Pandas** → manipulation et nettoyage des données  
- **Streamlit** → visualisation et interface web  
- **Altair / Pydeck** → graphiques et cartes interactives  

---

## 👤 Auteur
Projet réalisé par **Pierre-Hugo HERRAN**  
Cours : *Data Visualization – ING2-APP-BDML1*  
Année : 2025/2026
