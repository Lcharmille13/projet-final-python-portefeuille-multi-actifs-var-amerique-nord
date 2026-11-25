"""
analysis.py : analyse descriptive des actifs et du portefeuille (prix en euros).

Usage dans le notebook :
    from src.analysis import *
    prix = load_prices()
    rendements = compute_returns(prix)
Test rapide depuis le terminal :
    python src/analysis.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Paramètres
# --------------------------------------------------------------------------
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "prix_etf_eur.csv"
TRADING_DAYS = 252          # nombre de jours de cotation par an

# Deux répartitions à comparer (les poids de chaque dictionnaire somment à 1).
# Les clés doivent correspondre aux colonnes du CSV : à adapter si le panier change.
WEIGHTS_EQUAL = {"SPY": 0.2, "QQQ": 0.2, "IWM": 0.2, "EWC": 0.2, "VNQ": 0.2}
WEIGHTS_ALT = {"SPY": 0.40, "QQQ": 0.10, "IWM": 0.10, "EWC": 0.20, "VNQ": 0.20}


# --------------------------------------------------------------------------
# 1. Chargement et rendements
# --------------------------------------------------------------------------
def load_prices(path: Path = DATA_PATH) -> pd.DataFrame:
    """Prix en euros : une ligne par date, une colonne par actif."""
    return pd.read_csv(path, index_col="Date", parse_dates=True).sort_index()


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Rendements quotidiens simples : prix(t) / prix(t-1) - 1."""
    return prices.pct_change().dropna()


# --------------------------------------------------------------------------
# 2. Volatilité glissante et drawdown
# --------------------------------------------------------------------------
def rolling_volatility(returns: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Volatilité annualisée sur une fenêtre glissante de `window` jours."""
    return returns.rolling(window).std() * np.sqrt(TRADING_DAYS)


def drawdown(values: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """
    Perte depuis le plus haut atteint : valeur / plus haut historique - 1.
    Toujours <= 0 (0 = on est au plus haut, -0.30 = 30 % sous le plus haut).
    """
    return values / values.cummax() - 1


# --------------------------------------------------------------------------
# 3. Portefeuille
# --------------------------------------------------------------------------
def check_weights(weights: dict, columns) -> pd.Series:
    """Vérifie que les poids correspondent aux actifs et somment à 1."""
    w = pd.Series(weights, dtype=float)
    missing = set(columns) - set(w.index)
    extra = set(w.index) - set(columns)
    if missing or extra:
        raise ValueError(f"Actifs manquants : {missing}, en trop : {extra}")
    if not np.isclose(w.sum(), 1.0):
        raise ValueError(f"Les poids somment à {w.sum():.4f}, pas à 1")
    return w[list(columns)]


def portfolio_returns(returns: pd.DataFrame, weights: dict) -> pd.Series:
    """
    Rendement quotidien du portefeuille = somme des poids x rendements des actifs.
    Hypothèse : les poids sont remis aux valeurs cibles chaque jour (rééquilibrage quotidien).
    """
    w = check_weights(weights, returns.columns)
    return returns.mul(w, axis=1).sum(axis=1)


def portfolio_value(returns: pd.DataFrame, weights: dict, initial: float = 100.0) -> pd.Series:
    """Valeur du portefeuille dans le temps, en euros (départ : `initial`)."""
    return initial * (1 + portfolio_returns(returns, weights)).cumprod()


# --------------------------------------------------------------------------
# 4. Tableau de statistiques
# --------------------------------------------------------------------------
def annualized_return(returns: pd.DataFrame | pd.Series):
    """Rendement annualisé géométrique : (croissance totale) ^ (252 / nb de jours) - 1."""
    return (1 + returns).prod() ** (TRADING_DAYS / len(returns)) - 1


def annualized_volatility(returns: pd.DataFrame | pd.Series):
    """Volatilité annualisée : écart-type quotidien x racine de 252."""
    return returns.std() * np.sqrt(TRADING_DAYS)


def max_drawdown(returns: pd.DataFrame | pd.Series):
    """Perte maximale : le pire drawdown de la période."""
    cumulative = (1 + returns).cumprod()
    return drawdown(cumulative).min()


def stats_table(returns: pd.DataFrame) -> pd.DataFrame:
    """Tableau de statistiques : une ligne par actif (ou portefeuille)."""
    return pd.DataFrame({
        "Rendement annualisé": annualized_return(returns),
        "Volatilité annualisée": annualized_volatility(returns),
        "Perte maximale": max_drawdown(returns),
    })


def portfolios_comparison(returns: pd.DataFrame) -> pd.DataFrame:
    """Statistiques des deux répartitions, côte à côte."""
    port = pd.DataFrame({
        "Poids égaux": portfolio_returns(returns, WEIGHTS_EQUAL),
        "Répartition alternative": portfolio_returns(returns, WEIGHTS_ALT),
    })
    return stats_table(port)


# --------------------------------------------------------------------------
# Test rapide
# --------------------------------------------------------------------------
if __name__ == "__main__":
    prix = load_prices()
    rend = compute_returns(prix)
    print(f"{len(prix)} jours, de {prix.index.min().date()} à {prix.index.max().date()}\n")
    print("Statistiques par actif :")
    print(stats_table(rend).round(4), "\n")
    print("Corrélations :")
    print(rend.corr().round(2), "\n")
    print("Comparaison des portefeuilles :")
    print(portfolios_comparison(rend).round(4))
