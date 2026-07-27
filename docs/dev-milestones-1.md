# 🛡️ AEGIS - PLAN DE DÉVELOPPEMENT DÉTAILLÉ : JALON 1

## 📊 Étape 1.1 : Le Moteur de Synchronisation Temporelle (`core/engine.py`)
**Objectif :** Créer la Master Clock et l'algorithme d'alignement asynchrone des données Forex en UTC absolu.

*   **Livrables techniques :**
    *   Initialisation de la classe `MasterClockBacktestEngine`.
    *   Algorithme de boucle temporelle linéaire (Time-Step par Time-Step) basé sur le plus petit pas de temps (ex: 15 minutes).
    *   Mécanisme de **Forward-Fill** automatique : si un actif manque de liquidité et n'a pas de bougie au timestamp actuel $T$, duplication immédiate du dictionnaire de la bougie $T-1$ pour maintenir la continuité des indicateurs techniques sans désynchronisation.
*   **Validation :** Injecter deux fichiers CSV avec des dates de début différentes et des trous de cotation nocturnes. Vérifier que la boucle génère un flux de données propre et unifié.

---

## 🔒 Étape 1.2 : Le Bouclier Anti-Triche Multi-Timeframe (`core/engine.py`)
**Objectif :** Développer l'agrégateur de bougies macro sans aucun biais de regard vers le futur (*Look-Ahead Bias*).

*   **Livrables techniques :**
    *   Implémentation de la classe `TimeframeAggregator`.
    *   Gestionnaire de mémoire tampon (*buffers*) isolée par paire Forex et par unité de temps macro (ex: 4H, Daily).
    *   Logique de clôture stricte : une bougie macro (ex: 4H) calculée à partir de bougies de 15 minutes n'est validée et exposée à la stratégie qu'à la seconde exacte où sa dernière bougie de 15 minutes constitutive est entièrement clôturée.
*   **Validation :** Tenter de lire le Close de la bougie 4H à $12h15$ au lieu de $16h00$ et vérifier que le framework renvoie une exception ou bloque l'accès à la donnée.

---

## 📈 Étape 1.3 : L'Émulateur de Frictions Réelles IG Group (`core/engine.py`)
**Objectif :** Coder le moteur de tarification dynamique et de spread adaptatif d'IG Market.

*   **Livrables techniques :**
    *   Implémentation de la classe `IGGroupFrictionEngine`.
    *   Formule du spread variable indexé sur la volatilité immédiate calculée via l'ATR de la paire.
    *   Résolveur de fuseau horaire dynamique via `zoneinfo` (`Europe/London`).
    *   Pénalité de liquidité : élargissement automatique à 4× du spread de base durant le créneau de roll-over interbancaire d'IG (entre 21h45 et 23h15 heure de Londres), gérant de manière transparente l'heure d'été britannique (BST) et l'heure d'hiver (GMT).
*   **Validation :** Imprimer les prix d'exécution *Bid* et *Ask* générés à $14h00$ (spread normal) et à $22h00$ Londres (spread élargi), et valider l'écart en pips.

---

## 💸 Étape 1.4 : Le Grand Livre de Financement Overnight Tom-Next (`core/accounts.py`)
**Objectif :** Connecter la boucle de simulation aux débits financiers nocturnes réels d'IG.

*   **Livrables techniques :**
    *   Mise à jour de la méthode `process_market_bar` au sein de la classe `IsolatedAssetAccount`.
    *   Détection de la coupure quotidienne de fin de journée fixée à 22h00 heure de Londres.
    *   Calculatrice d'exposition notionnelle brute par lot Forex (1 lot standard = 100 000 unités).
    *   **Règle du Triple Mercredi :** Multiplication par 3 des frais de financement Tom-Next si le timestamp UTC détecté correspond au mercredi soir, simulant le dénouement bancaire du week-end.
*   **Validation :** Vérifier sur un trade maintenu sur 2 semaines que le solde cash du sous-compte est débité d'un montant standard le lundi, mardi, jeudi, vendredi, et de trois fois ce montant le mercredi soir à 22h00 Londres précises.
