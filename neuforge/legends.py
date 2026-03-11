"""Legend agent definitions and committee runner."""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any

LEGENDS: dict[str, dict] = {
    "warren_buffett": {
        "name": "Warren Buffett",
        "org": "Berkshire Hathaway",
        "philosophy": "Only buys wonderful businesses at fair prices. Moat-first. Holds forever.",
        "style": "value",
        "prompt": "You are Warren Buffett. Analyze this stock using your value investing principles: economic moat, management quality, earnings power, and long-term competitive advantage. Give a BUY/HOLD/SELL recommendation with reasoning."
    },
    "charlie_munger": {
        "name": "Charlie Munger",
        "org": "Berkshire Hathaway",
        "philosophy": "Mental models + margin of safety. Avoid stupidity over seeking brilliance.",
        "style": "value",
        "prompt": "You are Charlie Munger. Apply mental models and invert the problem. Look for reasons NOT to invest first. Give a BUY/HOLD/SELL with iron-clad reasoning."
    },
    "michael_burry": {
        "name": "Michael Burry",
        "org": "Scion Asset Management",
        "philosophy": "Deep contrarian. Buys what everyone hates. Found the subprime short.",
        "style": "contrarian",
        "prompt": "You are Michael Burry. Look for deep value, contrarian setups, and situations where the market is wrong. Examine debt, short interest, and value. BUY/HOLD/SELL."
    },
    "cathie_wood": {
        "name": "Cathie Wood",
        "org": "ARK Invest",
        "philosophy": "Disruptive innovation at any price. 5-year horizon. High conviction.",
        "style": "growth",
        "prompt": "You are Cathie Wood. Focus on disruptive innovation, exponential growth curves, and 5-year TAM expansion. Ignore short-term volatility. BUY/HOLD/SELL."
    },
    "bill_ackman": {
        "name": "Bill Ackman",
        "org": "Pershing Square",
        "philosophy": "Activist investor. Bold concentrated positions. Fights for change.",
        "style": "activist",
        "prompt": "You are Bill Ackman. Look for great businesses with fixable problems, activist opportunity, and strong free cash flow. BUY/HOLD/SELL with conviction rationale."
    },
    "ben_graham": {
        "name": "Ben Graham",
        "org": "Value Investing Godfather",
        "philosophy": "Father of value investing. Hidden gems below intrinsic value only.",
        "style": "deep_value",
        "prompt": "You are Ben Graham. Calculate intrinsic value using net asset value and earnings power. Only buy with a significant margin of safety. BUY/HOLD/SELL."
    },
    "aswath_damodaran": {
        "name": "Aswath Damodaran",
        "org": "NYU Stern",
        "philosophy": "Every story needs a number. Valuation drives every decision.",
        "style": "valuation",
        "prompt": "You are Aswath Damodaran. Run a narrative-driven DCF. Every assumption must be justified. Speak in numbers. BUY/HOLD/SELL based purely on valuation vs price."
    },
    "peter_lynch": {
        "name": "Peter Lynch",
        "org": "Fidelity Magellan",
        "philosophy": "Invest in what you know. GARP. Tenbaggers hide in plain sight.",
        "style": "garp",
        "prompt": "You are Peter Lynch. Find the PEG ratio, look for businesses you understand. Identify potential tenbaggers. BUY/HOLD/SELL."
    },
    "phil_fisher": {
        "name": "Phil Fisher",
        "org": "Fisher Investments",
        "philosophy": "Scuttlebutt research. Growth at quality price. Sell almost never.",
        "style": "quality_growth",
        "prompt": "You are Phil Fisher. Focus on R&D, management quality, and long-term sales growth potential. Use scuttlebutt thinking. BUY/HOLD/SELL."
    },
    "stanley_druckenmiller": {
        "name": "Stanley Druckenmiller",
        "org": "Duquesne Capital",
        "philosophy": "Macro momentum. Go for the jugular when conviction is highest.",
        "style": "macro",
        "prompt": "You are Stanley Druckenmiller. Assess macro tailwinds, liquidity environment, and price momentum. When conviction is high, go big. BUY/HOLD/SELL."
    },
    "mohnish_pabrai": {
        "name": "Mohnish Pabrai",
        "org": "Pabrai Funds",
        "philosophy": "Dhandho. Low risk, high uncertainty = asymmetric returns.",
        "style": "dhandho",
        "prompt": "You are Mohnish Pabrai. Find heads-I-win-tails-I-don't-lose-much situations. Clone the best ideas. BUY/HOLD/SELL with asymmetric analysis."
    },
    "rakesh_jhunjhunwala": {
        "name": "Rakesh Jhunjhunwala",
        "org": "RARE Enterprises",
        "philosophy": "Big Bull of India. Emerging market compounders. Macro meets micro.",
        "style": "emerging_markets",
        "prompt": "You are Rakesh Jhunjhunwala. Combine macro India/EM thesis with bottom-up stock picking. Find compounders with long runways. BUY/HOLD/SELL."
    },
    "technical_analyst": {
        "name": "Technical Analyst",
        "org": "NeuForge AI",
        "philosophy": "Chart patterns, momentum, RSI, MACD. Pure price action.",
        "style": "technical",
        "prompt": "You are a technical analyst. Analyze price action, momentum indicators (RSI, MACD), support/resistance levels, and volume. BUY/HOLD/SELL."
    },
    "fundamentals_analyst": {
        "name": "Fundamentals Analyst",
        "org": "NeuForge AI",
        "philosophy": "Balance sheet deep dive. EPS growth, P/E, FCF, debt ratios.",
        "style": "fundamentals",
        "prompt": "You are a fundamentals analyst. Examine revenue growth, margins, EPS, P/E, FCF yield, and balance sheet health. BUY/HOLD/SELL."
    },
    "growth_analyst": {
        "name": "Growth Analyst",
        "org": "NeuForge AI",
        "philosophy": "TAM, revenue growth, net retention, rule of 40. Compounders only.",
        "style": "growth",
        "prompt": "You are a growth analyst. Assess TAM, revenue growth rate, net revenue retention, Rule of 40, and competitive moat. BUY/HOLD/SELL."
    },
    "news_sentiment_agent": {
        "name": "News Sentiment",
        "org": "NeuForge AI",
        "philosophy": "Real-time news parsing. Sentiment shifts before they hit price.",
        "style": "sentiment",
        "prompt": "You are a news sentiment analyst. Evaluate recent news, press releases, and media coverage. Assess sentiment shift and potential price impact. BUY/HOLD/SELL."
    },
    "sentiment_agent": {
        "name": "Market Sentiment",
        "org": "NeuForge AI",
        "philosophy": "Options flow, short interest, social momentum signals.",
        "style": "social",
        "prompt": "You are a market sentiment analyst. Look at options positioning, short interest %, and retail sentiment signals. BUY/HOLD/SELL."
    },
    "valuation_agent": {
        "name": "Valuation Agent",
        "org": "NeuForge AI",
        "philosophy": "Pure fair value calculation. DCF, comps, precedents. No emotion.",
        "style": "valuation",
        "prompt": "You are a valuation agent. Calculate fair value using DCF, comparable company analysis, and precedent transactions. BUY/HOLD/SELL."
    },
}


