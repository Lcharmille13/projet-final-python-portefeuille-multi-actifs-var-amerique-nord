# Portefeuille multi-actifs — Amérique du Nord

Projet final du cours **Python pour la Data Science**, réalisé par trois étudiants.

Nous simulons le rôle d'une équipe d'investissement européenne (assureur, par exemple). L'objectif est d'analyser un portefeuille de 5 ETF nord-américains en euros, d'évaluer son risque à un an (VaR à 99,5 % et Expected Shortfall) et de présenter les résultats dans un tableau de bord interactif.

*Projet à visée pédagogique, ne constituant pas une recommandation d'investissement.*

## Portefeuille

| ETF | Exposition | Poids égaux | Poids alternatifs |
|---|---|---:|---:|
| SPY | Grandes entreprises américaines | 20 % | 40 % |
| QQQ | Nasdaq-100 (technologie) | 20 % | 10 % |
| IWM | Petites entreprises américaines | 20 % | 10 % |
| EWC | Actions canadiennes | 20 % | 20 % |
| VNQ | Immobilier coté américain | 20 % | 20 % |

## Données

- **Source :** Yahoo Finance (`yfinance`).
- **Période :** du 02/01/2015 au 20/11/2026 (2 990 séances).
- Prix de clôture ajustés (dividendes et divisions d'actions).
- Conversion en euros : `prix USD / EURUSD`, avec report du dernier taux connu en cas de donnée manquante.
- Données stockées en CSV, permettant une utilisation hors connexion.

## Installation

Prérequis : **Python 3.14**.

Depuis la racine du projet, créer et activer un environnement virtuel.

**Windows (PowerShell) :**

```powershell
py -V:3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux :**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Installer les dépendances :

```bash
python -m pip install -r requirements.txt
```

## Utilisation

Depuis la racine du projet, avec l'environnement virtuel activé :

1. **Actualisation facultative des données** (Internet nécessaire) : `python src/collecte_donnees.py`
2. **Analyse :** ouvrir `notebooks/analyse_portefeuille.ipynb` dans VS Code ou Jupyter, sélectionner le kernel `.venv` et lancer *Run All* (environ 30 s).
3. **Dashboard :** lancer `streamlit run dashboard/app.py`, accessible sur http://localhost:8501. Arrêt avec `Ctrl + C`.

## Organisation du projet

| Fichier ou dossier | Contenu |
|---|---|
| `data/raw/` | Données brutes |
| `data/processed/` | Prix en euros |
| `notebooks/` | Analyse, simulation et conclusion |
| `src/collecte_donnees.py` | Collecte et conversion |
| `src/analysis.py` | Analyse financière et statistiques |
| `src/risk.py` | Simulations et mesures de risque |
| `dashboard/app.py` | Dashboard Streamlit et Plotly |
| `.streamlit/config.toml` | Thème du dashboard |
| `requirements.txt` | Dépendances |
| `DECLARATION_IA.md` | Déclaration d'utilisation de l'IA |
| `README.md` | Documentation |

Le notebook et le dashboard utilisent les mêmes fonctions de `src/`, garantissant des résultats identiques.

## Méthodologie

- Capital initial fictif de **100 000 €**, avec rééquilibrage quotidien.
- Rendements simples quotidiens, annualisation géométrique et volatilité annualisée sur 252 séances (écart-type quotidien × √252).
- Simulation à un an : **100 000 scénarios**, avec une graine fixe (42).
- Deux méthodes : bootstrap historique avec remise et loi normale calibrée sur la moyenne et l'écart-type historiques.
- Implémentation par boucles Python et vectorisation NumPy par blocs.
- Perte = valeur initiale − valeur finale.
- **VaR 99,5 % :** seuil de perte dépassé dans 0,5 % des scénarios.
- **Expected Shortfall :** perte moyenne dans ces scénarios.

## Principaux résultats

Portefeuille équipondéré, capital initial de 100 000 €.

| Indicateur | Valeur |
|---|---:|
| Valeur au 20/11/2026 | 359 963 € |
| Rendement annualisé | 11,40 % |
| Volatilité annualisée | 19,50 % |
| Perte maximale (mars 2020) | −36,79 % |
| VaR 99,5 % à un an (bootstrap) | 33 417 € |
| Expected Shortfall 99,5 % (bootstrap) | 37 778 € |

*Ces résultats dépendent des hypothèses retenues et ne garantissent pas les pertes futures.*
