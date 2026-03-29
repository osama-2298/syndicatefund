"""KYC / AML framework for the Syndicate compliance layer.

Provides investor classification, accredited-investor verification,
sanctions screening, geographic restrictions, and PEP flagging.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


# ── Enums ────────────────────────────────────────────────────────────────────


class InvestorType(str, PyEnum):
    RETAIL = "retail"
    ACCREDITED = "accredited"
    INSTITUTIONAL = "institutional"


class VerificationStatus(str, PyEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RiskRating(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


# ── Pydantic models ─────────────────────────────────────────────────────────


class KYCProfile(BaseModel):
    """Identity and compliance profile for an investor."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investor_type: InvestorType = InvestorType.RETAIL
    full_name: str
    email: str | None = None
    date_of_birth: str | None = None
    nationality: str | None = None
    jurisdiction: str = Field(
        ..., description="Two-letter ISO 3166-1 country code of residence"
    )
    verified: bool = False
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verification_date: str | None = None
    sanctions_checked: bool = False
    sanctions_check_date: str | None = None
    pep_flagged: bool = False
    risk_rating: RiskRating = RiskRating.MEDIUM
    accreditation_evidence: dict[str, Any] | None = None
    notes: str | None = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str | None = None


class AccreditedInvestorEvidence(BaseModel):
    """Evidence submitted for accredited-investor verification (SEC Rule 501)."""

    annual_income: Decimal | None = None
    annual_income_joint: Decimal | None = None
    net_worth_excluding_primary_residence: Decimal | None = None
    professional_certifications: list[str] = Field(default_factory=list)
    entity_assets: Decimal | None = None
    is_knowledgeable_employee: bool = False


# ── Accredited Investor Check ───────────────────────────────────────────────


class AccreditedInvestorCheck:
    """Determines whether an individual or entity qualifies as accredited
    under SEC Regulation D, Rule 501 thresholds.

    Thresholds (2024):
      - Individual income >= $200,000 in each of last two years (or $300,000 joint)
      - Net worth (excl. primary residence) >= $1,000,000
      - Certain professional certifications (Series 7, 65, 82)
      - Entity with assets >= $5,000,000
    """

    INDIVIDUAL_INCOME_THRESHOLD = Decimal("200_000")
    JOINT_INCOME_THRESHOLD = Decimal("300_000")
    NET_WORTH_THRESHOLD = Decimal("1_000_000")
    ENTITY_ASSET_THRESHOLD = Decimal("5_000_000")
    QUALIFYING_CERTIFICATIONS = {"series_7", "series_65", "series_82", "cfa"}

    def evaluate(self, evidence: AccreditedInvestorEvidence) -> tuple[bool, str]:
        """Return (qualified: bool, reason: str)."""
        # Income test — individual
        if (
            evidence.annual_income is not None
            and evidence.annual_income >= self.INDIVIDUAL_INCOME_THRESHOLD
        ):
            return True, (
                f"Individual income ${evidence.annual_income:,.0f} meets "
                f"${self.INDIVIDUAL_INCOME_THRESHOLD:,.0f} threshold"
            )

        # Income test — joint
        if (
            evidence.annual_income_joint is not None
            and evidence.annual_income_joint >= self.JOINT_INCOME_THRESHOLD
        ):
            return True, (
                f"Joint income ${evidence.annual_income_joint:,.0f} meets "
                f"${self.JOINT_INCOME_THRESHOLD:,.0f} threshold"
            )

        # Net worth test
        if (
            evidence.net_worth_excluding_primary_residence is not None
            and evidence.net_worth_excluding_primary_residence >= self.NET_WORTH_THRESHOLD
        ):
            return True, (
                f"Net worth ${evidence.net_worth_excluding_primary_residence:,.0f} "
                f"meets ${self.NET_WORTH_THRESHOLD:,.0f} threshold"
            )

        # Professional certification test
        certs = {c.lower() for c in evidence.professional_certifications}
        qualifying = certs & self.QUALIFYING_CERTIFICATIONS
        if qualifying:
            return True, f"Holds qualifying certification(s): {', '.join(qualifying)}"

        # Knowledgeable employee test
        if evidence.is_knowledgeable_employee:
            return True, "Qualified as knowledgeable employee of private fund"

        # Entity asset test
        if (
            evidence.entity_assets is not None
            and evidence.entity_assets >= self.ENTITY_ASSET_THRESHOLD
        ):
            return True, (
                f"Entity assets ${evidence.entity_assets:,.0f} meet "
                f"${self.ENTITY_ASSET_THRESHOLD:,.0f} threshold"
            )

        return False, "Does not meet any accredited investor qualification criteria"


