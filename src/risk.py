"""
risk.py : simulation du risque du portefeuille sur 1 an, VaR 99,5 % et Expected Shortfall.

Deux méthodes de simulation :
  1. "bootstrap"  : on tire au hasard des jours du passé (avec remise) ;
  2. "normale"    : on tire des rendements dans une loi normale (moyenne et écart-type du passé).
Chaque méthode existe en deux versions :
  - version BOUCLES (Python pur, lente, facile à lire) ;
  - version VECTORISÉE (NumPy, rapide).

Usage dans le notebook :
    from src.risk import *
Test depuis le terminal (racine du projet) :
    python src/risk.py
"""
import random
import time

import numpy as np
import pandas as pd

try:                                   # import depuis le notebook (racine du projet)
    from src.analysis import (load_prices, compute_returns, portfolio_returns,
                              WEIGHTS_EQUAL, WEIGHTS_ALT)
except ModuleNotFoundError:            # lancement direct : python src/risk.py
    from analysis import (load_prices, compute_returns, portfolio_returns,
                          WEIGHTS_EQUAL, WEIGHTS_ALT)

# --------------------------------------------------------------------------
# Paramètres
# --------------------------------------------------------------------------
HORIZON = 252             # 1 an = environ 252 jours de cotation
N_SCENARIOS = 100_000     # le sujet demande au moins 100 000 scénarios
INITIAL = 100.0           # valeur de départ du portefeuille (en euros)
LEVEL = 0.995             # niveau de la VaR
SEED = 42                 # graine : mêmes résultats à chaque exécution
CHUNK = 10_000            # nb de scénarios traités à la fois (limite la mémoire)


# --------------------------------------------------------------------------
# 1. Versions BOUCLES (Python pur)
# --------------------------------------------------------------------------
def simulate_bootstrap_loop(returns, n_scenarios, horizon=HORIZON, initial=INITIAL, seed=SEED):
    """Chaque scénario : 252 jours tirés au hasard dans le passé, un par un."""
    random.seed(seed)
    r = list(returns)
    n = len(r)
    finals = []
    for _ in range(n_scenarios):                 # boucle sur les scénarios
        value = initial
        for _ in range(horizon):                 # boucle sur les jours
            value *= 1 + r[random.randrange(n)]  # on applique le rendement d'un jour tiré au hasard
        finals.append(value)
    return np.array(finals)


def simulate_normal_loop(returns, n_scenarios, horizon=HORIZON, initial=INITIAL, seed=SEED):
    """Chaque scénario : 252 rendements tirés dans une loi normale, un par un."""
    random.seed(seed)
    mu, sigma = float(np.mean(returns)), float(np.std(returns, ddof=1))
    finals = []
    for _ in range(n_scenarios):
        value = initial
        for _ in range(horizon):
            value *= 1 + random.gauss(mu, sigma)
        finals.append(value)
    return np.array(finals)


# --------------------------------------------------------------------------
# 2. Versions VECTORISÉES (NumPy)
# --------------------------------------------------------------------------
def simulate_bootstrap_vec(returns, n_scenarios, horizon=HORIZON, initial=INITIAL, seed=SEED):
    """Tous les tirages d'un bloc : tableau (scénarios x jours), puis produit sur les jours."""
    rng = np.random.default_rng(seed)
    r = np.asarray(returns)
    finals = []
    for start in range(0, n_scenarios, CHUNK):           # par blocs pour ne pas saturer la mémoire
        size = min(CHUNK, n_scenarios - start)
        idx = rng.integers(0, len(r), size=(size, horizon))   # indices de jours tirés au hasard
        draws = r[idx]                                        # rendements correspondants
        finals.append(initial * np.prod(1 + draws, axis=1))   # valeur finale de chaque scénario
    return np.concatenate(finals)


