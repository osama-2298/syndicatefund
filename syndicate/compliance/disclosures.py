"""Regulatory disclosure text for the Syndicate platform.

Each function returns a structured dict with ``title`` and ``body`` keys
so frontends can render headings and content independently.  All text is
kept in code (rather than a CMS) to ensure version-control and auditability.
"""

from __future__ import annotations

from typing import TypedDict


class Disclosure(TypedDict):
    title: str
    body: str


# ── Public API ───────────────────────────────────────────────────────────────


def risk_disclosure() -> Disclosure:
    """Comprehensive risk warnings for investors."""
    return {
        "title": "Risk Disclosure Statement",
        "body": (
            "IMPORTANT: Trading and investing in securities, cryptocurrencies, "
            "and other financial instruments involves substantial risk of loss "
            "and is not suitable for every investor. The value of your investments "
            "can go down as well as up, and you may lose some or all of your "
            "original investment.\n\n"
            "Key risks include but are not limited to:\n\n"
            "1. MARKET RISK — Prices of financial instruments can be highly "
            "volatile and are influenced by, among other things, government "
            "trade, fiscal, monetary, and exchange-control programs and policies; "
            "changing supply and demand relationships; national and international "
            "political and economic events; and changes in interest rates.\n\n"
            "2. LIQUIDITY RISK — Under certain market conditions, you may find it "
            "difficult or impossible to liquidate a position. This can occur, for "
            "example, when the market makes a limit move.\n\n"
            "3. TECHNOLOGY RISK — Algorithmic and AI-driven trading systems may "
            "experience technical failures, connectivity issues, software bugs, "
            "or erroneous signals that could result in unintended trades or "
            "inability to execute trades.\n\n"
            "4. MODEL RISK — Quantitative models and AI systems are based on "
            "historical data and assumptions that may not hold in the future. "
            "Past model performance does not guarantee future results.\n\n"
            "5. LEVERAGE RISK — If applicable, the use of leverage can magnify "
            "both gains and losses. You may sustain losses in excess of your "
            "initial deposit.\n\n"
            "6. CRYPTOCURRENCY-SPECIFIC RISK — Digital assets are subject to "
            "unique risks including but not limited to: regulatory uncertainty, "
            "cybersecurity threats, irreversibility of transactions, and the "
            "potential for total loss of value.\n\n"
            "You should carefully consider whether trading or investing is "
            "appropriate for you in light of your experience, objectives, "
            "financial resources, and other relevant circumstances. Seek "
            "independent professional advice if necessary."
        ),
    }


def past_performance_disclaimer() -> Disclosure:
    """Standard past-performance warning."""
    return {
        "title": "Past Performance Disclaimer",
        "body": (
            "PAST PERFORMANCE IS NOT INDICATIVE OF FUTURE RESULTS. Any "
            "historical returns, expected returns, or probability projections "
            "presented on this platform are provided for informational and "
            "illustrative purposes only. They do not reflect actual trading "
            "and may not reflect the impact of material economic and market "
            "factors.\n\n"
            "Actual results will vary. All investments and trading activities "
            "involve risk, and nothing herein should be interpreted as a "
            "guarantee of any specific outcome or profit. Hypothetical or "
            "back-tested performance results have inherent limitations: they "
            "are generally prepared with the benefit of hindsight, do not "
            "reflect actual trading, and cannot account for all factors "
            "associated with risk, including the impact of financial risk "
            "in actual trading.\n\n"
            "No representation is being made that any account will or is "
            "likely to achieve profits or losses similar to those shown. "
            "There are frequently sharp differences between hypothetical "
            "performance results and the actual results achieved."
        ),
    }