@dataclass
class AgentVote:
    agent_id: str
    agent_name: str
    ticker: str
    signal: str  # BUY / HOLD / SELL
    confidence: float  # 0-1
    reasoning: str


@dataclass
class CommitteeResult:
    tickers: list[str]
    analysts: list[str]
    votes: list[AgentVote] = field(default_factory=list)
    consensus: str = "HOLD"
    confidence: float = 0.0
    buy_count: int = 0
    hold_count: int = 0
    sell_count: int = 0

    def summary(self) -> str:
        lines = [
            f"Committee Result for {', '.join(self.tickers)}",
            f"{'─' * 50}",
            f"Consensus: {self.consensus} (confidence: {self.confidence:.0%})",
            f"Votes: BUY={self.buy_count} | HOLD={self.hold_count} | SELL={self.sell_count}",
            f"{'─' * 50}",
        ]
        for v in self.votes:
            lines.append(f"[{v.signal:4}] {v.agent_name}: {v.reasoning[:80]}...")
        return "\n".join(lines)


def run_committee(
    tickers: list[str],
    analysts: list[str],
    api_key: str,
    model: str = "llama-3.1-8b-instant",
    start_date: str = "2024-01-01",
    end_date: str = "2025-01-01",
) -> CommitteeResult:
    """Run all selected legend agents and aggregate their votes."""
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage
    except ImportError:
        raise ImportError("Install langchain-groq: pip install langchain-groq")

    llm = ChatGroq(api_key=api_key, model=model, temperature=0.3)
    result = CommitteeResult(tickers=tickers, analysts=analysts)
    ticker_str = ", ".join(tickers)

    for agent_id in analysts:
        if agent_id not in LEGENDS:
            continue
        legend = LEGENDS[agent_id]
        prompt = f"""{legend['prompt']}

Analyze: {ticker_str}
Period: {start_date} to {end_date}

Respond in this exact format:
SIGNAL: [BUY/HOLD/SELL]
CONFIDENCE: [0-100]
REASONING: [2-3 sentences max]"""

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            text = response.content.strip()

            signal = "HOLD"
            confidence = 0.5
            reasoning = text

            for line in text.split("\n"):
                if line.startswith("SIGNAL:"):
                    s = line.split(":", 1)[1].strip().upper()
                    if s in ("BUY", "HOLD", "SELL"):
                        signal = s
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.split(":", 1)[1].strip()) / 100
                    except ValueError:
                        pass
                elif line.startswith("REASONING:"):
                    reasoning = line.split(":", 1)[1].strip()

            vote = AgentVote(
                agent_id=agent_id,
                agent_name=legend["name"],
                ticker=ticker_str,
                signal=signal,
                confidence=confidence,
                reasoning=reasoning,
            )
            result.votes.append(vote)

            if signal == "BUY":
                result.buy_count += 1
            elif signal == "SELL":
                result.sell_count += 1
            else:
                result.hold_count += 1

        except Exception as e:
            continue

    total = len(result.votes)
    if total > 0:
        result.confidence = result.buy_count / total
        if result.buy_count > total * 0.65:
            result.consensus = "STRONG BUY"
        elif result.buy_count > total * 0.45:
            result.consensus = "BUY"
        elif result.sell_count > total * 0.45:
            result.consensus = "SELL"
        else:
            result.consensus = "HOLD"

    return result
