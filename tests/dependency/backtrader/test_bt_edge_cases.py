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

class BracketPendingCancellationStrategy(bt.Strategy):
    """Strategy designed to capture cascade cancellations on pending orders."""

    def __init__(self) -> None:
        self.captured_orders: list[bt.Order] = []
        self.bracket_orders: list[bt.Order] = []

    def next(self) -> None:
        """Submit a bracket and cancel the parent on the following cycle."""
        if len(self) == 1:
            # Price engineering: We place the entry LIMIT at 90.0 while market
            # is at 100.0, ensuring the parent stays PENDING (not executed).
            self.bracket_orders = self.buy_bracket(
                size=10.0,
                price=90.0,
                exectype=bt.Order.Limit,
                limitprice=110.0,
                stopprice=80.0,
            )

            # Disambiguate tracking IDs across the bracket architecture
            self.bracket_orders[0].info['client_order_id'] = 'AEGIS-PARENT'
            self.bracket_orders[1].info['client_order_id'] = 'AEGIS-TP'
            self.bracket_orders[2].info['client_order_id'] = 'AEGIS-SL'

        elif len(self) == 2:
            # Cancel the pending parent order on the next chronological cycle
            self.cancel(self.bracket_orders[0])

    def notify_order(self, order: bt.Order) -> None:
        """Capture every infrastructure order notification."""
        self.captured_orders.append(order)

# -----------------------------------------------------------------------------

class BracketRejectionStrategy(bt.Strategy):
    """Strategy designed to trap complete bracket notifications upon rejection."""

    def __init__(self) -> None:
        self.captured_orders: list[bt.Order] = []

    def next(self) -> None:
        """Trigger an oversized bracket group to force immediate rejection."""
        if len(self) == 1:
            # Leverage Backtrader native multi-order bracket deployment
            self.buy_bracket(
                size=1000000.0,
                limitprice=105.0,
                stopprice=95.0,
            )

    def notify_order(self, order: bt.Order) -> None:
        """Capture every infrastructure order notification sequentially."""
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

# When parent order is canceled, we receive cancel for all childrens.
def test_backtrader_bracket_cascade_cancellation_metadata() -> None:
    """Checks metadata state on auto-cancelled child orders inside brackets."""
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)

    # Price sequence: Kept flat at 100.0 so the 90.0 LIMIT order never executes
    records = [
        [datetime(2026, 1, 1), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
        [datetime(2026, 1, 2), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
        [datetime(2026, 1, 3), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
    ]
    data = MemoryDataFeed(records=records)

    cerebro.adddata(data, name='CONFRONT-BRACKET')
    cerebro.addstrategy(BracketPendingCancellationStrategy)

    strategies = cerebro.run()
    strat = strategies[0]

    # print('\n' + '=' * 80)
    # for order in strat.captured_orders:
    #     print(
    #         f'[CONFRONT-BRACKET] Ref: {order.ref} | '
    #         f'Status: {order.getstatusname()} | '
    #         f'Info: {order.info}'
    #     )
    # print('=' * 80 + '\n')

    # Filter out orders that reached the final Canceled state
    canceled_orders = [
        o for o in strat.captured_orders
        if o.status == o.Canceled
    ]

    # A successful cascade must show exactly 3 canceled orders (Parent + TP + SL)
    assert len(canceled_orders) == 3

    # Verify that children keys are preserved within the infrastructure layout
    tp_orders = [o for o in canceled_orders if o.info.get('client_order_id') == 'AEGIS-TP']
    sl_orders = [o for o in canceled_orders if o.info.get('client_order_id') == 'AEGIS-SL']

    assert len(tp_orders) == 1
    assert len(sl_orders) == 1

# -----------------------------------------------------------------------------

# When parent is rejected(margin), we receive rejected for all children.
def test_backtrader_bracket_rejection_notifies_children() -> None:
    """Ensures child orders receive notifications when parent is rejected."""
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100.0)

    # Establish a minimal historical price matrix for simulation bootstrap
    records = [
        [datetime(2026, 1, 1), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
        [datetime(2026, 1, 2), 100.0, 100.0, 100.0, 100.0, 1000.0, 0.0],
    ]

    # Adapt to use your custom MemoryDataFeed or factory mapping
    data = MemoryDataFeed(records=records)
    cerebro.adddata(data, name='CONFRONT-STK')
    cerebro.addstrategy(BracketRejectionStrategy)

    strategies = cerebro.run()
    strat = strategies[0]

    # print('\n' + '=' * 80)
    # for order in strat.captured_orders:
    #     print(
    #         f'[CONFRONT-BRACKET] Ref: {order.ref} | '
    #         f'Status: {order.getstatusname()} | '
    #         f'Info: {order.info}'
    #     )
    # print('=' * 80 + '\n')

    assert len(strat.captured_orders) == 6

    submitted_orders = [
        o for o in strat.captured_orders
        if o.status == o.Submitted
    ]
    assert len(submitted_orders) == 3

    # Locate the trailing stop loss and take profit child orders
    child_orders = [
        o for o in strat.captured_orders
        if o.status in (o.Margin, o.Rejected)
    ]
    assert len(child_orders) == 3

    # This is 1 MAGIN (parent) and 2 REJECTED (children)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