def ai_trading_disclosure() -> Disclosure:
    """Disclosure specific to AI/algorithmic trading operations."""
    return {
        "title": "AI and Algorithmic Trading Disclosure",
        "body": (
            "This platform utilizes artificial intelligence (AI) and "
            "algorithmic systems to generate trading signals, analyze market "
            "data, and in some cases execute trades. You should be aware of "
            "the following:\n\n"
            "1. AI-generated trading signals and decisions are produced by "
            "machine learning models and large language models (LLMs). These "
            "systems can and do make errors. No AI system is infallible.\n\n"
            "2. The AI agents operating on this platform may interpret market "
            "conditions differently than a human analyst would. Their reasoning "
            "processes, while transparent where possible, may not always align "
            "with conventional financial analysis.\n\n"
            "3. AI models are trained on historical data and may not adapt "
            "quickly to unprecedented market conditions, structural breaks, "
            "or black-swan events.\n\n"
            "4. Multiple AI agents may contribute to a single trading decision. "
            "The aggregation and weighting of these inputs involves additional "
            "layers of algorithmic processing.\n\n"
            "5. All AI-generated signals are subject to automated risk controls, "
            "including position sizing limits, portfolio heat constraints, "
            "drawdown ladders, and correlation checks. However, these controls "
            "cannot eliminate all risk.\n\n"
            "6. The platform includes a human-accessible emergency halt "
            "mechanism. In the event of system malfunction, trading can be "
            "stopped immediately.\n\n"
            "By using this platform, you acknowledge that AI-driven trading "
            "involves unique risks and that you have read and understand this "
            "disclosure."
        ),
    }


def not_fdic_insured() -> Disclosure:
    """FDIC / SIPC non-coverage notice."""
    return {
        "title": "Not FDIC Insured",
        "body": (
            "Investments made through this platform are NOT insured by the "
            "Federal Deposit Insurance Corporation (FDIC), the Securities "
            "Investor Protection Corporation (SIPC), or any other government "
            "agency. Investments are NOT deposits or obligations of, or "
            "guaranteed by, any bank or financial institution.\n\n"
            "Cryptocurrency and digital asset holdings are not protected by "
            "FDIC or SIPC insurance under any circumstances. You bear the "
            "full risk of loss for all funds deposited or invested through "
            "this platform."
        ),
    }


def conflict_of_interest() -> Disclosure:
    """Conflict of interest policy summary."""
    return {
        "title": "Conflict of Interest Disclosure",
        "body": (
            "Syndicate Fund and its affiliates, officers, directors, "
            "employees, and AI agents may have interests that conflict with "
            "yours. Potential conflicts include but are not limited to:\n\n"
            "1. PROPRIETARY TRADING — The platform or its affiliates may "
            "trade in the same securities or assets that are the subject of "
            "signals or recommendations provided to users.\n\n"
            "2. FEE STRUCTURES — Performance fees and management fees may "
            "create incentives that are not perfectly aligned with your "
            "investment objectives.\n\n"
            "3. AI AGENT INCENTIVES — AI agents within the system are "
            "evaluated and ranked based on performance metrics. This "
            "incentive structure could theoretically encourage risk-taking "
            "beyond what is optimal for all participants.\n\n"
            "4. DATA PROVIDERS — The platform relies on third-party data "
            "providers. Relationships with these providers do not influence "
            "trading decisions, but you should be aware they exist.\n\n"
            "We maintain policies and procedures designed to identify, "
            "manage, and mitigate conflicts of interest. Our surveillance "
            "systems monitor for front-running, wash trading, and other "
            "forms of market abuse. If you have concerns about a potential "
            "conflict, please contact our compliance team."
        ),
    }


def best_execution_policy() -> Disclosure:
    """Best execution policy summary."""
    return {
        "title": "Best Execution Policy",
        "body": (
            "Syndicate Fund is committed to achieving the best possible "
            "result for its participants when executing orders. Our best "
            "execution policy considers the following factors:\n\n"
            "1. PRICE — We seek to obtain the most favorable price available "
            "at the time of execution, accounting for the size and nature "
            "of the order.\n\n"
            "2. COST — Total cost of execution includes explicit costs "
            "(commissions, fees, taxes) and implicit costs (spread, market "
            "impact, opportunity cost).\n\n"
            "3. SPEED — Orders are routed and executed promptly to minimize "
            "slippage between signal generation and trade completion.\n\n"
            "4. LIKELIHOOD OF EXECUTION AND SETTLEMENT — We prioritize "
            "venues and counterparties with high reliability and settlement "
            "certainty.\n\n"
            "5. VENUE SELECTION — The platform may route orders to multiple "
            "exchanges or liquidity providers. Venue selection is based on "
            "liquidity, reliability, and cost — not on payment-for-order-flow "
            "or other conflicted incentives.\n\n"
            "6. MONITORING — Execution quality is monitored continuously. "
            "Slippage, fill rates, and venue performance are tracked and "
            "reviewed regularly.\n\n"
            "This policy is reviewed at least annually and updated as "
            "market conditions and available venues change."
        ),
    }


