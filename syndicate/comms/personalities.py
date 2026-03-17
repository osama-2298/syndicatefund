"""Agent personality map — maps every agent/manager/executive to a human identity."""

AGENT_PERSONALITIES: dict[str, dict[str, str]] = {
    # ── Technical Team ──
    "TechnicalTrendAgent": {
        "name": "Lena Karlsson",
        "team": "technical",
        "title": "Trend Analyst (1D)",
    },
    "TechnicalSignalAgent": {
        "name": "David Osei",
        "team": "technical",
        "title": "Signal Analyst (4H)",
    },
    "TechnicalTimingAgent": {
        "name": "Mika Tanaka",
        "team": "technical",
        "title": "Timing Analyst (1H)",
    },
    # ── Sentiment Team ──
    "SocialSentimentAgent": {
        "name": "Priya Sharma",
        "team": "sentiment",
        "title": "Social Sentiment Analyst",
    },
    "MarketSentimentAgent": {
        "name": "Alexei Volkov",
        "team": "sentiment",
        "title": "Market Sentiment Analyst",
    },
    "SmartMoneySentimentAgent": {
        "name": "Sofia Reyes",
        "team": "sentiment",
        "title": "Smart Money Analyst",
    },
    # ── Fundamental Team ──
    "ValuationAgent": {
        "name": "Henrik Larsen",
        "team": "fundamental",
        "title": "Valuation Analyst",
    },
    "CyclePositionAgent": {
        "name": "Amara Obi",
        "team": "fundamental",
        "title": "Cycle Position Analyst",
    },
    # ── Macro Team ──
    "CryptoMacroAgent": {
        "name": "Lucas Weber",
        "team": "macro",
        "title": "Crypto Macro Analyst",
    },
    "ExternalMacroAgent": {
        "name": "Fatima Al-Rashid",
        "team": "macro",
        "title": "External Macro Analyst",
    },
    # ── On-Chain Team ──
    "NetworkHealthAgent": {
        "name": "Jin Park",
        "team": "onchain",
        "title": "Network Health Analyst",
    },
    "CapitalFlowAgent": {
        "name": "Camille Dubois",
        "team": "onchain",
        "title": "Capital Flow Analyst",
    },
    # ── Managers ──
    "manager_technical": {
        "name": "Oscar Brennan",
        "team": "technical",
        "title": "Technical Team Manager",
    },
    "manager_sentiment": {
        "name": "Yara Haddad",
        "team": "sentiment",
        "title": "Sentiment Team Manager",
    },
    "manager_fundamental": {
        "name": "Isaac Thornton",
        "team": "fundamental",
        "title": "Fundamental Team Manager",
    },
    "manager_macro": {
        "name": "Zara Kimathi",
        "team": "macro",
        "title": "Macro Team Manager",
    },
    "manager_onchain": {
        "name": "Nikolai Petrov",
        "team": "onchain",
        "title": "On-Chain Team Manager",
    },
    # ── Executives ──
    "CEO": {
        "name": "Marcus Blackwell",
        "team": None,
        "title": "Chief Executive Officer",
    },
    "COO": {
        "name": "Elena Vasquez",
        "team": None,
        "title": "Chief Operating Officer",
    },
    "CRO": {
        "name": "Tobias Richter",
        "team": None,
        "title": "Chief Risk Officer",
    },
}


# Team-name to manager key mapping
TEAM_MANAGER_MAP = {
    "technical": "manager_technical",
    "sentiment": "manager_sentiment",
    "fundamental": "manager_fundamental",
    "macro": "manager_macro",
    "onchain": "manager_onchain",
    "on-chain": "manager_onchain",
}


def get_personality(agent_class: str) -> dict[str, str]:
    """Get personality for an agent class, with fallback."""
    return AGENT_PERSONALITIES.get(agent_class, {
        "name": agent_class,
        "team": None,
        "title": agent_class,
    })
