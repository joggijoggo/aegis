### 1. Vision et Architecture Globale du Projet AEGIS

**AEGIS** est un framework de trading algorithmique institutionnel, multi-actifs et haute performance, conçu selon les principes de la *Clean Architecture* (architecture hexagonale). Sa mission première est de découpler totalement la logique métier quantitative (les stratégies, le dimensionnement des positions, la gestion des risques) des contraintes techniques d'exécution (les API des courtiers comme IG Markets ou Interactive Brokers, et les moteurs de backtesting comme Backtrader).

Ce découpage strict garantit que le code d'une stratégie validé en backtest s'exécute de manière **100 % identique et déterministe** sur un compte de production réel, sans qu'il soit nécessaire de modifier une seule ligne de logique quantitative.

---

#### L'Architecture Hexagonale d'AEGIS

```
              [ EXTÉRIEUR : INFRASTRUCTURE & PASSERELLES ]
 ┌────────────────────────────────────────────────────────────────────┐
 │  Inbound Adapters (Flux)          │  Outbound Adapters (Ordres)    │
 │  - BacktraderStrategyBridge        │  - BacktraderBrokerAdapter     │
 │  - IGMarketsLiveStreamGate         │  - IGMarketsRESTExecutionPort  │
 └─────────────────┬─────────────────┴────────────────┬───────────────┘
                   │                                  │
                   ▼                                  ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │  CORE DOMAIN (Logique Métier Pure - Agnostique et Déterministe)   │
 │                                                                    │
 │   ┌───────────────────────┐              ┌─────────────────────┐   │
 │   │     PositionSizer     │              │     RiskManager     │   │
 │   │  Allocation Décimale  │ ◄──────────► │  Fusible Drawdown   │   │
 │   └───────────────────────┘              │    Margin Check     │   │
 │                                          └─────────────────────┘   │
 │                                                                    │
 │   ┌───────────────────────┐              ┌─────────────────────┐   │
 │   │ DynamicFrictionEngine │              │ InstrumentRegistry  │   │
 │   │ Spreads / Commissions │              │    Spécifications   │   │
 │   └───────────────────────┘              └─────────────────────┘   │
 └────────────────────────────────────────────────────────────────────┘
```

---

#### Les Composants Clés Déjà Déployés (Jalons 1 à 6)

1. **Le Modèle de Domaine Immuable (`core/models.py`)** : Conteneurs de données gelés (`@dataclass(frozen=True)`) garantissant qu'aucune mutation de prix, d'événement d'ordre ou de métrique de portefeuille ne peut survenir pendant le cycle de décision.
2. **Le Registre centralisé (`core/registry.py`)** : Base de données immuable cartographiant les constantes physiques des contrats (taille des lots, valeur du tick, pas de cotation minimum).
3. **Le Moteur de Friction (`core/frictions.py`)** : Simulateur de microstructure de marché. Il reproduit de manière adaptative l'élargissement des spreads en fonction de la volatilité de l'actif (ATR) et des pénalités de clôture interbancaire (tarification de nuit de la zone Europe/Paris, rollover de Londres).
4. **Les Adaptateurs et Ponts Inbound/Outbound (`brokers/`)** : Couches de conversion traduisant en temps réel les boucles d'événements spécifiques de Backtrader vers les structures normalisées d'AEGIS, et acheminant les ordres sous forme de *Bracket Orders* absolus (Protection par Stop Loss et Take Profit systématiques).
5. **Le Moteur d'Allocation Prudentiel (`core/position_sizer.py`)** : Calculateur mathématique en base 10 exacte (`Decimal`), neutralisant les approximations de la norme IEEE 754. Il applique la formule de risque pondérée par un facteur de confiance, avec une troncation stricte basée sur le pas de lot minimal autorisé par le courtier.
6. **Le Gestionnaire de Risque de Portefeuille (`core/risk_manager.py`)** : Filtre prudentiel binaire évaluant le drawdown historique global (coupe-circuit en cas de crise) et la couverture de marge exigée par actif avant de valider l'envoi d'une transaction.

