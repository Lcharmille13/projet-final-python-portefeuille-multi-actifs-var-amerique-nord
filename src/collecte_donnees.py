"""
collecte_donnees.py
-------------------
Télécharge depuis Yahoo Finance :
  - les prix de clôture ajustés quotidiens des 5 ETF du portefeuille (en dollars) ;
  - le taux de change EUR/USD (nombre de dollars pour 1 euro).

Puis enregistre :
  - data/raw/prix_etf_usd.csv        -> données brutes, telles que téléchargées
  - data/raw/taux_eurusd.csv         -> données brutes, telles que téléchargées
  - data/processed/prix_etf_eur.csv  -> prix convertis en euros, prêts pour l'analyse

À exécuter UNE SEULE FOIS, depuis la racine du projet (Internet nécessaire) :
    python src/collecte_donnees.py
Ensuite, le notebook et le dashboard lisent uniquement les CSV.
"""

from pathlib import Path

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# 1. Paramètres
# ---------------------------------------------------------------------------
# Racine du projet = dossier parent de "src", quel que soit l'endroit d'où on lance le script
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_RAW = RACINE / "data" / "raw"
DOSSIER_PROCESSED = RACINE / "data" / "processed"

TICKERS_ETF = ["SPY", "QQQ", "IWM", "EWC", "VNQ"]
TICKER_CHANGE = "EURUSD=X"  # cotation : combien de dollars pour 1 euro

DATE_DEBUT = "2015-01-01"
DATE_FIN = "2026-11-21"  # yfinance EXCLUT cette date -> dernière séance : vendredi 20/11/2026


# ---------------------------------------------------------------------------
# 2. Fonctions
# ---------------------------------------------------------------------------
def telecharger_cloture(tickers, debut, fin):
    """Télécharge les prix de clôture ajustés et renvoie un DataFrame (une colonne par ticker)."""
    liste_tickers = [tickers] if isinstance(tickers, str) else list(tickers)

    donnees = yf.download(
        liste_tickers,
        start=debut,
        end=fin,
        auto_adjust=True,  # "Close" tient compte des dividendes et des divisions d'actions
        progress=False,
    )
    if donnees is None or donnees.empty:
        raise RuntimeError(f"Aucune donnée reçue pour {liste_tickers}. Vérifie ta connexion Internet.")

    cloture = donnees["Close"]
    if isinstance(cloture, pd.Series):  # cas d'un seul ticker selon la version de yfinance
        cloture = cloture.to_frame(name=liste_tickers[0])

    # On refuse de continuer si un ticker est absent ou entièrement vide
    manquants = [t for t in liste_tickers if t not in cloture.columns or cloture[t].isna().all()]
    if manquants:
        raise RuntimeError(f"Tickers sans données : {manquants}")

    # Dates sans fuseau horaire, triées, sans doublon
    cloture.index = pd.to_datetime(cloture.index)
    if cloture.index.tz is not None:
        cloture.index = cloture.index.tz_localize(None)
    cloture = cloture.sort_index()
    cloture = cloture[~cloture.index.duplicated(keep="first")]
    cloture.index.name = "Date"

    return cloture[liste_tickers]


def convertir_en_euros(prix_usd, taux_eurusd):
    """
    Convertit des prix en dollars en euros.
    EUR/USD = dollars pour 1 euro  ->  prix en euros = prix en dollars / EUR/USD
    Le taux est aligné sur les jours de cotation des ETF. Si le taux manque un jour
    de bourse américaine, on reprend le dernier taux connu (ffill).
    """
    taux_sur_jours_etf = taux_eurusd.reindex(prix_usd.index)
    nb_manquants_avant = int(taux_sur_jours_etf.isna().sum())

    taux_aligne = taux_sur_jours_etf.ffill()
    nb_restants = int(taux_aligne.isna().sum())  # possible seulement tout au début

    prix_eur = prix_usd.div(taux_aligne, axis=0)

    # On supprime les éventuelles premières lignes sans taux : on n'invente aucune donnée
    prix_eur = prix_eur.dropna(how="all")

    print(f"Taux EUR/USD manquants sur des jours de bourse US : {nb_manquants_avant}")
    print(f"  -> complétés avec le dernier taux connu : {nb_manquants_avant - nb_restants}")
    print(f"  -> lignes supprimées faute de taux antérieur : {nb_restants}")
    return prix_eur, taux_aligne


# ---------------------------------------------------------------------------
# 3. Programme principal
# ---------------------------------------------------------------------------
def main():
    DOSSIER_RAW.mkdir(parents=True, exist_ok=True)
    DOSSIER_PROCESSED.mkdir(parents=True, exist_ok=True)

    print("Téléchargement des ETF...")
    prix_usd = telecharger_cloture(TICKERS_ETF, DATE_DEBUT, DATE_FIN)

    print("Téléchargement du taux EUR/USD...")
    taux = telecharger_cloture(TICKER_CHANGE, DATE_DEBUT, DATE_FIN)[TICKER_CHANGE]

    # Sauvegarde des données brutes, sans aucune modification
    prix_usd.to_csv(DOSSIER_RAW / "prix_etf_usd.csv")
    taux.to_frame().to_csv(DOSSIER_RAW / "taux_eurusd.csv")

    print("\nConversion en euros...")
    prix_eur, taux_aligne = convertir_en_euros(prix_usd, taux)
    prix_eur.to_csv(DOSSIER_PROCESSED / "prix_etf_eur.csv")

    # Contrôles affichés à l'écran
    print("\n===== CONTRÔLES =====")
    print(f"ETF      : {prix_usd.shape[0]} séances, du {prix_usd.index[0].date()} au {prix_usd.index[-1].date()}")
    print(f"EUR/USD  : {taux.shape[0]} jours, du {taux.index[0].date()} au {taux.index[-1].date()}")
    print("\nValeurs manquantes par ETF (en dollars) :")
    print(prix_usd.isna().sum().to_string())

    # Vérification manuelle de la conversion sur la dernière séance
    derniere_date = prix_eur.index[-1]
    print(f"\nExemple de conversion le {derniere_date.date()} :")
    print(f"  SPY = {prix_usd.loc[derniere_date, 'SPY']:.2f} $")
    print(f"  EUR/USD = {taux_aligne.loc[derniere_date]:.4f} $ pour 1 €")
    print(f"  SPY en euros = {prix_usd.loc[derniere_date, 'SPY']:.2f} / {taux_aligne.loc[derniere_date]:.4f}"
          f" = {prix_eur.loc[derniere_date, 'SPY']:.2f} €")

    print("\nFichiers enregistrés :")
    for fichier in [DOSSIER_RAW / "prix_etf_usd.csv", DOSSIER_RAW / "taux_eurusd.csv",
                    DOSSIER_PROCESSED / "prix_etf_eur.csv"]:
        print(f"  {fichier.relative_to(RACINE)}")


if __name__ == "__main__":
    main()