def simulate_normal_vec(returns, n_scenarios, horizon=HORIZON, initial=INITIAL, seed=SEED):
    """Tous les rendements tirés d'un bloc dans une loi normale."""
    rng = np.random.default_rng(seed)
    r = np.asarray(returns)
    mu, sigma = r.mean(), r.std(ddof=1)
    finals = []
    for start in range(0, n_scenarios, CHUNK):
        size = min(CHUNK, n_scenarios - start)
        draws = rng.normal(mu, sigma, size=(size, horizon))
        finals.append(initial * np.prod(1 + draws, axis=1))
    return np.concatenate(finals)


# --------------------------------------------------------------------------
# 3. Indicateurs de risque
# --------------------------------------------------------------------------
def risk_metrics(final_values, initial=INITIAL, level=LEVEL) -> dict:
    """
    Perte = valeur de départ - valeur finale (positive quand on perd).
    VaR : perte dépassée dans seulement (1 - level) = 0,5 % des scénarios.
    Expected Shortfall : perte moyenne dans ces pires scénarios.
    """
    losses = initial - np.asarray(final_values)
    var = np.quantile(losses, level)
    es = losses[losses >= var].mean()
    return {
        "VaR 99,5 % (€)": var,
        "VaR 99,5 % (%)": var / initial,
        "Expected Shortfall (€)": es,
        "Expected Shortfall (%)": es / initial,
        "Valeur finale moyenne (€)": float(np.mean(final_values)),
    }


def timed(func, *args, **kwargs):
    """Exécute func et renvoie (résultat, durée en secondes)."""
    t0 = time.perf_counter()
    out = func(*args, **kwargs)
    return out, time.perf_counter() - t0


def compare_loop_vs_vec(returns, n_compare=20_000) -> pd.DataFrame:
    """
    Compare boucles et NumPy sur le MÊME nombre de scénarios : résultats et durées.
    Les deux versions n'utilisent pas le même générateur aléatoire : les VaR sont proches,
    pas identiques (écart d'échantillonnage).
    """
    rows = []
    for name, f_loop, f_vec in [("bootstrap", simulate_bootstrap_loop, simulate_bootstrap_vec),
                                ("normale", simulate_normal_loop, simulate_normal_vec)]:
        v_loop, t_loop = timed(f_loop, returns, n_compare)
        v_vec, t_vec = timed(f_vec, returns, n_compare)
        rows.append({
            "Méthode": name, "Scénarios": n_compare,
            "VaR boucles (%)": risk_metrics(v_loop)["VaR 99,5 % (%)"],
            "VaR NumPy (%)": risk_metrics(v_vec)["VaR 99,5 % (%)"],
            "Durée boucles (s)": t_loop, "Durée NumPy (s)": t_vec,
            "Rapport de vitesse": t_loop / t_vec,
        })
    return pd.DataFrame(rows).set_index("Méthode")


def run_all(returns_by_portfolio: dict, n_scenarios=N_SCENARIOS) -> pd.DataFrame:
    """VaR et ES, pour chaque portefeuille et chaque méthode (versions NumPy)."""
    rows = {}
    for pname, rets in returns_by_portfolio.items():
        for mname, func in [("bootstrap", simulate_bootstrap_vec), ("normale", simulate_normal_vec)]:
            rows[(pname, mname)] = risk_metrics(func(rets, n_scenarios))
    return pd.DataFrame(rows).T


# --------------------------------------------------------------------------
# Test rapide
# --------------------------------------------------------------------------
if __name__ == "__main__":
    rend = compute_returns(load_prices())
    portfolios = {
        "Poids égaux": portfolio_returns(rend, WEIGHTS_EQUAL),
        "Répartition alternative": portfolio_returns(rend, WEIGHTS_ALT),
    }

    print(f"=== Boucles vs NumPy (portefeuille à poids égaux) ===")
    print(compare_loop_vs_vec(portfolios["Poids égaux"]).round(4).to_string(), "\n")

    print(f"=== VaR et ES sur {N_SCENARIOS:,} scénarios, horizon {HORIZON} jours ===".replace(",", " "))
    print(run_all(portfolios).round(4).to_string())
