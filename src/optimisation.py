"""
optimisation.py : EXTENSION - optimiser la répartition du portefeuille avec SciPy.

Idée : au lieu de choisir les poids "au feeling", on les calcule.
  - variance minimale : les poids qui donnent le portefeuille le MOINS volatil ;
  - Sharpe maximal    : les poids qui donnent le meilleur rendement par unité de risque.
Contraintes : poids >= 0 (pas de vente à découvert), somme = 1, chaque poids <= MAX_WEIGHT.

Précaution importante : on optimise sur une période d'ENTRAÎNEMENT (2015-2022) et on juge
sur une période de TEST (2023-2026) que l'optimiseur n'a jamais vue. Optimiser et évaluer
sur les mêmes données donnerait des résultats trop beaux.

Usage dans le notebook :
    from src.optimisation import *
Test depuis le terminal (racine du projet) :
    python src/optimisation.py
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize

try:                                   # import depuis le notebook (racine du projet)
    from src.analysis import (load_prices, compute_returns, portfolio_returns,
                              stats_table, TRADING_DAYS, WEIGHTS_EQUAL)
    from src.risk import simulate_bootstrap_vec, risk_metrics
except ModuleNotFoundError:            # lancement direct : python src/optimisation.py
    from analysis import (load_prices, compute_returns, portfolio_returns,
                          stats_table, TRADING_DAYS, WEIGHTS_EQUAL)
    from risk import simulate_bootstrap_vec, risk_metrics

# --------------------------------------------------------------------------
# Paramètres
# --------------------------------------------------------------------------
MAX_WEIGHT = 0.60                # un actif ne peut pas peser plus de 60 % (évite le "tout sur un seul")
SPLIT_DATE = "2023-01-01"        # entraînement avant cette date, test à partir de cette date
RISK_FREE = 0.0                  # taux sans risque annuel (simplification : 0)


# --------------------------------------------------------------------------
# 1. Outils : rendement et risque annualisés d'un jeu de poids
# --------------------------------------------------------------------------
def annual_inputs(returns: pd.DataFrame):
    """Rendement moyen annuel de chaque actif (mu) et matrice de covariance annuelle (cov)."""
    mu = returns.mean() * TRADING_DAYS
    cov = returns.cov() * TRADING_DAYS
    return mu, cov


def portfolio_stats(w, mu, cov):
    """Rendement et volatilité annuels d'un portefeuille de poids w."""
    ret = float(w @ mu)
    vol = float(np.sqrt(w @ cov.values @ w))
    return ret, vol


# --------------------------------------------------------------------------
# 2. Optimisation
# --------------------------------------------------------------------------
def optimize_weights(returns: pd.DataFrame, objective="min_variance",
                     max_weight=MAX_WEIGHT, risk_free=RISK_FREE) -> dict:
    """
    Cherche les poids optimaux avec SLSQP (méthode de SciPy pour les problèmes sous contraintes).
    objective : "min_variance" ou "max_sharpe".
    Renvoie un dictionnaire {actif: poids}, utilisable comme WEIGHTS_EQUAL.
    """
    mu, cov = annual_inputs(returns)
    n = len(mu)

    if objective == "min_variance":
        def to_minimize(w):
            return w @ cov.values @ w                       # variance du portefeuille
    elif objective == "max_sharpe":
        def to_minimize(w):
            ret, vol = portfolio_stats(w, mu, cov)
            return -(ret - risk_free) / vol                 # on minimise l'opposé du Sharpe
    else:
        raise ValueError("objective doit être 'min_variance' ou 'max_sharpe'")

    result = minimize(
        to_minimize,
        x0=np.full(n, 1 / n),                                # point de départ : poids égaux
        method="SLSQP",
        bounds=[(0, max_weight)] * n,                        # 0 <= poids <= max_weight
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],   # somme des poids = 1
    )
    if not result.success:
        raise RuntimeError(f"L'optimisation n'a pas convergé : {result.message}")
    w = np.clip(result.x, 0, None)
    w = np.round(w / w.sum(), 4)                             # nettoyage des erreurs d'arrondi
    w[np.argmax(w)] += round(1 - w.sum(), 4)                 # l'arrondi ne doit pas casser "somme = 1"
    return {c: float(x) for c, x in zip(returns.columns, w)}


