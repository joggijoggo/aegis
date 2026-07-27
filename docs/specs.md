# Rapport d’Architecture et Spécifications Techniques Fondatrices
**Framework Quantitatif Institutionnel Multi-Tenant, Multi-Stratégie avec Optimisation Rolling Walk-Forward & Analyse Post-Mortem Expliquable (Forex / Conditions IG Group)**

---

## 1. Résumé Exécutif de l’Architecture (High-Level Summary)

Ce document formalise les spécifications techniques fondamentales d'un framework de recherche et d'exécution quantitative de niveau institutionnel. Conçu spécifiquement pour le marché des changes (Forex), le système repose sur un paradigme **Multi-Tenant / Comptes Isolés à Capital Initial Plein**.

L'architecture permet la coexistence et l'exécution parallèle de plusieurs bots autonomes et de plusieurs sous-stratégies (ex: *Mean Reversion*, *Trend Following*) sur un flux temporel synchronisé, sans aucun biais de netting ou de regard vers le futur (*look-ahead bias*). Le framework intègre la réplication exacte des conditions de trading du courtier **IG Group** (spreads variables, pénalités de volatilité, roll-over nocturne Tom-Next) et structure l'évaluation scientifique via une optimisation **Rolling Walk-Forward (WFO)**. Enfin, la couche de présentation **Streamlit** offre une transparence totale d'audit grâce à un moteur d'explicabilité technique des transactions (*Trade Inspector*).

L’intégralité de la base de code, des structures de données, des commentaires et de l’interface utilisateur est implémentée en **anglais**, tandis que la gouvernance théorique est spécifiée ici en **français**.

```text
                                  [ MASTER CLOCK ENGINE ]
                                             │
               ┌─────────────────────────────┴─────────────────────────────┐
        (Timeline Sync)                                             (Dynamic Frictions)
               ▼                                                           ▼
      [ TIME-FRAME AGGREGATOR ]                                   [ IG GROUP SIMULATOR ]
      • Step delta baseline (15m)                                 • Volatility-Adjusted Spread
      • Look-Ahead Shield (MTF Closes)                            • Tom-Next Interest Swap
      • Forward-Fill Gap Handling                                 • 3-Day Wednesday Multiplier
               │                                                           │
               ├───────────────────────────────────────────────────────────┘
               ▼
      ┌───────────────────────────────────────────────────────────┐
      │               MULTI-TENANT BOT PIPELINE                   │
      ├───────────────────────────────────────────────────────────┤
      │  [ BOT_A (Config Hash A) ]    │  [ BOT_B (Config Hash B) ]│ ◄─── Caching Checkpoints
      │   ├── Account EURUSD (\$10k)    │   ├── Account EURUSD (\$10k)│      (SHA-256 Iso-Validation)
      │   └── Account GBPUSD (\$10k)    │   └── Account USDJPY (\$10k)│
      └───────────────────────────────────────────────────────────┘
               │
               ▼  (Execution Signals via Broker Abstract Port)
      ┌───────────────────────────────────────────────────────────┐
      │                 UNIFIED BROKER BRIDGE                     │
      ├───────────────────────────────────────────────────────────┤
      │   [ ADAPTER: BACKTRADER ]     │     [ ADAPTER: IG API ]   │
      │   • Backtest Loop (.next())   │     • Streaming Live      │
      │   • Virtual Bracket OCO       │     • REST Demo/Live      │
      └───────────────────────────────────────────────────────────┘
               │
               ▼  (Diagnostic Snapshots & Flattened Telemetry)
      ┌───────────────────────────────────────────────────────────┐
      │             POST-MORTEM STREAMLIT DASHBOARD               │
      ├───────────────────────────────────────────────────────────┤
      │ • Cross-Bot Benchmarking (Normalized Base 100 Overlay)    │
      │ • Time-Decomposition Analytics & Parameter Drift Charts   │
      │ • Explainable Trade Inspector (Microscope Price Charts)   │
      └───────────────────────────────────────────────────────────┘
```

## 2. Les Principes Directeurs d’Ingénierie Quantitative

