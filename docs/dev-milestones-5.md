# Aegis Framework - Engineering Specifications Report
## Milestone 5: Advanced Friction Engine & Market Microstructure Simulation

### 1. Architectural Justification & Core Objective
In high-frequency and institutional quantitative trading, executing strategies on theoretical mid-market prices introduces an idealization bias that leads to systematic underperformance in real-world environments. The primary objective of Milestone 5 is to transition Aegis Framework from a static spread footprint to a dynamic, asset-specific, and volatility-sensitive replication of the IG Markets clearing environment.

By modeling real-world constraints—such as time-based liquidity drain, volatility-driven slippage decay, asset fee matrices, and overnight financing overheads—the Core Domain will be insulated against backtesting overfitting. This ensures that alpha performance metrics generated in backtesting are mathematically replicable when transitioning to the Live Infrastructure Adapter (Milestone 8).

---

### 2. Microstructure Mathematical Breakdown
The overall mathematical cost calculation injected into each individual execution slice follows the equation:

C_total = S_dynamic + Slippage + Commission + Overnight

Where:
*   S_dynamic: Driven by base pip configurations, seasonal local Paris/London clock indicators, and structural volatility expansion coefficients.
*   Slippage: Non-linear execution degradation mapping available liquidity thinning during tail-risk events.
*   Commission: Tiered institutional schedules applying exchange flat rates or notionally scaled percentages.
*   Overnight: Cost of carry calculations matching interbank interest rate differentials for open risk exposure carried past settlement cutoffs.

---

### 3. Granular Development Roadmap (4-Stage Cycle)

[MILESTONE 5]
   |-- Sub-Milestone 5.1: Time-Based Liquidity Regimes (COMPLETED)
   |-- Sub-Milestone 5.2: Volatility-Driven Slippage Decay (NEXT STEP)
   |-- Sub-Milestone 5.3: Asset Profiles & Commission Matrix
   +-- Sub-Milestone 5.4: End-to-End Cerebro Loop Integration

#### Sub-Milestone 5.1: Time-Based Liquidity Regimes (Completed)
*   Objective: Model the daily institutional liquidity dry-up matching the London Settlement Rollover.
*   Logic: Convert input UTC transaction timestamps into local Europe/Paris time. Apply an absolute 4.0x spread markup penalty if the transaction coordinates fall outside standard liquid market parameters (Night tariff active between 23:00 and 08:00 local Paris time).
*   Verification: Validated via test_ig_friction_engine_paris_timezone_handling checking seasonal timeline anchors across both winter and summer clock shifts.

#### Sub-Milestone 5.2: Volatility-Driven Slippage Decay
*   Objective: Model execution price degradation driven by immediate order book thinning.
*   Logic: Consume the rolling mathematical metric MarketPricePoint.current_atr. Integrate a localized volatility coefficient where spread widths expand linearly or stochastically during rapid price expansions, and inject asymmetric slippage on execution returns.
*   Deliverables: Code updates in core/frictions.py to account for ATR thresholds. Isolation unit test expansion inside tests/core/test_frictions.py simulating high-volatility market crises (Phase RED initialization).

#### Sub-Milestone 5.3: Asset Profiles & Commission Matrix
*   Objective: Move away from hardcoded FX-centric assumptions to natively support Indices, Forex, Commodities, and Crypto.
*   Logic: Implement an immutable, type-safe asset configuration matrix binding specific InstrumentSpecification tokens to their exact clearing profiles (e.g., minimum index point bounds, contract-based ticket flat rates, or asset notional value percentages).
*   Deliverables: Validation rules and profile lookups inside core/frictions.py. Multi-asset edge case test scenarios validating commission calculations inside tests/core/test_frictions.py.

#### Sub-Milestone 5.4: End-to-End Cerebro Loop Integration
*   Objective: Connect the completed dynamic engine directly to the active Backtrader routing infrastructure.
*   Logic: Refactor BacktraderBrokerAdapter and BacktraderStrategyBridge to pull real-time friction calculations dynamically instead of relying on flat models. Ensure simulated account tracking in IsolatedAssetAccount deducts realistic costs natively.
*   Deliverables: Integration test validation via tests/integration/test_backtrader_e2e.py demonstrating degraded, non-linear, but structurally accurate strategy return distributions matching historical IG institutional ledger data.
