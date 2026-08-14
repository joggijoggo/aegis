"""Aegis Framework - Backtrader Infrastructure Runner Component Tests.

Validates multi-threaded orchestration, worker lifecycle setup, and error propagation mechanics.
"""

from threading import Thread
from unittest.mock import MagicMock, patch

import backtrader as bt
import pytest

from aegis.core.base import BaseBot
from aegis.core.model import ContractSpecification
from aegis.core.position_sizer import PositionSizer
from aegis.infra.backtrader import BacktraderRunner

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

@pytest.fixture
def mock_dependencies():
    """Mocks external infrastructure components to isolate the Runner."""
    with patch('aegis.infra.backtrader.backtrader_runner.BacktraderBridge') as mock_bridge, \
         patch('aegis.infra.backtrader.backtrader_runner.BacktraderMarketFeed') as mock_feed, \
         patch('aegis.infra.backtrader.backtrader_runner.BacktraderBrokerAdapter') as mock_adapter, \
         patch('aegis.infra.backtrader.backtrader_runner.BacktraderProxyStrategy') as mock_strategy, \
         patch('aegis.infra.backtrader.backtrader_runner.ContractRegistry') as mock_registry, \
         patch('aegis.infra.backtrader.backtrader_runner.AegisExecutionEngine') as mock_engine, \
         patch('backtrader.Cerebro') as mock_cerebro:

        yield {
            'bridge': mock_bridge,
            'market_feed': mock_feed,
            'broker_adapter': mock_adapter,
            'proxy_strategy': mock_strategy,
            'contract_registry': mock_registry,
            'execution_engine': mock_engine,
            'cerebro': mock_cerebro
        }

# -----------------------------------------------------------------------------

@pytest.fixture
def runner_inputs():
    """Generates the baseline inputs required by the constructor."""
    bot = MagicMock(spec=BaseBot)
    data_feed = MagicMock(spec=bt.feed.DataBase)
    position_sizer = MagicMock(spec=PositionSizer)

    contract_specification = MagicMock(spec=ContractSpecification)
    contract_specification.symbol = 'EURUSD'

    return {
        'bot': bot,
        'data_feed': data_feed,
        'position_sizer': position_sizer,
        'contract_specification': contract_specification,
    }

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================

def test_backtrader_runner_allocation_lifecycle(mock_dependencies, runner_inputs) -> None:
    """Verifies that initialization correctly sets up Cerebro and the Engine."""
    runner = BacktraderRunner(
        bot=runner_inputs['bot'],
        data_feed=runner_inputs['data_feed'],
        position_sizer=runner_inputs['position_sizer'],
        contract_specification=runner_inputs['contract_specification'],
        initial_cash=50000.0,
        commission_scheme=None
    )

    instance_cerebro = mock_dependencies['cerebro'].return_value
    instance_cerebro.adddata.assert_called_once_with(runner_inputs['data_feed'], 'EURUSD')
    instance_cerebro.broker.setcash.assert_called_once_with(50000.0)
    instance_cerebro.addstrategy.assert_called_once()
    instance_cerebro.broker.addcommissioninfo.assert_not_called()

    # Validate local ContractRegistry instantiation parameters
    mock_dependencies['contract_registry'].assert_called_once_with(
        specifications={'EURUSD': runner_inputs['contract_specification']}
    )

    mock_dependencies['execution_engine'].assert_called_once_with(
        bot=runner_inputs['bot'],
        broker_adapter=runner._broker_adapter,
        contract_registry=mock_dependencies['contract_registry'].return_value,
        position_sizer=runner_inputs['position_sizer']
    )

# -----------------------------------------------------------------------------

def test_backtrader_runner_commission_injection(mock_dependencies, runner_inputs) -> None:
    """Verifies commission scheme injection when provided."""
    mock_commission = MagicMock(spec=bt.CommissionInfo)

    BacktraderRunner(
        **runner_inputs,
        initial_cash=10000.0,
        commission_scheme=mock_commission
    )

    instance_cerebro = mock_dependencies['cerebro'].return_value
    instance_cerebro.broker.addcommissioninfo.assert_called_once_with(
        mock_commission,
        name='EURUSD'
    )

# -----------------------------------------------------------------------------

def test_backtrader_runner_broker_adapter_accessor(mock_dependencies, runner_inputs) -> None:
    """Verifies the broker adapter accessor."""
    runner = BacktraderRunner(**runner_inputs)
    assert runner._get_broker_adapter() == runner._broker_adapter

