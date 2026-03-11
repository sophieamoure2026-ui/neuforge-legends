#!/usr/bin/env python3
"""
neuforge-legends quickstart demo.
Run: python examples/demo.py
"""

from neuforge import LegendsPool

# Set your GROQ_API_KEY in env or pass directly
pool = LegendsPool()  # reads GROQ_API_KEY from env

# ─── Choose your committee ─────────────────────────────────────────────────────

# Starter: Warren Buffett, Charlie Munger, Michael Burry
result = pool.analyze(["NVDA", "TSLA"], package="starter")

# Pro: 10 legends
# result = pool.analyze(["NVDA", "TSLA"], package="pro")

# All-Stars: All 18 legends
# result = pool.analyze(["NVDA", "TSLA"], package="allstars")

# Custom committee:
# result = pool.analyze(["NVDA"], analysts=["warren_buffett", "michael_burry", "cathie_wood"])

# ─── Results ──────────────────────────────────────────────────────────────────
print(result.summary())
print(f"\nConsensus: {result.consensus}")
print(f"Confidence: {result.confidence:.0%}")
print(f"BUY: {result.buy_count} | HOLD: {result.hold_count} | SELL: {result.sell_count}")
