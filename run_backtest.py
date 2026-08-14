#!/usr/bin/env python3
"""Aegis Framework - Parameterized Multi-Broker Bootstrap Entrypoint.

Configures historical data feeds with custom date boundaries, instantiates
the trading bot, maps specific brokerage commission profiles for multiple
brokers (IG, IBKR, SAXO), and boots the runner execution engine.
"""

import argparse
from decimal import Decimal
import logging
from datetime import datetime
from pathlib import Path

import backtrader as bt
from rich.progress import Progress

from aegis.config.market_specs import (
    IBKR_SPECIFICATIONS,
    IG_MARKETS_SPECIFICATIONS,
    SAXO_BANK_SPECIFICATIONS,
)
from aegis.core.base import BaseBot
from aegis.core.currency_converter import CurrencyConverter
from aegis.core.model import (
    ContractSpecification,
    ExposureIntent,
    MarketContext,
)
from aegis.core.position_sizer import PositionSizer
from aegis.core.telemetry import SessionHistory
from aegis.infra.backtrader import (
    BacktraderRunner,
    ForexDynamicLeverageScheme,
    FutureFixedMarginScheme,
)

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

class PassiveBot(BaseBot):
    """Passive bot that stay flat."""

# -----------------------------------------------------------------------------

    def evaluate(
        self,
        market_context: MarketContext,
        historical_values: list[float],
    ) -> ExposureIntent:
        return ExposureIntent(alpha_direction=None)

# -----------------------------------------------------------------------------

    @property
    def warm_up_period(self) -> int:
        """Returns the structural technical indicator warm up bar lookback count."""
        return 0

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

# Mapping brokers to their imported specification catalogs
BROKER_SPEC_MAP = {
    'IG': IG_MARKETS_SPECIFICATIONS,
    'IBKR': IBKR_SPECIFICATIONS,
    'SAXO': SAXO_BANK_SPECIFICATIONS,
}

# -----------------------------------------------------------------------------

def create_commission_scheme(symbol: str, broker_specs: dict) -> bt.CommissionInfo:
    """Factory creating the appropriate Backtrader commission scheme.

    Args:
        symbol: The targeted financial instrument ticker name.
        broker_specs: The selected active broker specification dictionary.

    Returns:
        A configured Backtrader CommissionInfo instance matching market dynamics.
    """
    if symbol not in broker_specs:
        raise ValueError(
            f'Symbol {symbol} is missing from selected broker configurations.'
        )

    contract_spec = broker_specs[symbol]

    # Metal/Commodity dynamic handling (e.g., Gold requires fixed margin)
    if symbol == 'XAUUSD':
        return FutureFixedMarginScheme(
            margin=float(contract_spec.margin_requirement * 1000),
            mult=float(contract_spec.contract_multiplier),
        )

    # Standard Forex currency pairs utilizing dynamic percentage leverage
    # Leverage parsing calculation is now handled inside the scheme init
    return ForexDynamicLeverageScheme(
        margin_requirement=float(contract_spec.margin_requirement),
        mult=float(contract_spec.contract_multiplier),
    )

# -----------------------------------------------------------------------------

def create_position_sizer(
    contract_spec: ContractSpecification,
    account_currency: str = 'USD',
) -> PositionSizer:
    """Factory creating a PositionSizer seeded with automatic currency mappings.

    Args:
        contract_spec: Microstructural parameters of the targeted asset.
        account_currency: The active structural base currency of the portfolio.

    Returns:
        A fully initialized PositionSizer instance ready for risk equations.
    """
    currency_converter = CurrencyConverter()
    quote_currency = contract_spec.quote_currency

    # Inject an absolute 1:1 translation vector to secure isolation
    # whenever the asset quote denomination mismatches the account wallet
    if quote_currency != account_currency:
        identity_pair = f'{quote_currency}{account_currency}'
        currency_converter.update_rate(
            pair=identity_pair,
            rate=Decimal('1.0'),
        )

    return PositionSizer(currency_converter=currency_converter)

# -----------------------------------------------------------------------------

