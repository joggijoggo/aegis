"""Aegis Framework - Walk-Forward Optimization Engine.

Calculates continuous rolling walk-forward slices for model validation while
strictly banning look-ahead or selection data leakages.
"""
from datetime import datetime
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================


class WalkForwardOptimizer:
    """Orchestrates historical dataset slicing into train/test windows."""

# -----------------------------------------------------------------------------

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        train_days: int,
        test_days: int
    ):
        """Initializes the rolling slice window partitioner.

        Args:
            start_date (datetime): Absolute simulation start boundary.
            end_date (datetime): Absolute simulation end boundary.
            train_days (int): Width of the training parameter grid window.
            test_days (int): Width of the execution evaluation window.
        """
        self.start_date = start_date.replace(tzinfo=ZoneInfo('UTC'))
        self.end_date = end_date.replace(tzinfo=ZoneInfo('UTC'))
        self.train_delta = timedelta(days=train_days)
        self.test_delta = timedelta(days=test_days)

# -----------------------------------------------------------------------------

    def generate_sliding_windows(self) -> list[dict[str, Any]]:
        """Generates consecutive training and testing window dictionaries.

        Returns:
            list[dict[str, Any]]: Sequential boundary date parameter sets.
        """
        generated_slices = []
        current_train_start = self.start_date

        while True:
            current_train_end = current_train_start + self.train_delta
            current_test_start = current_train_end
            current_test_end = current_test_start + self.test_delta

            # Break structural loops if testing boundaries exceed master dates
            if current_test_end > self.end_date:
                break

            generated_slices.append({
                'train_start': current_train_start,
                'train_end': current_train_end,
                'test_start': current_test_start,
                'test_end': current_test_end
            })

            # Advance timeline by the testing segment offset increment
            current_train_start = current_train_start + self.test_delta

        return generated_slices


# =============================================================================
# -----------------------------------------------------------------------------
# =============================================================================