1. **Isolation Multi-Tenant à Capital Initial Plein :** Les instances de bots opérant sur le framework sont configurées comme des entités étanches (`Tenants`). Si un budget de départ de \$10 000 est alloué, chaque paire Forex affectée à ce bot bénéficie de son propre sous-compte de \$10 000. Le profit et perte (*PnL*) et la marge d'une paire n'altèrent jamais la capacité d'action des autres, permettant une évaluation à armes égales des actifs.
2. **Coexistence Parallèle des Stratégies (No Netting) :** Le moteur n'applique aucune règle de compensation de position au niveau de sa comptabilité interne. Si la stratégie A émet un signal de vente (*Short*) et la stratégie B émet simultanément un signal d'achat (*Long*) sur la même paire pour le même bot, le système maintient deux lignes de position distinctes avec leurs ordres de protection respectifs. Le framework comptabilise le **double coût réel** (spreads et frais d'exposition), forçant la stratégie à prouver sa viabilité face aux frictions bancaires cumulées.
3. **Labellisation Probabiliste des Régimes de Marché :** La détection d'environnement abandonne le partitionnement strict au profit d'un vecteur probabiliste normalisé basé sur des critères mathématiques purs (Coefficient de Hurst, Ratio de Kaufman). Chaque transaction se voit attribuer un instantané de ce vecteur à l'entrée (`regime_profile`), mesurant précisément la tolérance et la dégradation de la performance (*Strategy Decay*) hors de sa zone de confort.
4. **Indépendance vis-à-vis du Courtier (Architecture Hexagonale) :** Pour éliminer le besoin de réécriture lors du passage en production, les stratégies interagissent exclusivement avec un pont d'abstraction (`Abstract Broker Bridge`). L'aiguillage entre l'émulateur historique de backtest (Backtrader) et la connexion en temps réel (API REST/WebSocket d'IG) s'effectue par injection de dépendance au démarrage.

## 3. Spécifications Techniques des Composants Principaux

### 3.1 L'Horloge Maîtresse et Synchronisateur MTF (`core/engine.py`)
* **Agnosticisme Temporel UTC :** Le moteur interne incrémente le temps de manière linéaire selon un repère absolu en UTC (ex: pas de 15 minutes). Les séries temporelles en entrée sont purgées de tout fuseau local pour neutraliser définitivement les désynchronisations d'heures d'été internationales (*Daylight Saving Time*).
* **Bouclier Anti-Triche Multi-Timeframe :** L'agrégation des données macro (ex: 4-Heures, Daily) s'effectue en temps réel dans le moteur. Les indicateurs basés sur ces unités supérieures restent strictement verrouillés et indisponibles pour le bot tant que la dernière bougie micro de cet intervalle n'a pas intégralement clôturé.
* **Gestion des Trous de Cotation (Forward-Fill Master) :** Pour préserver la synchronisation multi-actifs, le moteur boucle sur un générateur de temps linéaire et non sur les lignes des fichiers de données. Si une paire Forex illiquide ne présente aucune transaction sur un pas de temps donné, le moteur duplique la dernière clôture connue (*Forward-Fill*) pour assurer la continuité des calculs d'indicateurs de l'ensemble du portefeuille.

### 3.2 L'Émulateur d'Exécution et Frictions IG Group (`core/accounts.py` & `core/orders.py`)
* **Spreads Variables et Volatilité :** Le spread d'exécution intègre une composante dynamique corrélée à l'écart-type récent du prix (`ATR`). De plus, le moteur applique une pénalité multiplicative automatique de 4× sur le spread de base si le pas de temps se situe dans la fenêtre de clôture journalière interbancaire d'IG (entre 21h45 et 23h15 UTC).
* **Financement Nocturne Tom-Next Forex :** Toute position active lors du franchissement de 22h00 UTC (coupure de Londres) subit l'application de frais de financement calculés sur la valeur notionnelle de l'exposition, indexée sur le différentiel de taux des devises sous-jacentes majoré de la commission administrative d'IG (1.5%). Le moteur applique une pondération triple de ces frais lors du traitement du mercredi soir pour répliquer le cycle de règlement à J+2 des banques le week-end.
* **Règle d'Exécution Pessimiste :** Pour éliminer le biais d'exécution intra-bougie, le gestionnaire d'ordres conditionnels `BracketOrderExecutionManager` applique une règle d'arbitrage stricte : si l'amplitude (`High`/`Low`) d'une seule bougie de 15 minutes franchit simultanément le niveau de *Take-Profit* et de *Stop-Loss*, le moteur considère automatiquement que le **Stop-Loss a été touché en premier**, comptabilisant la position comme perdante.
* **Vérification Réelle de Liquidité :** Les ordres à cours limité (*Limit Orders*) ne sont pas exécutés sur simple contact de prix. Un ordre d'achat limite à un niveau donné requiert que le prix *Ask* du marché descende strictement en dessous de ce niveau pour valider l'absorption de la liquidité par l'émulateur.