# ── Sanctions Screener ──────────────────────────────────────────────────────


class SanctionsScreener:
    """Screens individuals and entities against sanctions lists.

    In production, this would call an external API (e.g., OFAC SDN,
    EU consolidated list, UN sanctions).  This implementation provides the
    interface and a placeholder local check.
    """

    # Placeholder — in production, populated from OFAC SDN feed
    _BLOCKED_JURISDICTIONS: set[str] = {
        "KP",  # North Korea
        "IR",  # Iran
        "SY",  # Syria
        "CU",  # Cuba
        "RU",  # Russia (partial — depends on scope)
    }

    def __init__(self, additional_blocked: set[str] | None = None):
        self._blocked = self._BLOCKED_JURISDICTIONS.copy()
        if additional_blocked:
            self._blocked |= additional_blocked

    def screen_individual(
        self, full_name: str, jurisdiction: str, date_of_birth: str | None = None
    ) -> tuple[bool, str]:
        """Return (clear: bool, detail: str).

        ``clear=True`` means no match found; ``clear=False`` means flagged.
        """
        # Jurisdiction check
        if jurisdiction.upper() in self._blocked:
            logger.warning(
                "sanctions_jurisdiction_hit",
                name=full_name,
                jurisdiction=jurisdiction,
            )
            return False, (
                f"Jurisdiction {jurisdiction} is on the blocked list. "
                "Manual review required before onboarding."
            )

        # Name-based screening placeholder — in production, call external API
        logger.info(
            "sanctions_screen_clear",
            name=full_name,
            jurisdiction=jurisdiction,
        )
        return True, "No sanctions match found (automated pre-screen)"

    def screen_entity(
        self, entity_name: str, jurisdiction: str, registration_number: str | None = None
    ) -> tuple[bool, str]:
        """Screen a legal entity against sanctions lists."""
        if jurisdiction.upper() in self._blocked:
            logger.warning(
                "sanctions_entity_jurisdiction_hit",
                entity=entity_name,
                jurisdiction=jurisdiction,
            )
            return False, (
                f"Entity jurisdiction {jurisdiction} is on the blocked list."
            )

        logger.info(
            "sanctions_entity_screen_clear",
            entity=entity_name,
            jurisdiction=jurisdiction,
        )
        return True, "No sanctions match found for entity (automated pre-screen)"


# ── Geographic Restrictions ─────────────────────────────────────────────────


class GeographicRestrictionChecker:
    """Enforces jurisdictional eligibility rules.

    Different product tiers may be restricted in certain jurisdictions.
    """

    # Jurisdictions where the platform is entirely unavailable
    FULLY_RESTRICTED: set[str] = {"KP", "IR", "SY", "CU"}

    # Jurisdictions requiring additional compliance steps
    ENHANCED_DUE_DILIGENCE: set[str] = {"CN", "RU", "VE", "MM", "BY"}

    # US states with specific requirements (placeholder)
    US_RESTRICTED_STATES: set[str] = {"NY"}  # BitLicense requirement example

    def check(
        self,
        jurisdiction: str,
        us_state: str | None = None,
    ) -> tuple[bool, str, RiskRating]:
        """Return (allowed: bool, reason: str, risk_rating: RiskRating)."""
        code = jurisdiction.upper()

        if code in self.FULLY_RESTRICTED:
            return (
                False,
                f"Jurisdiction {code} is fully restricted. Service unavailable.",
                RiskRating.PROHIBITED,
            )

        if code in self.ENHANCED_DUE_DILIGENCE:
            return (
                True,
                f"Jurisdiction {code} requires enhanced due diligence.",
                RiskRating.HIGH,
            )

        if code == "US" and us_state:
            if us_state.upper() in self.US_RESTRICTED_STATES:
                return (
                    False,
                    f"US state {us_state} has additional licensing requirements "
                    "that are not yet met.",
                    RiskRating.PROHIBITED,
                )

        return True, f"Jurisdiction {code} is eligible.", RiskRating.LOW