---

### 2. Charte de Développement d'AEGIS (Les Règles Prussiennes)

La base de code d'AEGIS est régie par un standard de qualité de niveau financier. Toute modification doit respecter les contraintes suivantes sous peine de rejet par le linter et la CI/CD :

*   **TDD Rigide (Tolérance Zéro)** : Aucun code de production n'est toléré s'il n'est pas précédé d'un test unitaire ou d'intégration complet validant d'abord un échec (Phase RED), puis un succès (Phase GREEN). La couverture globale de code (*Statement Coverage*) doit être maintenue à **100,00 %**.
*   **Géométrie de Code** : Aucune ligne de code ne doit dépasser **90 caractères**. Les séparateurs graphiques (`# ===...`) doivent commencer en colonne 1.
*   **Densité Visuelle Vis-à-vis des Paramètres** : La notation multiligne systématique est proscrite pour éviter de surcharger le code. Elle est réservée exclusivement aux fonctions et instanciations dont la longueur menace la barrière des 90 caractères. Les structures courtes doivent être écrites de manière dense, sur une seule ligne. Lorsqu'un bloc multiligne est obligatoire, **un seul paramètre par ligne** est autorisé, s'achevant impérativement par une virgule de clôture.
*   **La Boussole Numérique Décimale** :
    *   **`decimal.Decimal` (Exactitude décimale)** : Impératif pour tout solde comptable (`balance`, `equity`), taille d'ordre (`lots`), commission, ou prix servant à une comparaison logique menant à une décision d'exécution (ex: adéquation de marge).
    *   **`float` (Vitesse matérielle)** : Réservé aux flux d'indicateurs quantitatifs continus (Moyennes mobiles, indices de volatilité ATR) pour conserver l'optimisation mathématique du CPU et des DataFrames Pandas/NumPy.

---

### 3. Plan de Développement Historique Réalisé (Jalons 1 à 6)

Ce plan retrace la trajectoire de construction des fondations du framework, de l'isolation du domaine immuable jusqu'à la mise en place de l'allocation de capital haute précision.

#### Jalon 1 — Isolation du Domaine et Modèles Immuables
*   **Objectif** : Figer les structures de données fondamentales de l'écosystème pour interdire toute mutation d'état en cours de calcul.
*   **Livrables Métiers** :
    *   `core/models.py` : Instanciation des conteneurs gelés (`@dataclass(frozen=True)`) pour encapsuler les snapshots de prix, les tickets d'intentions de transactions et les relevés de performance.
    *   `OrderStatus`, `OrderType`, `TransactionSide` : Énumérations strictes pour sécuriser le typage lors du routage des ordres.

#### Jalon 2 — Registre Centralisé et Spécifications Contrats
*   **Objectif** : Centraliser les constantes physiques des instruments financiers pour découpler le code des stratégies des spécifications imposées par les courtiers.
*   **Livrables Métiers** :
    *   `core/registry.py` : Base de données immuable (`InstrumentRegistry`) associant chaque ticker à ses contraintes réelles (taille de lot standard, valeur et taille minimale du tick).
    *   Levée d'erreurs explicites en cas de tentative d'accès à un actif non référencé, protégeant le framework contre les ordres non conformes.

#### Jalon 3 — Modélisation des Frictions et Microstructure de Marché
*   **Objectif** : Implémenter un moteur de simulation des coûts de transaction capable de reproduire la dégradation des spreads en conditions réelles.
*   **Livrables Métiers** :
    *   `core/frictions.py` : Moteur dynamique de friction (`DynamicFrictionEngine`) calculant l'écartement des fourchettes Bid/Ask en fonction de la volatilité locale (ATR) et de l'heure du serveur (bascule automatique en tarification de nuit Europe/Paris et rollover interbancaire de Londres).
    *   Calculateur de commissions institutionnelles basé sur le volume nominal traité.

