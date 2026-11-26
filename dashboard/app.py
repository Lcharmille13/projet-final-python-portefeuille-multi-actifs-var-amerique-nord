"""
app.py : tableau de bord interactif du portefeuille multi-actifs (Amérique du Nord).

Lancement, depuis la racine du projet :
    streamlit run dashboard/app.py

Le tableau de bord lit uniquement les CSV de data/ : aucune connexion Internet n'est nécessaire.
Les calculs réutilisent les fonctions de src/analysis.py et src/risk.py.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Streamlit lance ce fichier depuis dashboard/ : on ajoute la racine du projet pour importer src
RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from src.analysis import (load_prices, compute_returns, rolling_volatility, drawdown,
                          portfolio_returns, stats_table, WEIGHTS_EQUAL, WEIGHTS_ALT)
from src.risk import simulate_bootstrap_vec, simulate_normal_vec, risk_metrics, HORIZON, INITIAL

# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Portefeuille Amérique du Nord", page_icon="📈", layout="wide")


def euros(x):
    """Formate un montant : 123456.7 -> '123 457 €'."""
    return f"{x:,.0f} €".replace(",", " ")


# ---------------------------------------------------------------------------
# Données (mises en cache : lues une seule fois)
# ---------------------------------------------------------------------------
@st.cache_data
def charger_prix():
    return load_prices()


@st.cache_data
def simuler(rend_portefeuille, methode, n_scenarios):
    """Simulation NumPy (bootstrap ou loi normale), mise en cache pour ne pas tout recalculer."""
    fonction = simulate_bootstrap_vec if methode == "Bootstrap historique" else simulate_normal_vec
    return fonction(rend_portefeuille, n_scenarios)


prix_complets = charger_prix()
ACTIFS = list(prix_complets.columns)

# ---------------------------------------------------------------------------
# Barre latérale : les choix de l'utilisateur
# ---------------------------------------------------------------------------
st.sidebar.header("Paramètres")

choix_repartition = st.sidebar.selectbox(
    "Répartition du portefeuille",
    ["Poids égaux", "Répartition alternative", "Personnalisée"],
)

if choix_repartition == "Poids égaux":
    poids = dict(WEIGHTS_EQUAL)
elif choix_repartition == "Répartition alternative":
    poids = dict(WEIGHTS_ALT)
else:
    actifs_choisis = st.sidebar.multiselect("Actifs du portefeuille", ACTIFS, default=ACTIFS)
    if not actifs_choisis:
        st.sidebar.error("Choisis au moins un actif.")
        st.stop()
    st.sidebar.caption("Poids bruts : ils sont ramenés automatiquement à 100 %.")
    poids_bruts = {a: st.sidebar.slider(f"Poids {a} (%)", 0, 100, 20, step=5) for a in actifs_choisis}
    total = sum(poids_bruts.values())
    if total == 0:
        st.sidebar.error("La somme des poids est nulle.")
        st.stop()
    # Actifs non choisis : poids 0 ; poids choisis : normalisés pour sommer à 1
    poids = {a: poids_bruts.get(a, 0) / total for a in ACTIFS}

date_min, date_max = prix_complets.index.min().date(), prix_complets.index.max().date()
debut, fin = st.sidebar.slider(
    "Période d'analyse", min_value=date_min, max_value=date_max,
    value=(date_min, date_max), format="DD/MM/YYYY",
)

capital = st.sidebar.number_input("Capital initial (€)", min_value=1_000, value=100_000, step=10_000)

st.sidebar.divider()
methode = st.sidebar.selectbox("Méthode de simulation", ["Bootstrap historique", "Loi normale"])
n_scenarios = st.sidebar.select_slider("Nombre de scénarios", [10_000, 50_000, 100_000], value=100_000)

# ---------------------------------------------------------------------------
# Calculs sur la période choisie
# ---------------------------------------------------------------------------
prix = prix_complets.loc[str(debut):str(fin)]
if len(prix) < 70:
    st.error("Période trop courte : choisis au moins 70 séances (volatilité glissante sur 60 jours).")
    st.stop()

rendements = compute_returns(prix)
rend_port = portfolio_returns(rendements, poids)
rend_ref = {  # les deux répartitions de référence, pour la comparaison
    "Poids égaux": portfolio_returns(rendements, WEIGHTS_EQUAL),
    "Répartition alternative": portfolio_returns(rendements, WEIGHTS_ALT),
}


def valeur_en_euros(rend):
    """Valeur du portefeuille dans le temps, en partant du capital le premier jour."""
    valeur = capital * (1 + rend).cumprod()
    return pd.concat([pd.Series(capital, index=[prix.index[0]]), valeur])


valeur = valeur_en_euros(rend_port)
stats_port = stats_table(rend_port.to_frame("Portefeuille")).iloc[0]

# ---------------------------------------------------------------------------
# En-tête et indicateurs clés
# ---------------------------------------------------------------------------
st.title("📈 Portefeuille multi-actifs — Amérique du Nord")
st.caption(f"Valeurs en euros · Répartition : **{choix_repartition}** · "
           f"Période : {debut:%d/%m/%Y} → {fin:%d/%m/%Y} ({len(prix)} séances)")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Valeur finale", euros(valeur.iloc[-1]), f"{valeur.iloc[-1] / capital - 1:+.1%}")
col2.metric("Rendement annualisé", f"{stats_port['Rendement annualisé']:.2%}")
col3.metric("Volatilité annualisée", f"{stats_port['Volatilité annualisée']:.2%}")
col4.metric("Perte maximale", f"{stats_port['Perte maximale']:.2%}")

st.dataframe(pd.DataFrame({"Poids": poids}).T.style.format("{:.0%}"), width="stretch")

onglets = st.tabs(["Évolution", "Risque historique", "Corrélations", "Comparaison", "Simulation et VaR"])

# ---------------------------------------------------------------------------
# Onglet 1 : évolution
# ---------------------------------------------------------------------------
with onglets[0]:
    fig = px.line(valeur, labels={"index": "Date", "value": "Valeur (€)"},
                  title=f"Valeur du portefeuille (capital initial : {euros(capital)})")
    fig.update_layout(showlegend=False, yaxis_tickformat=",.0f")
    st.plotly_chart(fig, width="stretch")

    actifs_affiches = st.multiselect("ETF à afficher (base 100)", ACTIFS, default=ACTIFS)
    if actifs_affiches:
        base100 = prix[actifs_affiches] / prix[actifs_affiches].iloc[0] * 100
        fig = px.line(base100, labels={"value": "Base 100", "variable": "ETF"},
                      title="Évolution des ETF en euros (base 100 au début de la période)")
        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Onglet 2 : rendements et risque historique
# ---------------------------------------------------------------------------
with onglets[1]:
    stats_actifs = stats_table(rendements)
    stats_actifs.loc["Portefeuille"] = stats_port
    st.subheader("Statistiques sur la période")
    st.dataframe(stats_actifs.style.format("{:.2%}"), width="stretch")

    col_a, col_b = st.columns(2)
    with col_a:
        vol = rolling_volatility(rend_port.to_frame("Portefeuille"), window=60) * 100
        fig = px.line(vol, labels={"value": "%", "index": "Date"},
                      title="Volatilité annualisée glissante sur 60 jours (%)")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")
    with col_b:
        dd = drawdown(valeur) * 100
        fig = px.area(dd, labels={"value": "%", "index": "Date"},
                      title="Drawdown : perte depuis le plus haut (%)")
        fig.update_traces(line_color="crimson")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")

    fig = px.histogram(rend_port * 100, nbins=100, labels={"value": "Rendement quotidien (%)"},
                       title="Distribution des rendements quotidiens du portefeuille (%)")
    fig.update_layout(showlegend=False, yaxis_title="Nombre de jours")
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Onglet 3 : corrélations
# ---------------------------------------------------------------------------
with onglets[2]:
    fig = px.imshow(rendements.corr(), text_auto=".2f", zmin=-1, zmax=1,
                    color_continuous_scale="RdBu_r",
                    title="Corrélations des rendements quotidiens")
    st.plotly_chart(fig, width="stretch")
    st.caption("+1 : les ETF bougent toujours ensemble · 0 : aucun lien · −1 : sens inverse.")

# ---------------------------------------------------------------------------
# Onglet 4 : comparaison des portefeuilles
# ---------------------------------------------------------------------------
with onglets[3]:
    comparaison = dict(rend_ref)
    if choix_repartition == "Personnalisée":
        comparaison["Personnalisée"] = rend_port

    valeurs = pd.DataFrame({nom: valeur_en_euros(r) for nom, r in comparaison.items()})
    fig = px.line(valeurs, labels={"value": "Valeur (€)", "variable": "Portefeuille", "index": "Date"},
                  title="Valeur des portefeuilles en euros")
    fig.update_layout(yaxis_tickformat=",.0f")
    st.plotly_chart(fig, width="stretch")

    tableau = stats_table(pd.DataFrame(comparaison))
    tableau.insert(0, "Valeur finale (€)", valeurs.iloc[-1])
    st.dataframe(tableau.style.format({"Valeur finale (€)": euros, "Rendement annualisé": "{:.2%}",
                                       "Volatilité annualisée": "{:.2%}", "Perte maximale": "{:.2%}"}),
                 width="stretch")

# ---------------------------------------------------------------------------
# Onglet 5 : simulation à un an, VaR et Expected Shortfall
# ---------------------------------------------------------------------------
with onglets[4]:
    st.markdown(f"**{n_scenarios:,} scénarios** de {HORIZON} jours ({methode.lower()}), à partir des "
                f"rendements du portefeuille sur la période choisie.".replace(",", " "))

    finales = simuler(rend_port, methode, n_scenarios) * capital / INITIAL
    m = risk_metrics(finales, initial=capital)
    seuil_var = capital - m["VaR 99,5 % (€)"]
    moyenne_pires = capital - m["Expected Shortfall (€)"]

    c1, c2, c3 = st.columns(3)
    c1.metric("VaR 99,5 % à 1 an", euros(m["VaR 99,5 % (€)"]), f"{-m['VaR 99,5 % (%)']:.1%}",
              delta_color="off")
    c2.metric("Expected Shortfall 99,5 %", euros(m["Expected Shortfall (€)"]),
              f"{-m['Expected Shortfall (%)']:.1%}", delta_color="off")
    c3.metric("Valeur finale moyenne", euros(m["Valeur finale moyenne (€)"]))

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=finales, nbinsx=200, name="Scénarios", marker_color="steelblue"))
    fig.add_trace(go.Histogram(x=finales[finales <= seuil_var], nbinsx=30,
                               name="0,5 % pires scénarios", marker_color="crimson"))
    fig.add_vline(x=capital, line_dash="dash", line_color="black",
                  annotation_text="Capital initial")
    fig.add_vline(x=seuil_var, line_color="crimson", line_width=3,
                  annotation_text=f"VaR : {euros(seuil_var)}", annotation_position="top left")
    fig.add_vline(x=moyenne_pires, line_dash="dot", line_color="darkred", line_width=3,
                  annotation_text=f"ES : {euros(moyenne_pires)}", annotation_position="bottom left")
    fig.update_layout(barmode="overlay", title="Distribution simulée de la valeur dans un an",
                      xaxis_title="Valeur du portefeuille dans 1 an (€)",
                      yaxis_title="Nombre de scénarios", xaxis_tickformat=",.0f")
    st.plotly_chart(fig, width="stretch")

    st.info(f"Il y a une chance sur 200 de perdre plus de **{euros(m['VaR 99,5 % (€)'])}** en un an. "
            f"Dans ces cas-là, la perte moyenne est de **{euros(m['Expected Shortfall (€)'])}**. "
            "Ces chiffres dépendent des hypothèses du modèle et ne garantissent pas les pertes futures.")