def efficient_frontier(returns: pd.DataFrame, n_points=30, max_weight=MAX_WEIGHT) -> pd.DataFrame:
    """
    Frontière efficiente : pour chaque rendement cible, le portefeuille de risque minimal.
    Renvoie un tableau (rendement, volatilité) à tracer.
    """
    mu, cov = annual_inputs(returns)
    n = len(mu)
    targets = np.linspace(mu.min(), mu.max(), n_points)
    rows = []
    for target in targets:
        res = minimize(
            lambda w: w @ cov.values @ w,
            x0=np.full(n, 1 / n), method="SLSQP",
            bounds=[(0, max_weight)] * n,
            constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1},
                         {"type": "eq", "fun": lambda w, t=target: w @ mu - t}],
        )
        if res.success:
            ret, vol = portfolio_stats(res.x, mu, cov)
            rows.append({"Rendement": ret, "Volatilité": vol})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 3. Évaluation honnête : entraînement / test
# --------------------------------------------------------------------------
def split_returns(returns: pd.DataFrame, split_date=SPLIT_DATE):
    """Sépare les rendements en période d'entraînement et période de test."""
    date = pd.Timestamp(split_date)
    return returns.loc[returns.index < date], returns.loc[returns.index >= date]


def train_test_comparison(returns: pd.DataFrame, split_date=SPLIT_DATE):
    """
    Optimise sur l'entraînement, puis compare sur le TEST (jamais vu) :
    poids égaux, variance minimale, Sharpe maximal.
    Renvoie (poids, statistiques sur le test).
    """
    train, test = split_returns(returns, split_date)
    weights = {
        "Poids égaux": {c: 1 / returns.shape[1] for c in returns.columns},
        "Variance minimale": optimize_weights(train, "min_variance"),
        "Sharpe maximal": optimize_weights(train, "max_sharpe"),
    }
    test_returns = pd.DataFrame({name: portfolio_returns(test, w) for name, w in weights.items()})
    return pd.DataFrame(weights), stats_table(test_returns)


def var_of_weights(returns: pd.DataFrame, weights: dict, n_scenarios=100_000) -> dict:
    """VaR 99,5 % et ES sur 1 an d'un jeu de poids (bootstrap NumPy de risk.py)."""
    return risk_metrics(simulate_bootstrap_vec(portfolio_returns(returns, weights), n_scenarios))


# --------------------------------------------------------------------------
# Test rapide
# --------------------------------------------------------------------------
if __name__ == "__main__":
    rend = compute_returns(load_prices())
    train, test = split_returns(rend)
    print(f"Entraînement : {train.index.min().date()} -> {train.index.max().date()} ({len(train)} jours)")
    print(f"Test         : {test.index.min().date()} -> {test.index.max().date()} ({len(test)} jours)\n")

    poids, stats_test = train_test_comparison(rend)
    print("Poids calculés sur l'entraînement :")
    print(poids.round(3).to_string(), "\n")
    print("Résultats sur la période de TEST (jamais vue par l'optimiseur) :")
    print(stats_test.round(4).to_string(), "\n")

    print("VaR 99,5 % sur 1 an, optimisation sur TOUTE la période (poids variance minimale) :")
    w_full = optimize_weights(rend, "min_variance")
    print(w_full)
    for nom, w in [("Poids égaux", WEIGHTS_EQUAL if set(WEIGHTS_EQUAL) == set(rend.columns)
                    else {c: 1 / rend.shape[1] for c in rend.columns}), ("Variance minimale", w_full)]:
        m = var_of_weights(rend, w)
        print(f"  {nom:18s} VaR {m['VaR 99,5 % (%)']:.1%}   ES {m['Expected Shortfall (%)']:.1%}")