#### Jalon 4 — Adaptateur Outbound et Traduction des Ordres
*   **Objectif** : Concevoir la passerelle de transmission des ordres vers l'extérieur sans lier le domaine au framework Backtrader.
*   **Livrables Métiers** :
    *   `brokers/backtrader_adapter.py` : Implémentation de l'adaptateur (`BacktraderBrokerAdapter`) convertissant les demandes de lots théoriques du robot en unités physiques et acheminant les ordres sous forme de *Bracket Orders* à prix absolus.
    *   Extraction transparente des snapshots financiers du courtier (solde et équité nette).

#### Jalon 5 — Pont Inbound et Ingestion de Flux Événementiels
*   **Objectif** : Ingerer et normaliser la chronologie des ticks générés par la boucle d'événements du simulateur.
*   **Livrables Métiers** :
    *   `brokers/backtrader_strategy_bridge.py` : Orchestrateur d'ingestion interceptant les fermetures de barres pour alimenter la mémoire glissante du robot, tout en traduisant les notifications asynchrones de cycles de vie d'ordres et de clôtures de positions vers le domaine AEGIS.

#### Jalon 6 — Moteur d'Allocation Prudentiel et Coupe-Circuit
*   **Objectif** : Sécuriser la décision financière de dimensionnement et de validation des risques avant tout routage d'ordre.
*   **Livrables Métiers** :
    *   `core/position_sizer.py` : Calculateur mathématique d'exposition pondérée par la confiance, appliquant une division entière rigide et une troncation stricte au pas de lot contractuel de l'actif.
    *   `core/risk_manager.py` : Fusible de portefeuille binaire auditant le drawdown historique maximal autorisé de la firme et bloquant l'ordre en cas de couverture de marge disponible insuffisante.
    *   **Sécurisation Décimale** : Refactoring intégral des briques de calcul (`Sizer`, `RiskManager`, `FrictionEngine`) vers le module `decimal.Decimal` pour éteindre définitivement les anomalies d'accumulation de la norme IEEE 754.

---

### 4. Plan de Développement Détaillé de Référence (Suivant)

Le plan de référence est conçu pour étendre de manière incrémentale les capacités d'AEGIS vers l'autonomie en production réelle.

#### Jalon 7 — Persistance de l'État, Cycle de Vie et Synchronisation
*   **Objectif** : Doter le framework d'une mémoire déterministe pour survivre aux crashs applicatifs ou aux pertes de connexion sans corrompre les métriques de risque.
*   **Livrables** :
    *   `core/state_manager.py` : Moteur de sérialisation atomique (écriture sécurisée par fichier temporaire) au format JSON.
    *   Sauvegarde de l'état complet : Fonds propres d'ancrage (*High-Water Mark*), drawdown historique maximum, liste des ordres en attente, et variables d'état des stratégies.
    *   Routine de démarrage à froid (*Cold Start*) : Rechargement de l'état disque et réalignement avec l'état réel renvoyé par le courtier.

#### Jalon 8 — Passerelle de Production Temps Réel (IG Markets API)
*   **Objectif** : Déployer le premier adaptateur de production sans altérer le cœur du domaine.
*   **Livrables** :
    *   `brokers/ig_markets_adapter.py` : Implémentation du port outbound gérant l'authentification OAuth2, le protocole REST de soumission des ordres, et la gestion des comptes de levier ESMA.
    *   `brokers/ig_markets_streaming.py` : Passerelle inbound se connectant aux sockets Lightstreamer d'IG pour ingérer le flux de ticks direct (Bid/Ask) et le convertir à la volée en structures `MarketPricePoint`.