### 3.3 Le Framework de Validation Walk-Forward Glissant (`core/optimization.py`)
* **Segmentation Temporelle Rolling :** Les données historiques sont découpées en fenêtres glissantes composées d'une phase d'entraînement *In-Sample* (IS - ex: 6 mois) et d'une phase de test *Out-of-Sample* (OOS - ex: 1 mois). La fenêtre se décale d'un pas fixe équivalent à la durée de l'OOS pour le bloc suivant.
* **Mutation à la Volée (Hot-Swapping) :** Au franchissement de la frontière temporelle de test, la stratégie reçoit sa nouvelle matrice de paramètres optimaux. Les transactions déjà ouvertes conservent leurs paramètres d'origine (*Legacy Protection*) et s'exécutent de manière exacte, tandis que toutes les nouvelles détections de signaux exploitent immédiatement la nouvelle configuration.

### 3.4 Le Moteur de Persistance et Checkpointing Sélectif (`core/cache.py`)
* **Granularité par Instance Complète :** Pour optimiser le temps de calcul lors du développement, le framework met en place un cache persistant. L'unité minimale du cache est définie par le couple unique **[Bot ID + Actif Tradé]**.
* **Génération d'Empreinte SHA-256 :** Le système génère une signature numérique unique basée sur la configuration globale des stratégies du bot, ses hyperparamètres, son calendrier WFO et l'empreinte physique du fichier de données source. Si vous modifiez un paramètre sur le Bot A, seul son cache expire ; le moteur recharge instantanément les données pré-calculées du Bot B depuis le disque dur au format binaire optimisé.

## 4. Architecture de Présentation Post-Mortem (Streamlit Blueprint)

L'interface utilisateur Streamlit est développée de manière à interdire les rafraîchissements inutiles (`st.session_state` persistant), à décimer les séries temporelles trop lourdes pour garantir des graphiques fluides, et à différer la préparation des fichiers d'exportation pour préserver la mémoire vive du serveur. Elle s'organise selon une arborescence graphique à 5 écrans.

### Écran 1 : Portfolio Macro Performance (Performance Globale des Actifs)
* **KPI Cards (Double Grille) :** Affichage horizontal des 6 métriques clés :
  * *Ligne 1 (Exécution) :* Total Return (%) | Win Rate (%) | Profit Factor
  * *Ligne 2 (Risque) :* Max Drawdown (%) | Sharpe Ratio | Sortino Ratio *(calculé exclusivement sur la déviation baissière)*.
* **Overlay Equity Chart (Base 100) :** Graphique interactif superposant les courbes d'équité de chaque paire Forex du bot, normalisées à un indice initial de 100.00 pour comparer la régularité sans distorsion d'échelle.
* **Section : Time-Decomposition Analytics (Analyse Temporelle)**
  * *Monthly Returns Heatmap :* Grille matricielle (Années vs Mois) colorée selon le PnL net pour identifier visuellement les phases de fatigue d'un bot.
  * *Rolling KPI Trajectories :* Graphiques temporels traçant l'évolution du Win Rate, du Sharpe et du ratio de Sortino sur une fenêtre glissante de 30 trades pour détecter la dégradation structurelle de l'algorithme face aux changements macroéconomiques.

