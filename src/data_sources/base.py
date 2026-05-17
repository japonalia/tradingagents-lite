from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class MarketDataResult:
    symbol: str
    source: str
    market_data: dict[str, Any]
    history: pd.DataFrame
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