#### Jalon 9 — Moteur d'Exécution Asynchrone et Réalignement
*   **Objectif** : Gérer la latence réseau, les rejets d'ordres du courtier (*Slippage*, requotes) et synchroniser l'état théorique du robot avec l'état physique du carnet d'ordres.
*   **Livrables** :
    *   `core/execution_orchestrator.py` : Gestionnaire asynchrone (via `asyncio`) assurant le suivi des ordres du statut `SUBMITTED` à `COMPLETED` ou `REJECTED`.
    *   Module de réalignement (*Reconciliation Layer*) : Algorithme auditant périodiquement (ex: toutes les 60 secondes) l'inventaire des positions réelles du courtier et exécutant des ordres correctifs automatiques en cas d'écart avec les positions théoriques du robot.

#### Jalon 10 — Ordonnanceur Multi-Stratégies et Tableau de Bord Audit
*   **Objectif** : Permettre la cohabitation de plusieurs robots sur un compte unique en centralisant l'allocation globale de capital.
*   **Livrables** :
    *   `core/portfolio_dispatcher.py` : Module de répartition des risques affectant des enveloppes de capital étanches à chaque stratégie sous-jacente.
    *   `logging/audit_logger.py` : Système de traçabilité haute fidélité générant des fichiers de logs au format structuré (JSON Lines) pour l'analyse post-mortem des décisions du sizer et des blocages du gestionnaire de risques.

---

### 5. Plans de Développement Alternatifs

Selon les priorités commerciales de la firme, deux trajectoires alternatives peuvent remplacer ou modifier l'ordre des jalons de référence.

#### Trajectoire Alternative A : Orientation "Recherche Quantitative & Haute Performance"
*Priorité mise sur la vitesse de backtesting, l'optimisation de portefeuilles massifs et le multi-devises avant le déploiement réel.*

*   **Jalon 7 Alternatif : Extension Multi-Devises (`CurrencyConverter`)**
    *   *Objectif* : Gérer le risque de change pour les portefeuilles multi-actifs (ex: trader le DAX en EUR et le Dow Jones en USD depuis un compte adossé en CHF).
    *   *Livrables* : Intégration d'un module de conversion dynamique des devises convertissant instantanément les valeurs de tick et les expositions nominales en devises de compte de référence via `Decimal`.
*   **Jalon 8 Alternatif : Intégration Native Vectorisée (Pandas / Vectorbt)**
    *   *Objectif* : Remplacer la lenteur de la boucle itérative bar-par-bar de Backtrader par un moteur d'analyse vectoriel pour tester des stratégies sur 20 ans d'historique en quelques secondes.
    *   *Livrables* : Adaptateur de données capable de diffuser des matrices NumPy tridimensionnelles au domaine tout en isolant la décision de dimensionnement de lot.

#### Trajectoire Alternative B : Orientation "Sécurité Maximale et Conformité Réglementaire"
*Priorité absolue mise sur la tolérance aux pannes, la cyber-sécurité et l'auditabilité par rapport à un régulateur financier (AMF, FCA).*

*   **Jalon 7 Alternatif : Journalisation Cryptographique des Décisions**
    *   *Objectif* : Rendre le carnet de décision du robot infalsifiable pour prouver la conformité des algorithmes de risques face aux audits internes.
    *   *Livrables* : Système de hachage en chaîne (type blockchain locale) où chaque structure `RiskValidationResult` émise est signée cryptographiquement (SHA-256) avec l'état précédent du portefeuille.
*   **Jalon 8 Alternatif : Supervision par Mocks et Injection de Pannes (Chaos Engineering)**
    *   *Objectif* : Tester la résilience d'AEGIS face à des scénarios catastrophes avant d'allouer le moindre euro en production.
    *   *Livrables* : Module simulant des pannes d'infrastructure majeures pendant l'envoi d'un ordre (déconnexion réseau exacte au moment du routage, gel de l'API du courtier, exécution partielle d'une ligne, décalage anormal du carnet d'ordres). Validation de la capacité du `RiskManager` à verrouiller le système en mode de sécurité totale (*Safe Mode*).