### Écran 2 : Cross-Bot Benchmarking (Comparateur Inter-Bots)
* **Normalized Equity Comparison :** Permet la sélection multiple de plusieurs bots pour superposer leurs courbes de performance globale privée à armes égales (départ base 100).
* **The Leaderboard Grid :** Tableau d'honneur triable classant les bots selon leurs ratios de Sharpe, Sortino et performance nette.
* **Risk-Return Scatter Plot :** Graphique à deux dimensions positionnant chaque bot (Axe X : Max Drawdown, Axe Y : Total Return) pour identifier visuellement la frontière d'efficience et les profils de risque disproportionnés.
* **Bot Correlation Matrix :** Carte thermique (*Heatmap*) affichant les coefficients de corrélation des rendements quotidiens entre les bots pour valider la diversification réelle des modèles développés.

### Écran 3 : Bot Strategy Attribution (Analyse Interne des Stratégies)
* **The Strategy Leaderboard :** Grille isolant les 6 KPI réglementaires pour chaque sous-stratégie active au sein du bot sélectionné (ex: mesurer la rentabilité propre de la *Mean Reversion* face au *Trend Following*).
* **Cumulative PnL Attribution Chart :** Graphique à zones empilées affichant la contribution nette en dollars de chaque logique mathématique dans le temps.
* **Risk Exposure Share :** Graphique sectoriel mesurant le taux d'occupation et l'allocation marginale du capital immobilisé par chaque algorithme.

### Écran 4 : WFO Analytics & Robustness (Audit de l'Optimisation)
* **WFE Breakdown :** Barres de couleur matérialisant le score d'Efficacité Walk-Forward pour chaque bloc glissant. Alerte visuellement sur le surapprentissage (Couleur Rouge si le ratio OOS / IS s'effondre en dessous de 50%).
* **Parameter Drift Chart :** Suivi chronologique de la valeur des paramètres optimaux d'une fenêtre à l'autre pour valider leur stabilité statistique.

