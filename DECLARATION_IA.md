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

## Partie de Noémie Laure ANGUILLE CHARMILLE (analyse, simulation du risque, extension)

**Préparer le travail en groupe : création du dépôt GitHub, branches, git pull / push, Pull Requests, environnement virtuel et VS Code.

1. Écrire, avec Claude, les trois modules de calcul du groupe : src/analysis.py (rendements, volatilité glissante, drawdown, portefeuilles, statistiques), src/risk.py (simulation à un an en boucles et en NumPy, VaR à 99,5 % et Expected Shortfall) et src/optimisation.py (extension : optimisation de la répartition avec SciPy, avec séparation entraînement / test).

2. Intégrer l'extension dans le notebook (section 6) et nous aider à lire les résultats.
Expliquer les notions (VaR, Expected Shortfall, frontière efficiente, variance minimale, Sharpe).

**Qu'est-ce qui était faux ou inadapté ? Comment l'avons-nous vu et corrigé ?

   Une explication fausse des fichiers de données « modifiés ». Après avoir relancé le script de collecte, Git signalait des différences sur presque toutes les lignes des CSV. L'IA a d'abord avancé de nouvelles données Yahoo Finance, puis des fins de ligne Windows/Mac. En comparant les mêmes lignes dans les deux versions, nous avons vu que les prix étaient identiques, avec des écarts de l'ordre de 10⁻⁷ : des écarts d'arrondi informatique, et non des données différentes. Nous avons restauré les CSV du dépôt (git restore data/), qui restent notre référence.

   Un fichier qui « disparaît » en changeant de branche. L'IA nous a fait créer la branche feature/risk à partir de main alors que analysis.py, dont dépend risk.py, n'était encore que sur feature/analysis. Résultat : ModuleNotFoundError: No module named 'analysis'. Nous avons vu que le fichier existait toujours sur l'autre branche (git ls-tree) et l'avons récupéré avec git checkout feature/analysis -- src/analysis.py.

   Un jour de cotation perdu dans optimisation.py. La première version de la séparation entraînement / test ne mettait le 30/12/2022 dans aucune des deux périodes. Nous l'avons vu en lisant les dates affichées (entraînement jusqu'au 29/12/2022, test à partir du 03/01/2023). Correction : séparation par comparaison de dates (index < date et index >= date).

   Des poids arrondis qui ne somment plus à 1. Les poids optimisés, arrondis à 4 décimales, pouvaient sommer à 1,0001 et être refusés par la vérification de analysis.py. L'erreur est apparue en testant plusieurs dates de coupure. Correction : ajustement du plus gros poids après l'arrondi.

   Une répartition « alternative » sans justification. La répartition 40/10/10/20/20 était un exemple proposé par l'IA, que nous avons gardé sans raison précise au départ. En préparant la soutenance, nous avons vu que nous ne pouvions pas la justifier. Dans le notebook, nous indiquons que l'optimisation de variance minimale retrouve ensuite cette logique, sans prétendre qu'elle avait guidé le choix ce que nous avons vérifié

Nous avons exécuté les scripts et le notebook sur nos données réelles et lu les résultats (statistiques, corrélations, VaR, poids optimisés, performances sur la période de test). Nous avons relu le sujet pour vérifier que le notebook répond à chaque demande. Les limites de l'extension (optimisation sur le passé, dépendance à la date de coupure, plafond de 60 % par actif) sont écrites dans le notebook.