# -----------------------------------------------------------------------------

def test_backtrader_runner_domain_worker_execution(mock_dependencies, runner_inputs) -> None:
    """Verifies that the domain worker invokes the execution cycle."""
    runner = BacktraderRunner(**runner_inputs)
    worker = runner._create_domain_worker()

    worker()

    runner._engine.run_execution_cycle.assert_called_once_with(
        symbol='EURUSD',
        market_feed=runner._market_feed
    )

# -----------------------------------------------------------------------------

def test_backtrader_runner_domain_worker_fault_tolerance(mock_dependencies, runner_inputs) -> None:
    """The domain worker must force-stop the bridge if an exception occurs."""
    runner = BacktraderRunner(**runner_inputs)
    runner._engine.run_execution_cycle.side_effect = RuntimeError('Domain crash')
    worker = runner._create_domain_worker()

    with pytest.raises(RuntimeError, match='Domain crash'):
        worker()

    runner._bridge.stop_simulation.assert_called_once()

# -----------------------------------------------------------------------------

def test_backtrader_runner_infra_worker_execution(mock_dependencies, runner_inputs) -> None:
    """Verifies that the infrastructure worker starts Cerebro."""
    runner = BacktraderRunner(**runner_inputs)
    worker = runner._create_infra_worker()

    worker()

    runner._cerebro.run.assert_called_once()

# -----------------------------------------------------------------------------

def test_backtrader_runner_infra_worker_fault_tolerance(mock_dependencies, runner_inputs) -> None:
    """The infrastructure worker must force-stop the bridge if Cerebro crashes."""
    runner = BacktraderRunner(**runner_inputs)
    runner._cerebro.run.side_effect = RuntimeError('Cerebro crash')
    worker = runner._create_infra_worker()

    with pytest.raises(RuntimeError, match='Cerebro crash'):
        worker()

    runner._bridge.stop_simulation.assert_called_once()

# -----------------------------------------------------------------------------

@patch('aegis.infra.backtrader.backtrader_runner.Thread')
def test_backtrader_runner_nominal_lifecycle(mock_thread_cls, mock_dependencies, runner_inputs) -> None:
    """Verifies nominal lifecycle: setup, launch, synchronization, and teardown."""
    runner = BacktraderRunner(**runner_inputs)

    runner._bridge.is_simulation_completed.return_value = True

    mock_infra_thread = MagicMock(spec=Thread)
    mock_domain_thread = MagicMock(spec=Thread)
    mock_infra_thread.is_alive.return_value = False
    mock_domain_thread.is_alive.return_value = False

    mock_thread_cls.side_effect = [mock_infra_thread, mock_domain_thread]

    runner.run(timeout=5.0)

    # Assert that exactly 2 threads were instantiated
    assert mock_thread_cls.call_count == 2

    # Inspect first instantiation call (INFRA thread)
    infra_call_kwargs = mock_thread_cls.call_args_list[0].kwargs
    assert infra_call_kwargs['daemon'] is True
    assert infra_call_kwargs['name'] == 'INFRA'
    assert callable(infra_call_kwargs['target'])

    # Inspect second instantiation call (MAIN thread)
    domain_call_kwargs = mock_thread_cls.call_args_list[1].kwargs
    assert domain_call_kwargs['daemon'] is True
    assert domain_call_kwargs['name'] == 'MAIN'
    assert callable(domain_call_kwargs['target'])

    # Validate startup sequence
    mock_infra_thread.start.assert_called_once()
    mock_domain_thread.start.assert_called_once()

    # Validate join synchronization with timeout propagation
    mock_infra_thread.join.assert_called_once_with(timeout=5.0)
    mock_domain_thread.join.assert_called_once_with(timeout=5.0)

    runner._bridge.stop_simulation.assert_called_once()

# -----------------------------------------------------------------------------

def test_backtrader_runner_graceful_shutdown_enforcement(mock_dependencies, runner_inputs) -> None:
    """Verifies that an AssertionError is raised if threads or bridge fail to terminate clean."""
    runner = BacktraderRunner(**runner_inputs)

    runner._bridge.is_simulation_completed.return_value = False
    with pytest.raises(AssertionError):
        runner._assert_graceful_shutdown()

    runner._bridge.is_simulation_completed.return_value = True
    runner._infra_thread = MagicMock(spec=Thread)
    runner._infra_thread.is_alive.return_value = True
    with pytest.raises(AssertionError):
        runner._assert_graceful_shutdown()

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
