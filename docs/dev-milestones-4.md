# 🛡️ PLAN DE DÉVELOPPEMENT DÉTAILLÉ : JALON 4


## 📌 Jalon 4.1 : L'Adaptateur Portuaire & Traduction de Prix (`BacktraderBrokerAdapter`)
**Objectif :** Traduire les intentions d'ordres universelles d'Aegis en requêtes d'ordres brackets OCO natives Backtrader basées sur des prix absolus corrigés.

*   **🛠️ Spécifications du Composant :**
    *   Hérite de `AbstractBrokerBridge`. Encapsule une référence interne vers l'instance de `bt.Strategy` active.
    *   Méthode `place_order()` : Intercepte les paramètres (Pips relatifs, `TransactionSide`, `OrderType`). Elle utilise le prix actuel corrigé pour calculer les barrières absolues de Stop-Loss et Take-Profit.
    *   Convertit l'ordre `MARKET` en ordre `LIMIT` réglé au prix exact `Bid` (si SHORT) ou `Ask` (si LONG) pour interdire à Backtrader d'exécuter au cours `Mid` brut.
    *   Méthode `get_portfolio_snapshot()` : Extrait le cash, l'equity et la valeur des positions directement depuis le broker de Backtrader (`self.strategy.broker`).
*   **🧪 Critère de Validation TDD (100% Coverage) :**
    *   Créer `tests/brokers/test_backtrader_adapter.py`.
    *   Mocker une instance de `bt.Strategy` et exécuter `place_order(TransactionSide.LONG)`.
    *   Vérifier mathématiquement que les prix transmis à `strategy.buy()` intègrent les pips absolus exacts calculés sur le cours `Ask` simulé.

---

## 📌 Jalon 4.2 : Le Pont Événementiel & Ingestion de Données (`BacktraderStrategyBridge`)
**Objectif :** Créer la classe maîtresse orchestrée par Cerebro chargée de convertir le flux historique brut en structures immuables Aegis et de piloter le Warm-up.

*   **🛠️ Spécifications du Composant :**
    *   Créer `strategies/backtrader_strategy_bridge.py`. Cette classe hérite nativement de `bt.Strategy`.
    *   Méthode `__init__()` : Reçoit et stocke l'instance de la stratégie Aegis cible (ex: `AegisMeanReversionBot`). Elle instancie également l'`IGFrictionEngine` du Jalon 1.
    *   Méthode `next()` : Appelée par Cerebro à chaque bougie. Elle extrait l'horodatage UTC et le prix `Mid` actuel. Elle utilise le moteur de friction pour générer l'objet immuable `MarketPricePoint` (`Bid`/`Ask` réels).
    *   Extraction dynamique : Elle récupère l'historique des clôtures via `self.data.close.get(size=N)` et transmet l'ensemble à la méthode `on_bar_close()` de votre robot Aegis, alimentant ainsi sa barrière de Warm-up par héritage.
*   **🧪 Critère de Validation TDD (100% Coverage) :**
    *   Créer `tests/strategies/test_backtrader_bridge.py`.
    *   Instancier un mini `bt.Cerebro()` avec un flux de données Pandas artificiel de 15 bougies.
    *   Vérifier que le robot Aegis passe son statut `is_warmed_up` à `True` dès que la longueur requise est atteinte dans la boucle `next()`.

---

## 📌 Jalon 4.3 : L'Intercepteur d'États Asynchrones (`notify_order`)
**Objectif :** Écouter les notifications d'ordres de Backtrader pour synchroniser la télémétrie d'Aegis en temps réel.

*   **🛠️ Spécifications du Composant :**
    *   Ajouter un hook d'écoute `on_order_status_change()` sur l'interface mère `AbstractStrategy` (Aegis).
    *   Dans `BacktraderStrategyBridge`, implémenter la méthode native `notify_order(self, order)`.
    *   Intercepter les statuts Backtrader (`Submitted` -> `Accepted` -> `Completed` / `Canceled` / `Margin`).
    *   Dès qu'un ordre change d'état, transmettre le snapshot d'audit (prix d'exécution réel, volume, id) au robot Aegis pour inscrire la transaction finale ou acter son rejet par manque de liquidité.
*   **🧪 Critère de Validation TDD (100% Coverage) :**
    *   Simuler le passage d'un ordre dans le Cerebro de test.
    *   Forcer un statut `Canceled` (par exemple en fixant une limite hors-marché).
    *   Vérifier que le robot Aegis reçoit la notification d'annulation et ne valide aucun trade fantôme dans son historique.

---

## 📌 Jalon 4.4 : Le Nœud de Réconciliation Comptable (`notify_trade`)
**Objectif :** Intercepter la clôture définitive d'une position Backtrader pour aligner le grand livre financier isolé et enregistrer les KPI.

*   **🛠️ Spécifications du Composant :**
    *   Dans `BacktraderStrategyBridge`, implémenter la méthode native `notify_trade(self, trade)`.
    *   Dès qu'`trade.isclosed` est détecté (le Stop-Loss ou le Take-Profit bracket a été percuté à l'écran), intercepter le PnL brut (`trade.pnl`) et net des commissions (`trade.pnlcomm`).
    *   Appeler la méthode comptable de l'`IsolatedAssetAccount` (Aegis) pour mettre à jour définitivement le solde de capital simulé.
    *   Transmettre les statistiques de clôture au `PerformanceAssessor` pour mettre à jour la matrice des 11 KPI quantitatifs d'Aegis.
*   **🧪 Critère de Validation TDD (100% Coverage) :**
    *   Lancer un trade complet (Achat -> Vente de protection touchée) dans le Cerebro de test.
    *   Vérifier qu'à la fin de la simulation, le solde de l'objet `IsolatedAssetAccount` correspond exactement au dollar près au solde comptabilisé par le système de Backtrader, pouvant la réconciliation absolue des deux environnements.
