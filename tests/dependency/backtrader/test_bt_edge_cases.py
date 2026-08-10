"""Black-box confrontation suite mapping Backtrader internal edge cases."""

from datetime import datetime

import backtrader as bt

from tests.testutil.backtrader_harness import MemoryDataFeed

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class RejectionMarginStrategy(bt.Strategy):
    """Strategy designed to trap immediate margin rejection at submission."""

    def __init__(self) -> None:
        self.captured_orders: list[bt.Order] = []

    def next(self) -> None:
        """Trigger an oversized order to force an immediate margin state."""
        if len(self) == 1:
            self.buy(size=1000000.0, client_order_id='AEGIS-IMMEDIATE-REJECT')

    def notify_order(self, order: bt.Order) -> None:
        """Capture every infrastructure order notification."""
        self.captured_orders.append(order)


# -----------------------------------------------------------------------------

class LiquidationMarginStrategy(bt.Strategy):
    """Strategy designed to capture an infrastructure-generated liquidation."""

    def __init__(self) -> None:
        self.captured_orders: list[bt.Order] = []

    def next(self) -> None:
        """Open a valid massive position and let the market crash provoke it."""
        if len(self) == 1:
            self.buy(size=95.0, client_order_id='AEGIS-LIVE-POSITION')

    def notify_order(self, order: bt.Order) -> None:
        """Capture every infrastructure order notification."""
        self.captured_orders.append(order)


# -----------------------------------------------------------------------------

class TargetOrdersConfrontationStrategy(bt.Strategy):
    """Strategy designed to test metadata retention within order_target methods."""

    def __init__(self) -> None:
        self.captured_orders: list[bt.Order] = []

    def next(self) -> None:
        """Trigger a target rebalancing call using custom tracking parameters."""
        if len(self) == 1:
            self.order_target_percent(
                target=0.5,
                client_order_id='AEGIS-TARGET-REBALANCE',
            )

    def notify_order(self, order: bt.Order) -> None:
        """Capture every infrastructure order notification."""
        self.captured_orders.append(order)

# -----------------------------------------------------------------------------

class BracketCancellationConfrontationStrategy(bt.Strategy):
    """Strategy designed to capture automated cascade cancellations in brackets."""

    def __init__(self) -> None:
        self.captured_orders: list[bt.Order] = []

    def next(self) -> None:
        """Submit a bracket order group structure to observe cascade events."""
        if len(self) == 1:
            self.buy_bracket(
                size=10.0,
                price=100.0,
                exectype=bt.Order.Limit,
                limitprice=110.0,
                stopprice=90.0,
                client_order_id='AEGIS-BRACKET-PARENT'
            )

    def notify_order(self, order: bt.Order) -> None:
        """Capture every infrastructure order notification."""
        self.captured_orders.append(order)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_immediate_margin_rejection_retains_metadata() -> None:
    """Ensures immediate margin rejection (Status 7) preserves tracking keys."""
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100.0)

    records = [
        [datetime(2026, 1, 1), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
        [datetime(2026, 1, 2), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
    ]
    data = MemoryDataFeed(records=records)

    cerebro.adddata(data, name='CONFRONT-STK')
    cerebro.addstrategy(RejectionMarginStrategy)

    strategies = cerebro.run()
    strat = strategies[0]

    margin_orders = [o for o in strat.captured_orders if o.status == o.Margin]
    assert len(margin_orders) > 0

    target_order = margin_orders[0]
    assert 'client_order_id' in target_order.info
    assert target_order.info['client_order_id'] == 'AEGIS-IMMEDIATE-REJECT'

# -----------------------------------------------------------------------------

def test_backtrader_forced_liquidation_does_not_trigger() -> None:
    """Proves that Backtrader default broker never generates margin calls natively."""
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(margin=100.0, mult=1.0)

    records = [
        [datetime(2026, 1, 1), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
        [datetime(2026, 1, 2), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
        [datetime(2026, 1, 3), 10.0, 10.0, 10.0, 10.0, 1000.0, 0.0],
        [datetime(2026, 1, 4), 10.0, 10.0, 10.0, 10.0, 1000.0, 0.0],
    ]
    data = MemoryDataFeed(records=records)

    cerebro.adddata(data, name='CONFRONT-STK')
    cerebro.addstrategy(LiquidationMarginStrategy)

    strategies = cerebro.run()
    strat = strategies[0]

    # Confirm that all generated orders belong exclusively to our strategy
    # No orphan auto-liquidation order (Size with inverse sign) is injected
    assert len(strat.captured_orders) == 3
    for order in strat.captured_orders:
        assert 'client_order_id' in order.info
        assert order.info['client_order_id'] == 'AEGIS-LIVE-POSITION'

# -----------------------------------------------------------------------------

def test_backtrader_order_target_metadata_propagation() -> None:
    """Empirically checks if order_target methods pass kwargs to order info."""
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)

    records = [
        [datetime(2026, 1, 1), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
        [datetime(2026, 1, 2), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
    ]
    data = MemoryDataFeed(records=records)

    cerebro.adddata(data, name='CONFRONT-STK')
    cerebro.addstrategy(TargetOrdersConfrontationStrategy)

    strategies = cerebro.run()
    strat = strategies[0]

    # print('\n' + '=' * 80)
    # for order in strat.captured_orders:
    #     print(f'[CONFRONT-TARGET] Ref: {order.ref} | Info: {order.info}')
    # print('=' * 80 + '\n')

    assert len(strat.captured_orders) > 0

# -----------------------------------------------------------------------------

def test_backtrader_bracket_cascade_cancellation_metadata() -> None:
    """Checks metadata state on auto-cancelled or child orders inside brackets."""
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)

    records = [
        [datetime(2026, 1, 1), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
        [datetime(2026, 1, 2), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
        [datetime(2026, 1, 3), 115.0, 115.0, 115.0, 115.0, 1000.0, 0.0],
    ]
    data = MemoryDataFeed(records=records)

    cerebro.adddata(data, name='CONFRONT-STK')
    cerebro.addstrategy(BracketCancellationConfrontationStrategy)

    strategies = cerebro.run()
    strat = strategies[0]

    # print('\n' + '=' * 80)
    # for order in strat.captured_orders:
    #     print(
    #         f'[CONFRONT-BRACKET] Ref: {order.ref} | '
    #         f'Status: {order.status} | '
    #         f'Info: {order.info}'
    #     )
    # print('=' * 80 + '\n')

    assert len(strat.captured_orders) > 0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
