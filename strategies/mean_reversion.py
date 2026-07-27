"""Aegis Framework - Mean Reversion Strategy Layer.

Implements structural execution boundaries using automated bracket order routing.
"""

from brokers.base_broker import AbstractBrokerBridge
from core.models import InstrumentSpecification
from core.models import MarketPricePoint
from core.models import OrderType
from core.models import TradeTelemetrySnapshot
from core.models import TransactionSide
from strategies.base_strategy import AbstractStrategy
from strategies.regime_manager import MarketRegimeClassifier

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class AegisMeanReversionBot(AbstractStrategy):
    """Executes range boundaries entries backed by statistical classification maps."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        broker_bridge: AbstractBrokerBridge,
        instrument_specs: dict[str, InstrumentSpecification],
        warm_up_bars: int = 200
    ):
        """Initializes the target statistical tracking matrices and ledger arrays."""
        super().__init__(
            broker_bridge=broker_bridge,
            instrument_specs=instrument_specs,
            warm_up_bars=warm_up_bars,
        )
        self.classifier = MarketRegimeClassifier()
        self.telemetry_history: list[TradeTelemetrySnapshot] = []

# -----------------------------------------------------------------------------

    def _on_bar_close(
        self,
        asset: str,
        price_snapshot: MarketPricePoint,
        historical_closes: list[float]
    ) -> None:
        """Evaluates ongoing pricing arrays to release automated brackets trades."""
        # Compute internal indicator metrics using simple rolling baseline mechanisms
        rolling_mean = sum(historical_closes[-self.warm_up_bars:]) / self.warm_up_bars

        # Evaluate current statistical structures configuration
        regime = self.classifier.classify_series(historical_closes)

        # Execution criteria: Mean Reversion dominant with significant price expansion
        if regime.mean_reversion > 0.40 and price_snapshot.mid_price > rolling_mean * 1.02:
            # Instantiation of explicable post-mortem snapshots parameters PRIOR to order routing
            snapshot = TradeTelemetrySnapshot(
                timestamp=price_snapshot.timestamp,
                indicator_value=rolling_mean,
                regime_vector=regime
            )
            self.telemetry_history.append(snapshot)

            # Route standardized order receipts structures to the ledger port
            self.place_bracket_order(
                symbol=asset,
                side=TransactionSide.SHORT,
                order_type=OrderType.MARKET,
                volume_lots=1.0,
                current_price=price_snapshot.mid_price,
                stop_loss_pips=20.0,
                take_profit_pips=40.0
            )

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