def estimate_total_ticks(
    csv_filepath: Path,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """Estimates the exact total of row ticks matching temporal constraints.

    Args:
        csv_filepath: Path filesystem coordinate pointing to the data catalog.
        start_date: Backtest simulation chronological start boundary.
        end_date: Backtest simulation chronological termination boundary.

    Returns:
        The verified discrete counts of timeline entries inside the scope.
    """
    total_lines = 0

    with csv_filepath.open('r') as f:
        # Skip the layout header row automatically
        next(f)
        for line in f:
            # Extract the ISO datetime string chunk from the first column
            columns = line.split(',')
            if not columns:
                continue

            try:
                line_dt = datetime.strptime(columns[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue

            # Enforce chronological validation boundaries constraints
            if start_date and line_dt < start_date:
                continue
            if end_date and line_dt > end_date:
                continue

            total_lines += 1

    return total_lines

# -----------------------------------------------------------------------------

def valid_date(date_string: str) -> datetime:
    """Validates and parses incoming command line date strings.

    Args:
        date_string: A date string formatted as YYYY-MM-DD.

    Returns:
        A parsed datetime object.
    """
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f'Not a valid date: "{date_string}". Use YYYY-MM-DD.',
        ) from error

# -----------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    """Configures and processes macro command line interface options.

    Returns:
        A structured namespace container populated with validated inputs.
    """
    parser = argparse.ArgumentParser(
        description='Aegis Backtrader Multi-Broker Bootstrap Runner.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Visual Group 1: Broker & Market Profile Constraints
    market_group = parser.add_argument_group('Broker & Market Configuration')
    market_group.add_argument(
        '-b', '--broker',
        type=str,
        choices=['IG', 'IBKR', 'SAXO'],
        default='IG',
        help='The target execution broker account metadata rule mapping.'
    )
    market_group.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='The ticker symbol to backtest (e.g., EURUSD, XAUUSD).'
    )
    market_group.add_argument(
        '--initial-cash',
        type=float,
        default=10000.0,
        help='Starting virtual capital balance allocation.'
    )

    # Visual Group 2: Temporal Boundaries Constraints
    temporal_group = parser.add_argument_group(
        'Temporal Boundaries Constraints'
    )
    temporal_group.add_argument(
        '--start-date',
        type=valid_date,
        help='Backtest filter starting boundary format YYYY-MM-DD.'
    )
    temporal_group.add_argument(
        '--end-date',
        type=valid_date,
        help='Backtest filter terminating boundary format YYYY-MM-DD.'
    )

    return parser.parse_args()

# -----------------------------------------------------------------------------

def initialize_runner(
    bot: BaseBot,
    symbol: str,
    broker: str = 'IG',
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    initial_cash: float = 10000.0,
    progress: Progress | None = None,
) -> BacktraderRunner:
    """Assembles framework requirements and initializes the runner lifecycle.

    Args:
        bot: The active quantitative strategy bot instance to evaluate.
        symbol: The financial asset pair ticker symbol to run.
        broker: Targeted infrastructure broker account blueprint name.
        start_date: Backtest simulation chronological start boundary.
        end_date: Backtest simulation chronological termination boundary.
        initial_cash: Virtual collateral base allocated for tracking.

    Returns:
        A completely wired up BacktraderRunner instance ready for execution.
    """
    symbol_upper = symbol.upper()
    csv_filepath = (
        Path('data') / 'raw' / 'ejtraderLabs' / f'{symbol_upper}m15.csv'
    )

    # Ensure targeted historical dataset exists locally
    if not csv_filepath.exists():
        raise FileNotFoundError(
            f"Missing historical data catalog at path: '{csv_filepath}'"
        )

    broker_specs = BROKER_SPEC_MAP[broker.upper()]
    if symbol_upper not in broker_specs:
        raise ValueError(
            f"Symbol '{symbol_upper}' is missing from {broker} configs."
        )

    contract_spec = broker_specs[symbol_upper]
    position_sizer = create_position_sizer(
        contract_spec=contract_spec,
        account_currency='USD', # FIXME: this is currently hardcoded in AccountSnapshot.
    )

    # Prepare historical data stream constraints matching ejtraderLabs schema
    # time=-1: Time data is integrated within the datetime string
    # openinterest=-1: Asset dataset does not include open interest matrix fields
    data_feed = bt.feeds.GenericCSVData(
        dataname=str(csv_filepath),
        dtformat='%Y-%m-%d %H:%M:%S',
        timeframe=bt.TimeFrame.Minutes,
        compression=15,
        fromdate=start_date,
        todate=end_date,
        headers=True,
        datetime=0,
        time=-1,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1,
    )

    commission_scheme = create_commission_scheme(
        symbol=symbol_upper,
        broker_specs=broker_specs
    )

    runner = BacktraderRunner(
        bot=bot,
        data_feed=data_feed,
        position_sizer=position_sizer,
        contract_specification=contract_spec,
        initial_cash=initial_cash,
        commission_scheme=commission_scheme,
    )

    if progress:
        total_lines = estimate_total_ticks(
            csv_filepath=csv_filepath,
            start_date=start_date,
            end_date=end_date,
        )

        task_id = progress.add_task(
            description=f'[cyan]Backtesting "{symbol_upper}"',
            total=total_lines,
        )

        def update_bar(event: str):
            if event == 'MARKET_TICK':
                progress.update(task_id, advance=1)

        runner.register_listener(update_bar)

    return runner

# -----------------------------------------------------------------------------

def main() -> None:
    """Bootstrap root entrypoint orchestrating modular sequence logic."""
    logging.basicConfig(
        level=logging.WARN,
        format='%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s',
        force=True,
    )

    args = parse_arguments()

    with Progress() as progress:
        session_history = SessionHistory()
        bot = PassiveBot()

        runner = initialize_runner(
            bot=bot,
            symbol=args.symbol,
            broker=args.broker,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_cash=args.initial_cash,
            progress=progress,
        )

        runner._engine.register_listener(session_history.receive)

        runner.run()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

if __name__ == '__main__':
    main()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