### Écran 5 : Explainable Trade Inspector (Le Microscope Technique)
* **Interactive Filterable Trade Log :** Registre complet de toutes les transactions fermées, triable par PnL ou par étiquette de régime de marché. Le clic sur une ligne charge l'audit.
* **The Microscope Chart (Plotly) :** Graphique de prix ultra-zoomé centré sur la durée de vie du trade (encadré de 20 bougies). Il affiche les prix réels d'exécutions d'IG (*Bid* et *Ask* distincts), les bandes de volatilité d'ATR et des flèches d'exécution précises. En dessous, l'oscillateur déclencheur (ex: RSI) est synchronisé temporellement pour valider graphiquement le signal.
* **The Reason Log (Boîte d'Audit Textuelle) :** Traduction littérale du contexte mathématique de l'ordre :
  * Le vecteur probabiliste complet du régime au moment exact de l'entrée (ex: `RANGE: 82%, TREND: 10%, BREAKOUT: 8%` avec un score de confiance de 0.82).
  * La valeur exacte des indicateurs au clic du signal.
  * Le décompte précis des frictions IG appliquées (coût du spread dynamique à l'entrée et cumul des swaps Tom-Next encourus).

## 5. Spécifications de l'Architecture Hexagonale (Abstraction Layer Code Blueprint)

Pour garantir que votre bot de retour à la moyenne puisse s'exécuter de la même manière en simulation historique ou branché en direct sur l'API d'IG Market, la logique de trading ne doit contenir aucune commande liée à un outil spécifique. Elle interagit avec un port d'interface unifié (`AbstractBrokerBridge`).

Voici l'architecture logicielle complète formalisée en **anglais** pour l'interfaçage dual Backtest / Live.

```python
"""
Hexagonal Architecture Layer for Broker Independence.
Defines the unified Port (AbstractBrokerBridge) and the structural blueprints
for the Backtrader Adapter and the live IG Group API Wrapper.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass(frozen=True)
class OrderIntentPayload:
    """ Agnostic representation of a trading decision generated by a strategy. """
    bot_id: str
    asset_pair: str
    strategy_name: str
    direction: str  # "BUY" or "SELL"
    order_type: str # "MARKET", "LIMIT", "STOP"
    quantity_lots: float
    target_price: Optional[float] = None
    stop_loss_pips: Optional[float] = None
    take_profit_pips: Optional[float] = None

class AbstractBrokerBridge(ABC):
    """
    The Unified Port Interface. Every strategy inside the framework interacts
    exclusively with this boundary layer, ensuring zero coupling to external APIs.
    """
    @abstractmethod
    def submit_order_intent(self, payload: OrderIntentPayload) -> str:
        """ Submits an order intent and returns a standardized tracking order_id string. """
        pass

    @abstractmethod
    def cancel_active_order(self, order_id: str) -> bool:
        """ Request the immediate cancellation of a pending conditional order. """
        pass

    @abstractmethod
    def get_account_state(self, asset_pair: str) -> Dict[str, float]:
        """ Returns unified ledger parameters: {'balance': float, 'equity': float, 'margin': float} """
        pass


class BacktraderBrokerAdapter(AbstractBrokerBridge):
    """
    The Backtest Adapter. Translates agnostic OrderIntentPayload structures
    into native Backtrader platform commands (e.g., self.buy, self.sell).
    """
    def __init__(self, backtrader_strategy_instance: Any):
        self.bt_strat = backtrader_strategy_instance

    def submit_order_intent(self, payload: OrderIntentPayload) -> str:
        exec_type = self._map_order_type(payload.order_type)
        side_func = self.bt_strat.buy if payload.direction == "BUY" else self.bt_strat.sell

        native_order = side_func(
            size=payload.quantity_lots,
            price=payload.target_price,
            exectype=exec_type,
            valid=None
        )
        return str(native_order.ref)

    def cancel_active_order(self, order_id: str) -> bool:
        for order in self.bt_strat.broker.get_orderspending():
            if str(order.ref) == order_id:
                self.bt_strat.cancel(order)
                return True
        return False

    def get_account_state(self, asset_pair: str) -> Dict[str, float]:
        return {
            "balance": self.bt_strat.broker.get_cash(),
            "equity": self.bt_strat.broker.get_value(),
            "margin": 0.0
        }

    def _map_order_type(self, generic_type: str) -> Any:
        import backtrader as bt
        mapping = {"MARKET": bt.Order.Market, "LIMIT": bt.Order.Limit, "STOP": bt.Order.Stop}
        return mapping.get(generic_type, bt.Order.Market)


class IGLiveBrokerAdapter(AbstractBrokerBridge):
    """
    The Live Real-Time Adapter. Translates agnostic OrderIntentPayload structures
    into secure HTTPS REST network request bodies targeting the official IG Demo/Live APIs.
    Enforces real-time synchronization via Lightstreamer WebSocket events.
    """
    def __init__(self, api_client_session: Any, websocket_stream: Any):
        self.session = api_client_session
        self.stream = websocket_stream

    def submit_order_intent(self, payload: OrderIntentPayload) -> str:
        ig_epic = self._map_pair_to_ig_epic(payload.asset_pair)

        request_body = {
            "epic": ig_epic,
            "expiry": "DFB",
            "direction": payload.direction,
            "size": payload.quantity_lots,
            "orderType": payload.order_type,
            "guaranteedStop": False,
            "stopDistance": payload.stop_loss_pips,
            "limitDistance": payload.take_profit_pips,
            "currencyCode": "USD"
        }

        response = self.session.post("/gateway/deal/positions/otc", json=request_body)

        if response.status_code == 200:
            return response.json().get("dealReference", "FAILED_REFERENCE")
        else:
            raise ConnectionError(f"IG Group API Order Rejection: {response.text}")

    def cancel_active_order(self, order_id: str) -> bool:
        response = self.session.delete(f"/gateway/deal/workingorders/otc/{order_id}")
        return response.status_code == 200

    def get_account_state(self, asset_pair: str) -> Dict[str, float]:
        response = self.session.get("/gateway/deal/accounts")
        data = response.json()
        return {
            "balance": data["balance"]["balance"],
            "equity": data["balance"]["balance"] + data["balance"]["pnl"],
            "margin": data["balance"]["funds"]
        }

    def _map_pair_to_ig_epic(self, pair: str) -> str:
        mapping = {"EURUSD": "CS.D.EURUSD.CFD.IP", "GBPUSD": "CS.D.GBPUSD.CFD.IP"}
        return mapping.get(pair, "")
```
