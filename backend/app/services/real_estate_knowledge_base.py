"""
Real Estate Knowledge Base and Domain Specialization.

This module provides comprehensive real estate domain knowledge,
including legal requirements, compliance rules, market data integration,
and industry-specific workflow automation.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


class PropertyType(Enum):
    """Types of real estate properties."""
    RESIDENTIAL_SINGLE_FAMILY = "residential_single_family"
    RESIDENTIAL_MULTI_FAMILY = "residential_multi_family"
    RESIDENTIAL_CONDO = "residential_condo"
    RESIDENTIAL_TOWNHOUSE = "residential_townhouse"
    COMMERCIAL_OFFICE = "commercial_office"
    COMMERCIAL_RETAIL = "commercial_retail"
    COMMERCIAL_INDUSTRIAL = "commercial_industrial"
    COMMERCIAL_WAREHOUSE = "commercial_warehouse"
    LAND_VACANT = "land_vacant"
    LAND_AGRICULTURAL = "land_agricultural"
    MIXED_USE = "mixed_use"


class TransactionType(Enum):
    """Types of real estate transactions."""
    PURCHASE = "purchase"
    SALE = "sale"
    LEASE = "lease"
    RENTAL = "rental"
    REFINANCE = "refinance"
    ASSIGNMENT = "assignment"
    OPTION = "option"


class Jurisdiction(Enum):
    """Supported jurisdictions."""
    US_FEDERAL = "us_federal"
    US_CALIFORNIA = "us_california"
    US_TEXAS = "us_texas"
    US_FLORIDA = "us_florida"
    US_NEW_YORK = "us_new_york"
    CANADA_FEDERAL = "canada_federal"
    CANADA_ONTARIO = "canada_ontario"
    CANADA_BC = "canada_bc"


@dataclass
class LegalRequirement:
    """Legal requirement for real estate transactions."""
    requirement_id: str
    jurisdiction: Jurisdiction
    property_type: PropertyType
    transaction_type: TransactionType
    title: str
    description: str
    mandatory: bool
    deadline_days: Optional[int] = None
    required_documents: List[str] = None
    penalties: str = ""
    references: List[str] = None


@dataclass
class ComplianceRule:
    """Compliance rule for real estate transactions."""
    rule_id: str
    jurisdiction: Jurisdiction
    category: str
    title: str
    description: str
    validation_criteria: Dict[str, Any]
    severity: str  # "error", "warning", "info"
    remediation_steps: List[str]


@dataclass
class DocumentTemplate:
    """Real estate document template."""
    template_id: str
    name: str
    description: str
    property_types: List[PropertyType]
    transaction_types: List[TransactionType]
    jurisdictions: List[Jurisdiction]
    required_fields: List[str]
    optional_fields: List[str]
    template_content: str
    version: str = "1.0"


@dataclass
class MarketData:
    """Market data for property valuation."""
    location: str
    property_type: PropertyType
    median_price: float
    price_per_sqft: float
    days_on_market: int
    inventory_level: str
    price_trend: str  # "increasing", "decreasing", "stable"
    last_updated: datetime


class RealEstateKnowledgeBase:
    """Comprehensive real estate knowledge base."""

    def __init__(self):
        self.legal_requirements: Dict[str, LegalRequirement] = {}
        self.compliance_rules: Dict[str, ComplianceRule] = {}
        self.document_templates: Dict[str, DocumentTemplate] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.clause_library: Dict[str, Dict[str, Any]] = {}

        # Initialize with default data
        self._initialize_legal_requirements()
        self._initialize_compliance_rules()
        self._initialize_document_templates()
        self._initialize_clause_library()
        self._initialize_sample_market_data()

    def get_legal_requirements(
        self,
        jurisdiction: Jurisdiction,
        property_type: PropertyType,
        transaction_type: TransactionType
    ) -> List[LegalRequirement]:
        """Get legal requirements for specific transaction parameters."""
        requirements = []

        for req in self.legal_requirements.values():
            if (req.jurisdiction == jurisdiction and
                req.property_type == property_type and
                req.transaction_type == transaction_type):
                requirements.append(req)

        # Sort by mandatory first, then by deadline
        requirements.sort(key=lambda x: (not x.mandatory, x.deadline_days or 999))
        return requirements

    def validate_compliance(
        self,
        jurisdiction: Jurisdiction,
        transaction_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate transaction compliance against rules."""
        violations = []

        for rule in self.compliance_rules.values():
            if rule.jurisdiction != jurisdiction:
                continue

            violation = self._check_compliance_rule(rule, transaction_data)
            if violation:
                violations.append(violation)

        return violations

    def get_document_templates(
        self,
        property_type: PropertyType,
        transaction_type: TransactionType,
        jurisdiction: Jurisdiction
    ) -> List[DocumentTemplate]:
        """Get applicable document templates."""
        templates = []

        for template in self.document_templates.values():
            if (property_type in template.property_types and
                transaction_type in template.transaction_types and
                jurisdiction in template.jurisdictions):
                templates.append(template)

        return templates

    def get_market_analysis(
        self,
        location: str,
        property_type: PropertyType
    ) -> Optional[Dict[str, Any]]:
        """Get market analysis for a location and property type."""
        key = f"{location}_{property_type.value}"

        if key not in self.market_data:
            return None

        data = self.market_data[key]

        return {
            "location": data.location,
            "property_type": data.property_type.value,
            "median_price": data.median_price,
            "price_per_sqft": data.price_per_sqft,
            "days_on_market": data.days_on_market,
            "inventory_level": data.inventory_level,
            "price_trend": data.price_trend,
            "last_updated": data.last_updated.isoformat(),
            "market_score": self._calculate_market_score(data)
        }

    def get_suggested_clauses(
        self,
        property_type: PropertyType,
        transaction_type: TransactionType,
        jurisdiction: Jurisdiction,
        risk_factors: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get suggested contract clauses."""
        suggested_clauses = []
        risk_factors = risk_factors or []

        # Base clauses for all transactions
        base_clauses = self.clause_library.get("base", {})
        for clause_id, clause in base_clauses.items():
            if self._is_clause_applicable(clause, property_type, transaction_type, jurisdiction):
                suggested_clauses.append({
                    "clause_id": clause_id,
                    "category": "base",
                    "priority": clause.get("priority", "normal"),
                    **clause
                })

        # Property-specific clauses
        property_clauses = self.clause_library.get(property_type.value, {})
        for clause_id, clause in property_clauses.items():
            suggested_clauses.append({
                "clause_id": clause_id,
                "category": property_type.value,
                "priority": clause.get("priority", "normal"),
                **clause
            })

        # Risk-specific clauses
        for risk_factor in risk_factors:
            risk_clauses = self.clause_library.get(f"risk_{risk_factor}", {})
            for clause_id, clause in risk_clauses.items():
                suggested_clauses.append({
                    "clause_id": clause_id,
                    "category": f"risk_{risk_factor}",
                    "priority": "high",
                    **clause
                })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        suggested_clauses.sort(key=lambda x: priority_order.get(x["priority"], 2))

        return suggested_clauses

    def estimate_property_value(
        self,
        location: str,
        property_type: PropertyType,
        square_footage: float,
        bedrooms: int = None,
        bathrooms: float = None,
        year_built: int = None,
        additional_features: List[str] = None
    ) -> Dict[str, Any]:
        """Estimate property value using market data."""
        market_data = self.get_market_analysis(location, property_type)

        if not market_data:
            return {"error": "Market data not available for this location"}

        base_value = market_data["price_per_sqft"] * square_footage

        # Adjustments
        adjustments = []
        adjustment_factor = 1.0

        # Age adjustment
        if year_built:
            current_year = datetime.now().year
            age = current_year - year_built
            if age < 5:
                adjustment_factor *= 1.05
                adjustments.append({"factor": "new_construction", "adjustment": 5})
            elif age > 30:
                adjustment_factor *= 0.95
                adjustments.append({"factor": "older_property", "adjustment": -5})

        # Market trend adjustment
        if market_data["price_trend"] == "increasing":
            adjustment_factor *= 1.02
            adjustments.append({"factor": "market_trend", "adjustment": 2})
        elif market_data["price_trend"] == "decreasing":
            adjustment_factor *= 0.98
            adjustments.append({"factor": "market_trend", "adjustment": -2})

        # Feature adjustments
        if additional_features:
            feature_values = {
                "pool": 0.03,
                "garage": 0.02,
                "fireplace": 0.01,
                "updated_kitchen": 0.02,
                "hardwood_floors": 0.015
            }

            for feature in additional_features:
                if feature in feature_values:
                    adjustment_factor *= (1 + feature_values[feature])
                    adjustments.append({
                        "factor": feature,
                        "adjustment": feature_values[feature] * 100
                    })

        estimated_value = base_value * adjustment_factor

        return {
            "estimated_value": round(estimated_value, 2),
            "base_value": round(base_value, 2),
            "adjustment_factor": round(adjustment_factor, 3),
            "adjustments": adjustments,
            "confidence_level": self._calculate_confidence_level(market_data),
            "value_range": {
                "low": round(estimated_value * 0.9, 2),
                "high": round(estimated_value * 1.1, 2)
            }
        }

    def _check_compliance_rule(self, rule: ComplianceRule, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if transaction data violates a compliance rule."""
        criteria = rule.validation_criteria

        for field, requirement in criteria.items():
            if field not in data:
                if requirement.get("required", False):
                    return {
                        "rule_id": rule.rule_id,
                        "severity": rule.severity,
                        "title": rule.title,
                        "description": f"Required field '{field}' is missing",
                        "remediation_steps": rule.remediation_steps
                    }
                continue

            value = data[field]

            # Check value constraints
            if "min_value" in requirement and value < requirement["min_value"]:
                return {
                    "rule_id": rule.rule_id,
                    "severity": rule.severity,
                    "title": rule.title,
                    "description": f"Field '{field}' value {value} is below minimum {requirement['min_value']}",
                    "remediation_steps": rule.remediation_steps
                }

            if "max_value" in requirement and value > requirement["max_value"]:
                return {
                    "rule_id": rule.rule_id,
                    "severity": rule.severity,
                    "title": rule.title,
                    "description": f"Field '{field}' value {value} exceeds maximum {requirement['max_value']}",
                    "remediation_steps": rule.remediation_steps
                }

            if "allowed_values" in requirement and value not in requirement["allowed_values"]:
                return {
                    "rule_id": rule.rule_id,
                    "severity": rule.severity,
                    "title": rule.title,
                    "description": f"Field '{field}' value '{value}' is not allowed",
                    "remediation_steps": rule.remediation_steps
                }

        return None

    def _is_clause_applicable(
        self,
        clause: Dict[str, Any],
        property_type: PropertyType,
        transaction_type: TransactionType,
        jurisdiction: Jurisdiction
    ) -> bool:
        """Check if a clause is applicable to the transaction."""
        # Check property type restrictions
        if "property_types" in clause:
            if property_type.value not in clause["property_types"]:
                return False

        # Check transaction type restrictions
        if "transaction_types" in clause:
            if transaction_type.value not in clause["transaction_types"]:
                return False

        # Check jurisdiction restrictions
        if "jurisdictions" in clause:
            if jurisdiction.value not in clause["jurisdictions"]:
                return False

        return True

    def _calculate_market_score(self, data: MarketData) -> float:
        """Calculate a market attractiveness score."""
        score = 50  # Base score

        # Inventory level impact
        if data.inventory_level == "low":
            score += 15
        elif data.inventory_level == "high":
            score -= 10

        # Days on market impact
        if data.days_on_market < 30:
            score += 10
        elif data.days_on_market > 90:
            score -= 15

        # Price trend impact
        if data.price_trend == "increasing":
            score += 20
        elif data.price_trend == "decreasing":
            score -= 20

        return max(0, min(100, score))

    def _calculate_confidence_level(self, market_data: Dict[str, Any]) -> str:
        """Calculate confidence level for property valuation."""
        days_since_update = (datetime.now() - datetime.fromisoformat(market_data["last_updated"].replace('Z', '+00:00'))).days

        if days_since_update < 30:
            return "high"
        elif days_since_update < 90:
            return "medium"
        else:
            return "low"

    def _initialize_legal_requirements(self):
        """Initialize legal requirements database."""
        # California residential purchase requirements
        self.legal_requirements["ca_res_purchase_disclosure"] = LegalRequirement(
            requirement_id="ca_res_purchase_disclosure",
            jurisdiction=Jurisdiction.US_CALIFORNIA,
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY,
            transaction_type=TransactionType.PURCHASE,
            title="Property Disclosure Statement",
            description="Seller must provide complete property disclosure statement",
            mandatory=True,
            deadline_days=3,
            required_documents=["Transfer Disclosure Statement", "Natural Hazard Disclosure"],
            penalties="Transaction may be voided by buyer",
            references=["California Civil Code Section 1102"]
        )

        self.legal_requirements["ca_res_purchase_inspection"] = LegalRequirement(
            requirement_id="ca_res_purchase_inspection",
            jurisdiction=Jurisdiction.US_CALIFORNIA,
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY,
            transaction_type=TransactionType.PURCHASE,
            title="Property Inspection Period",
            description="Buyer has right to inspect property within specified timeframe",
            mandatory=False,
            deadline_days=17,
            required_documents=["Inspection Reports"],
            penalties="Waiver of inspection rights",
            references=["California Civil Code Section 1102.6"]
        )

        # Federal requirements
        self.legal_requirements["fed_res_purchase_lead"] = LegalRequirement(
            requirement_id="fed_res_purchase_lead",
            jurisdiction=Jurisdiction.US_FEDERAL,
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY,
            transaction_type=TransactionType.PURCHASE,
            title="Lead-Based Paint Disclosure",
            description="Disclosure required for homes built before 1978",
            mandatory=True,
            deadline_days=10,
            required_documents=["Lead-Based Paint Disclosure", "EPA Pamphlet"],
            penalties="$10,000+ fines, transaction voidable",
            references=["42 USC 4852d"]
        )

    def _initialize_compliance_rules(self):
        """Initialize compliance rules database."""
        self.compliance_rules["purchase_price_validation"] = ComplianceRule(
            rule_id="purchase_price_validation",
            jurisdiction=Jurisdiction.US_FEDERAL,
            category="financial",
            title="Purchase Price Validation",
            description="Purchase price must be reasonable and properly documented",
            validation_criteria={
                "purchase_price": {
                    "required": True,
                    "min_value": 1000,
                    "max_value": 50000000
                },
                "financing_type": {
                    "required": True,
                    "allowed_values": ["cash", "conventional", "fha", "va", "usda"]
                }
            },
            severity="error",
            remediation_steps=[
                "Verify purchase price is accurate",
                "Ensure financing type is properly documented",
                "Obtain property appraisal if required"
            ]
        )

        self.compliance_rules["earnest_money_requirement"] = ComplianceRule(
            rule_id="earnest_money_requirement",
            jurisdiction=Jurisdiction.US_CALIFORNIA,
            category="financial",
            title="Earnest Money Deposit",
            description="Earnest money deposit should be reasonable percentage of purchase price",
            validation_criteria={
                "earnest_money": {
                    "required": True,
                    "min_value": 500
                },
                "earnest_money_percentage": {
                    "min_value": 0.5,
                    "max_value": 10.0
                }
            },
            severity="warning",
            remediation_steps=[
                "Verify earnest money amount is appropriate",
                "Ensure earnest money is held in proper escrow account"
            ]
        )

    def _initialize_document_templates(self):
        """Initialize document templates."""
        self.document_templates["ca_residential_purchase"] = DocumentTemplate(
            template_id="ca_residential_purchase",
            name="California Residential Purchase Agreement",
            description="Standard residential purchase agreement for California",
            property_types=[PropertyType.RESIDENTIAL_SINGLE_FAMILY, PropertyType.RESIDENTIAL_CONDO],
            transaction_types=[TransactionType.PURCHASE],
            jurisdictions=[Jurisdiction.US_CALIFORNIA],
            required_fields=[
                "buyer_name", "seller_name", "property_address", "purchase_price",
                "earnest_money", "closing_date", "financing_terms"
            ],
            optional_fields=[
                "personal_property", "repairs", "contingencies", "special_terms"
            ],
            template_content="[CALIFORNIA RESIDENTIAL PURCHASE AGREEMENT TEMPLATE]",
            version="2024.1"
        )

        self.document_templates["commercial_lease"] = DocumentTemplate(
            template_id="commercial_lease",
            name="Commercial Lease Agreement",
            description="Standard commercial lease agreement",
            property_types=[PropertyType.COMMERCIAL_OFFICE, PropertyType.COMMERCIAL_RETAIL],
            transaction_types=[TransactionType.LEASE],
            jurisdictions=[Jurisdiction.US_FEDERAL, Jurisdiction.US_CALIFORNIA],
            required_fields=[
                "landlord_name", "tenant_name", "property_address", "lease_term",
                "monthly_rent", "security_deposit", "permitted_use"
            ],
            optional_fields=[
                "renewal_options", "maintenance_responsibilities", "insurance_requirements"
            ],
            template_content="[COMMERCIAL LEASE AGREEMENT TEMPLATE]",
            version="2024.1"
        )

    def _initialize_clause_library(self):
        """Initialize clause library."""
        self.clause_library = {
            "base": {
                "time_is_essence": {
                    "title": "Time is of the Essence",
                    "content": "Time is of the essence in this agreement. All deadlines and dates specified herein are material terms.",
                    "priority": "high",
                    "category": "general"
                },
                "entire_agreement": {
                    "title": "Entire Agreement",
                    "content": "This agreement constitutes the entire agreement between the parties and supersedes all prior negotiations.",
                    "priority": "normal",
                    "category": "general"
                }
            },
            "residential_single_family": {
                "inspection_contingency": {
                    "title": "Inspection Contingency",
                    "content": "Buyer's obligation to purchase is contingent upon satisfactory inspection of the property.",
                    "priority": "high",
                    "category": "contingency"
                },
                "financing_contingency": {
                    "title": "Financing Contingency",
                    "content": "Buyer's obligation is contingent upon obtaining financing on terms specified herein.",
                    "priority": "high",
                    "category": "contingency"
                }
            },
            "risk_flood": {
                "flood_disclosure": {
                    "title": "Flood Zone Disclosure",
                    "content": "Property is located in a designated flood zone. Buyer acknowledges receipt of flood zone information.",
                    "priority": "critical",
                    "category": "disclosure"
                }
            }
        }

    def _initialize_sample_market_data(self):
        """Initialize sample market data."""
        self.market_data["los_angeles_residential_single_family"] = MarketData(
            location="Los Angeles, CA",
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY,
            median_price=850000.0,
            price_per_sqft=650.0,
            days_on_market=35,
            inventory_level="low",
            price_trend="increasing",
            last_updated=datetime.now() - timedelta(days=7)
        )

        self.market_data["austin_residential_single_family"] = MarketData(
            location="Austin, TX",
            property_type=PropertyType.RESIDENTIAL_SINGLE_FAMILY,
            median_price=475000.0,
            price_per_sqft=285.0,
            days_on_market=28,
            inventory_level="medium",
            price_trend="stable",
            last_updated=datetime.now() - timedelta(days=5)
        )


# Global knowledge base instance
_knowledge_base = None


def get_real_estate_knowledge_base() -> RealEstateKnowledgeBase:
    """Get the global real estate knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = RealEstateKnowledgeBase()
    return _knowledge_base
