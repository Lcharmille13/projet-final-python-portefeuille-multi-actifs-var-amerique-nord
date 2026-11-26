# Déclaration d'utilisation de l'IA

Nous avons utilisé des assistants d'IA (Claude) pendant le projet. Nous avons relu, exécuté et vérifié
tout ce que nous rendons, et chaque membre du groupe peut en expliquer le code et les résultats.

## Partie de Ayao Edoh AWOUVI (collecte des données, notebook, tableau de bord)

### Pour quoi avons-nous utilisé l'IA ?

- Préparer l'environnement de travail (Python, VS Code, environnement virtuel, `requirements.txt`) et Git.
- Écrire une première version du script de collecte (`src/collecte_donnees.py`) et de la conversion en euros.
- Relire le code de calcul du groupe (`src/analysis.py`, `src/risk.py`) avant de l'utiliser dans le notebook.
- Proposer les cellules du notebook et la première version du tableau de bord Streamlit.
- Expliquer les notions (rendement annualisé, drawdown, VaR, Expected Shortfall, vectorisation)
  et proposer des textes d'interprétation, que nous avons vérifiés et corrigés avec nos propres résultats.

### Qu'est-ce qui était faux ou inadapté ? Comment l'avons-nous vu et corrigé ?

1. **Un graphique vide dans le tableau de bord.** Dans la première version proposée par l'IA,
   le graphique « base 100 » s'affichait sans aucune courbe (axes et légende visibles, lignes absentes).
   Le code tournait sans erreur : nous l'avons vu en regardant le dashboard dans le navigateur.
   Cause : avec plus de 1 000 points, Plotly Express dessine en WebGL, et le navigateur limite
   le nombre de graphiques WebGL actifs. Correction : `render_mode="svg"` dans les appels à `px.line`.

2. **Une interprétation imprécise.** Un premier texte d'interprétation proposé par l'IA avait été
   rédigé à partir de la lecture visuelle du graphique des drawdowns : il ne donnait pas la date
   du pire drawdown de QQQ. Nous l'avons vu en affichant le tableau des pires drawdowns et de leurs
   dates : celui de QQQ date du 28/12/2022, et non du krach de mars 2020 comme les autres ETF.
   Nous avons corrigé le texte avec les dates exactes.

3. **Un import impossible depuis le notebook.** Le code de `src/` indiquait de l'importer avec
   `from src.risk import *`, ce qui échoue depuis le dossier `notebooks/` (`No module named 'src'`).
   Nous l'avons vu en testant l'import. Correction : ajout de la racine du projet à `sys.path`
   dans la première cellule du notebook.

4. **Un nombre de scénarios insuffisant.** La comparaison boucles / NumPy utilisait par défaut
   20 000 scénarios, alors que le sujet en demande au moins 100 000. Nous l'avons vu en relisant
   le sujet. Correction : appel avec `n_compare=100_000` dans le notebook.

## Partie de [membre 2]

*À compléter.*

## Partie de [membre 3]

*À compléter.*
