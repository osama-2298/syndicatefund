"""WeatherTrader protocol — interface shared by paper and live traders."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from syndicate.polymarket.models import WeatherPortfolio, WeatherPosition


@runtime_checkable
class WeatherTrader(Protocol):
    """Protocol that both WeatherPaperTrader and WeatherLiveTrader satisfy."""

    def place_bet(
        self,
        condition_id: str,
        token_id: str,
        city: str,
        date: str,
        bin_label: str,
        entry_price: float,
        quantity: float,
        model_prob: float,
        edge: float,
        forecast_mean: float = 0.0,
        forecast_std: float = 0.0,
        total_market_volume: float = 0.0,
        n_bins: int = 10,
    ) -> WeatherPosition | None: ...

    def resolve_position(self, condition_id: str, won: bool) -> float: ...

    def get_portfolio(self) -> WeatherPortfolio: ...

    def save(self) -> None: ...