# ── PEP Flagging ────────────────────────────────────────────────────────────


class PEPScreener:
    """Politically Exposed Person detection.

    In production, integrates with a PEP database provider (e.g.,
    Dow Jones, Refinitiv World-Check).  This implementation provides the
    interface and a placeholder.
    """

    def screen(
        self,
        full_name: str,
        nationality: str | None = None,
        date_of_birth: str | None = None,
    ) -> tuple[bool, str]:
        """Return (is_pep: bool, detail: str).

        A ``True`` result does NOT automatically disqualify — it triggers
        enhanced due diligence.
        """
        # Placeholder — in production, call external PEP database API
        logger.info(
            "pep_screen_executed",
            name=full_name,
            nationality=nationality,
        )
        return False, "No PEP match found (automated pre-screen)"


# ── Orchestrator ────────────────────────────────────────────────────────────


class KYCOrchestrator:
    """Runs the full KYC/AML onboarding workflow for a profile."""

    def __init__(self):
        self.accredited_check = AccreditedInvestorCheck()
        self.sanctions_screener = SanctionsScreener()
        self.geo_checker = GeographicRestrictionChecker()
        self.pep_screener = PEPScreener()

    def run_onboarding(
        self,
        profile: KYCProfile,
        accreditation_evidence: AccreditedInvestorEvidence | None = None,
        us_state: str | None = None,
    ) -> tuple[KYCProfile, list[str]]:
        """Execute all checks and return updated profile + list of issues.

        An empty issues list means the profile passed all checks.
        """
        issues: list[str] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Geographic eligibility
        geo_ok, geo_reason, risk_rating = self.geo_checker.check(
            profile.jurisdiction, us_state=us_state
        )
        profile = profile.model_copy(update={"risk_rating": risk_rating})
        if not geo_ok:
            issues.append(f"GEO: {geo_reason}")
            profile = profile.model_copy(
                update={
                    "verification_status": VerificationStatus.REJECTED,
                    "updated_at": now_iso,
                }
            )
            logger.warning("kyc_geo_rejected", profile_id=profile.id, reason=geo_reason)
            return profile, issues

        # 2. Sanctions screening
        sanctions_clear, sanctions_detail = self.sanctions_screener.screen_individual(
            full_name=profile.full_name,
            jurisdiction=profile.jurisdiction,
            date_of_birth=profile.date_of_birth,
        )
        profile = profile.model_copy(
            update={
                "sanctions_checked": True,
                "sanctions_check_date": now_iso,
            }
        )
        if not sanctions_clear:
            issues.append(f"SANCTIONS: {sanctions_detail}")
            profile = profile.model_copy(
                update={
                    "verification_status": VerificationStatus.REJECTED,
                    "updated_at": now_iso,
                }
            )
            logger.warning("kyc_sanctions_hit", profile_id=profile.id)
            return profile, issues

        # 3. PEP screening
        is_pep, pep_detail = self.pep_screener.screen(
            full_name=profile.full_name,
            nationality=profile.nationality,
            date_of_birth=profile.date_of_birth,
        )
        if is_pep:
            profile = profile.model_copy(
                update={
                    "pep_flagged": True,
                    "risk_rating": RiskRating.HIGH,
                }
            )
            issues.append(f"PEP: {pep_detail} — enhanced due diligence required")

        # 4. Accredited investor check (if evidence provided)
        if accreditation_evidence is not None:
            qualified, reason = self.accredited_check.evaluate(accreditation_evidence)
            if qualified:
                profile = profile.model_copy(
                    update={
                        "investor_type": InvestorType.ACCREDITED,
                        "accreditation_evidence": accreditation_evidence.model_dump(),
                    }
                )
            else:
                issues.append(f"ACCREDITATION: {reason}")

        # 5. Final status
        if not any(issue.startswith("SANCTIONS:") for issue in issues):
            profile = profile.model_copy(
                update={
                    "verified": True,
                    "verification_status": VerificationStatus.VERIFIED,
                    "verification_date": now_iso,
                    "updated_at": now_iso,
                }
            )
            logger.info("kyc_verified", profile_id=profile.id, investor_type=profile.investor_type)
        else:
            profile = profile.model_copy(
                update={
                    "verification_status": VerificationStatus.REJECTED,
                    "updated_at": now_iso,
                }
            )

        return profile, issues