def privacy_policy_summary() -> Disclosure:
    """Privacy policy summary."""
    return {
        "title": "Privacy Policy Summary",
        "body": (
            "Syndicate Fund is committed to protecting your personal "
            "information. This summary outlines how we collect, use, and "
            "safeguard your data.\n\n"
            "INFORMATION WE COLLECT:\n"
            "- Identity information (name, date of birth, government ID) "
            "for KYC/AML compliance\n"
            "- Contact information (email, phone number)\n"
            "- Financial information (income, net worth) for accredited "
            "investor verification\n"
            "- Trading activity and portfolio data\n"
            "- Device and usage data (IP address, browser type, access logs)\n\n"
            "HOW WE USE YOUR INFORMATION:\n"
            "- To provide and improve our services\n"
            "- To comply with legal and regulatory obligations (KYC, AML, "
            "tax reporting)\n"
            "- To detect and prevent fraud and market abuse\n"
            "- To communicate with you about your account\n\n"
            "DATA PROTECTION:\n"
            "- All sensitive data is encrypted at rest and in transit\n"
            "- Access controls follow the principle of least privilege\n"
            "- We conduct regular security assessments and penetration tests\n"
            "- We do not sell your personal information to third parties\n\n"
            "DATA RETENTION:\n"
            "- Account data is retained for the duration of your account "
            "and for a period thereafter as required by applicable regulations\n"
            "- Audit logs are retained for a minimum of 7 years per "
            "regulatory requirements\n"
            "- You may request deletion of your data subject to regulatory "
            "retention obligations\n\n"
            "For the full privacy policy or to exercise your data rights, "
            "please contact our data protection officer."
        ),
    }


def terms_of_service_summary() -> Disclosure:
    """Terms of service summary."""
    return {
        "title": "Terms of Service Summary",
        "body": (
            "By using the Syndicate Fund platform, you agree to the "
            "following terms. This is a summary; the full terms of service "
            "govern your use of the platform.\n\n"
            "ELIGIBILITY:\n"
            "- You must be at least 18 years of age\n"
            "- You must not be located in a jurisdiction where use of the "
            "platform is prohibited\n"
            "- You must complete all required KYC/AML verification\n\n"
            "YOUR RESPONSIBILITIES:\n"
            "- Provide accurate and complete information\n"
            "- Maintain the security of your account credentials\n"
            "- Comply with all applicable laws and regulations\n"
            "- Report any suspected unauthorized account activity promptly\n\n"
            "PLATFORM LIMITATIONS:\n"
            "- The platform is provided on an \"as is\" basis\n"
            "- We do not guarantee uninterrupted access or error-free "
            "operation\n"
            "- Trading signals and AI-generated content are informational "
            "and do not constitute financial advice\n"
            "- We reserve the right to halt trading, restrict access, or "
            "modify services at any time for risk management or compliance "
            "reasons\n\n"
            "FEES AND CHARGES:\n"
            "- All applicable fees are disclosed before you commit to any "
            "transaction\n"
            "- Fee schedules may be updated with prior notice\n\n"
            "DISPUTE RESOLUTION:\n"
            "- Disputes will be resolved through binding arbitration as "
            "outlined in the full terms of service\n"
            "- Class action waiver applies\n\n"
            "TERMINATION:\n"
            "- Either party may terminate the relationship with notice\n"
            "- Upon termination, open positions will be closed in an "
            "orderly manner\n"
            "- Regulatory reporting obligations survive termination\n\n"
            "For the complete terms of service, please refer to the legal "
            "section of our website."
        ),
    }


# ── Utility ─────────────────────────────────────────────────────────────────


def all_disclosures() -> list[Disclosure]:
    """Return every standard disclosure in presentation order."""
    return [
        risk_disclosure(),
        past_performance_disclaimer(),
        ai_trading_disclosure(),
        not_fdic_insured(),
        conflict_of_interest(),
        best_execution_policy(),
        privacy_policy_summary(),
        terms_of_service_summary(),
    ]
