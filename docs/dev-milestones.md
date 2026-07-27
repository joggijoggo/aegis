# 🛡️ PLAN DE DÉVELOPPEMENT ITÉRATIF D'AEGIS (VERSION R&D PRIORITAIRE)

## 📌 Jalon 1 : Le Cœur de Simulation & Réalisme IG (Backbone)
**Objectif :** Bâtir le moteur d'exécution historique synchrone et la réplication ultra-réaliste des frictions de marché.

*   **Composants clés à développer :**
    *   `core/engine.py` : L'horloge maîtresse temporelle (Master Clock) qui itère linéairement en UTC absolu et intègre l'algorithme de *Forward-Fill* pour aligner les paires Forex asynchrones ou peu liquides.
    *   `core/engine.py (TimeframeAggregator)` : Le module d'agrégation multi-timeframe (MTF) qui verrouille les données macro (4H, Daily) jusqu'à leur clôture officielle pour interdire tout biais de regard vers le futur.
    *   `core/engine.py (IGGroupFrictionEngine)` : L'émulateur de spread dynamique (calculé via l'ATR) incluant la pénalité multiplicative de 4× lors de la coupure nocturne interbancaire d'IG (21h45 - 23h15 UTC).
*   **Critère de validation :** Faire tourner un jeu de données asymétrique (une paire majeure fluide et une paire exotique pleine de trous de cotation). Valider que l'horloge aligne les ticks de manière chronologique parfaite et applique les frais de financement *Tom-Next* exacts (avec le triple mercredi à 22h00 Londres).

---

## 📌 Jalon 2 : Le Framework Walk-Forward & Caching (R&D Pipeline)
**Objectif :** Automatiser le découpage scientifique des données historiques et optimiser les temps de calcul pour permettre le développement intensif multi-bots.

*   **Composants clés à développer :**
    *   `core/optimization.py` : Le générateur de fenêtres glissantes (*Rolling Walk-Forward*) qui segmente automatiquement l'historique en blocs d'entraînement (*In-Sample*) et de test (*Out-of-Sample*).
    *   `core/optimization.py (Hot-Swapping)` : Le mécanisme de mutation des paramètres à la volée lors des transitions de fenêtres, tout en appliquant la règle de *Legacy Management* (les trades en cours restent gérés par les anciens paramètres jusqu'à leur clôture).
    *   `core/cache.py` : Le module de persistance locale qui calcule une empreinte numérique unique SHA-256 par couple `[Bot + Actif]` et sérialise les résultats validés.
*   **Critère de validation :** Modifier les paramètres d'une seule stratégie du Bot A, lancer l'exécution globale et valider graphiquement (via des logs) que le framework recalcule uniquement le Bot A mais recharge instantanément le Bot B depuis le disque dur.

---

## 📌 Jalon 3 : Abstraction Hexagonale, Régimes & Stratégies (Intelligence)
**Objectif :** Poser les algorithmes de trading, le classificateur probabiliste et implémenter l'agnosticisme du courtier avec les verrous de sécurité pour le Live.

*   **Composants clés à développer :**
    *   `brokers/base_broker.py` : Le port d'interface agnostique (`AbstractBrokerBridge`) et l'adaptateur de simulation pour Backtrader.
    *   `brokers/base_broker.py (IGLiveBrokerAdapter Stub)` : Implémentation du code à trous pour l'API IG Live. **Chaque méthode doit obligatoirement lever une exception `NotImplementedError`** pour sécuriser la phase de R&D.
    *   `strategies/base_strategy.py` : La classe mère gérant le pré-chargement historique des indicateurs (*Warm-up period*) avant le début des phases de test.
    *   `strategies/mean_reversion.py` : Notre logique de retour à la moyenne avec ses ordres brackets OCO.
    *   `strategies/regime_manager.py` : Le classificateur basé sur les calculs mathématiques de Hurst et Kaufman, retournant le vecteur probabiliste normalisé et son score de confiance.
*   **Critère de validation :** Vérifier qu'à chaque trade initié, le framework associe un dictionnaire de télémétrie explicative (`TradeTelemetrySnapshot`) contenant les indicateurs et le profil de régime exacts à la milliseconde de l'entrée.

## 📌 Jalon 4 : L'Interface Post-Mortem Expliquable (Streamlit Analytics)
**Objectif :** Créer le tableau de bord d'audit visuel descendant à 5 écrans, optimisé pour la fluidité et la gestion de la mémoire vive.

*   **Composants clés à développer :**
    *   `dashboard/app.py` : Configuration de `st.session_state` pour mémoriser les sélections de l'utilisateur et bloquer les recalculs de scripts descendants de Streamlit.
    *   **Écrans 1, 2 & 3 :** Intégration de la double grille des 6 KPI (Sortino, Sharpe, Win Rate...), de la heatmap de décomposition temporelle (Mensuelle/Annuelle), des graphiques de corrélation inter-bots et de l'attribution des gains par stratégie.
    *   **Écran 4 & 5 :** Affichage des barres d'efficacité WFE et déploiement du *Trade Inspector* (Microscope Plotly affichant les spreads Bid/Ask réels appliqués par IG).
    *   **Moteurs d'optimisation UI :** Algorithme de décimation de données pour alléger les graphiques lourds et mise en place du téléchargement différé (*Lazy Export CSV*).
*   **Critère de validation :** Naviguer de manière instantanée entre les bots et les paires Forex sans aucun re-déclenchement des calculs de backtest, et inspecter visuellement la photo technique d'un trade au clic sur sa ligne de log.

---

## 📌 Jalon 5 : La Passerelle Production (Live IG Integration)
**Objectif :** Activer le trading en direct sur un compte de démonstration IG en remplaçant les codes à trous par la tuyauterie réseau réelle, une fois la R&D validée.

*   **Composants clés à développer :**
    *   `brokers/ig_live_bridge.py` : Remplacement des `NotImplementedError` par l'implémentation des requêtes chiffrées HTTPS REST (connexion aux endpoints `/gateway/deal/positions/otc`) et interfaçage avec le flux de streaming WebSocket Lightstreamer d'IG.
    *   Développement du gestionnaire d'événements asynchrones (`CONFIRMS`) pour mettre à jour les statuts des positions en direct et notifier les bots en cas d'exécution ou de rejet par le courtier.
*   **Critère de validation :** Passer la variable du fichier de configuration maître de `mode = "BACKTEST"` à `mode = "LIVE_DEMO"`. Observer le bot **Aegis** écouter le flux de prix en direct et router ses ordres brackets vers les serveurs de démo d'IG sans avoir modifié une seule ligne de code de vos stratégies.
