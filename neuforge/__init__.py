"""
NeuForge Legends — Core Agent Runner
"""

from __future__ import annotations
import os
from typing import Optional
from .legends import LEGENDS, run_committee
from .models import get_model

__version__ = "1.0.0"
__all__ = ["LegendsPool", "run_committee", "LEGENDS"]


class LegendsPool:
    """
    Your AI investment committee — modeled on legendary investors.

    Example:
        pool = LegendsPool(api_key="gsk_...")
        result = pool.analyze(["NVDA", "TSLA"], package="pro")
        print(result.consensus)  # 'STRONG BUY'
    """

    PACKAGES = {
        "starter":  ["warren_buffett", "charlie_munger", "michael_burry"],
        "pro":      ["warren_buffett", "charlie_munger", "michael_burry",
                     "cathie_wood", "bill_ackman", "ben_graham",
                     "peter_lynch", "phil_fisher", "stanley_druckenmiller",
                     "aswath_damodaran"],
        "allstars": None,  # All 18
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.1-8b-instant",
        provider: str = "groq",
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model
        self.provider = provider

    def analyze(
        self,
        tickers: list[str],
        package: str = "pro",
        analysts: Optional[list[str]] = None,
        start_date: str = "2024-01-01",
        end_date: str = "2025-01-01",
    ):
        """Run the committee analysis on given tickers."""
        if analysts is None:
            analysts = self.PACKAGES.get(package) or list(LEGENDS.keys())
        return run_committee(
            tickers=tickers,
            analysts=analysts,
            api_key=self.api_key,
            model=self.model,
            start_date=start_date,
            end_date=end_date,
        )

    def list_legends(self) -> list[dict]:
        """Return all available legend agents."""
        return [{"id": k, **v} for k, v in LEGENDS.items()]
