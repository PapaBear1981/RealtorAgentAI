"""
Compliance Checker Agent Tools.

This module provides specialized tools for the Compliance Checker Agent,
including validation rules, jurisdiction-specific policies, and severity gates.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from .base import ComplianceTool, ToolInput, ToolResult, ToolCategory
from ...core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class SeverityLevel(Enum):
    """Severity levels for compliance issues."""
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class ComplianceCheckInput(ToolInput):
    """Input for compliance checking tool."""
    contract_content: str = Field(..., description="Contract content to check")
    contract_type: str = Field(default="residential_purchase", description="Type of contract")
    jurisdiction: str = Field(default="default", description="Legal jurisdiction")
    check_options: Dict[str, Any] = Field(default_factory=dict, description="Checking options")


class RuleValidationInput(ToolInput):
    """Input for rule validation tool."""
    content: str = Field(..., description="Content to validate")
    rule_set: str = Field(..., description="Rule set to apply")
    jurisdiction: str = Field(default="default", description="Legal jurisdiction")


class ComplianceReportInput(ToolInput):
    """Input for compliance report generation."""
    validation_results: Dict[str, Any] = Field(..., description="Validation results")
    contract_metadata: Dict[str, Any] = Field(default_factory=dict, description="Contract metadata")
    report_options: Dict[str, Any] = Field(default_factory=dict, description="Report generation options")


class ComplianceRule(BaseModel):
    """Model for a compliance rule."""
    id: str = Field(..., description="Rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    severity: SeverityLevel = Field(..., description="Rule severity level")
    pattern: Optional[str] = Field(None, description="Regex pattern for text-based rules")
    validator_function: Optional[str] = Field(None, description="Custom validator function name")
    jurisdiction: str = Field(default="default", description="Applicable jurisdiction")
    category: str = Field(..., description="Rule category")
    enabled: bool = Field(default=True, description="Whether rule is enabled")


class ComplianceValidationTool(ComplianceTool):
    """Tool for validating contracts against compliance rules."""
    
    @property
    def name(self) -> str:
        return "compliance_validator"
    
    @property
    def description(self) -> str:
        return "Validate contracts against legal requirements and industry regulations"
    
    async def execute(self, input_data: ComplianceCheckInput) -> ToolResult:
        """Validate contract compliance."""
        try:
            # Load applicable rules
            rules = await self._load_compliance_rules(
                input_data.contract_type,
                input_data.jurisdiction
            )
            
            # Run validation checks
            validation_results = await self._run_validation_checks(
                input_data.contract_content,
                rules,
                input_data.check_options
            )
            
            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(validation_results)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(validation_results)
            
            return ToolResult(
                success=True,
                data={
                    "compliance_score": compliance_score,
                    "validation_results": validation_results,
                    "recommendations": recommendations,
                    "rules_checked": len(rules),
                    "issues_found": sum(len(results) for results in validation_results.values()),
                    "blockers": len(validation_results.get("blockers", [])),
                    "warnings": len(validation_results.get("warnings", [])),
                    "info": len(validation_results.get("info", []))
                },
                metadata={
                    "contract_type": input_data.contract_type,
                    "jurisdiction": input_data.jurisdiction,
                    "validation_timestamp": datetime.utcnow().isoformat(),
                    "rules_version": "1.0"
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Compliance validation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )
    
    async def _load_compliance_rules(self, 
                                   contract_type: str,
                                   jurisdiction: str) -> List[ComplianceRule]:
        """Load applicable compliance rules."""
        # This would load from a rules database in production
        rules = [
            ComplianceRule(
                id="required_parties",
                name="Required Parties",
                description="Contract must identify all required parties",
                severity=SeverityLevel.BLOCKER,
                pattern=r"(?i)(buyer|purchaser).*?and.*?(seller|vendor)",
                jurisdiction=jurisdiction,
                category="parties"
            ),
            ComplianceRule(
                id="purchase_price",
                name="Purchase Price Disclosure",
                description="Contract must clearly state the purchase price",
                severity=SeverityLevel.BLOCKER,
                pattern=r"\$[\d,]+\.?\d*",
                jurisdiction=jurisdiction,
                category="financial"
            ),
            ComplianceRule(
                id="property_description",
                name="Property Description",
                description="Contract must include adequate property description",
                severity=SeverityLevel.WARNING,
                pattern=r"(?i)(property|premises|real estate).*?(located|situated|address)",
                jurisdiction=jurisdiction,
                category="property"
            ),
            ComplianceRule(
                id="closing_date",
                name="Closing Date",
                description="Contract should specify closing date",
                severity=SeverityLevel.WARNING,
                pattern=r"(?i)(closing|settlement).*?(\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-\d{1,2}-\d{4})",
                jurisdiction=jurisdiction,
                category="timeline"
            ),
            ComplianceRule(
                id="contingencies",
                name="Contingency Clauses",
                description="Review contingency clauses for completeness",
                severity=SeverityLevel.INFO,
                pattern=r"(?i)(contingent|subject to|provided that)",
                jurisdiction=jurisdiction,
                category="contingencies"
            ),
            ComplianceRule(
                id="signatures",
                name="Signature Requirements",
                description="Contract must have signature blocks for all parties",
                severity=SeverityLevel.BLOCKER,
                pattern=r"(?i)(signature|signed|executed)",
                jurisdiction=jurisdiction,
                category="execution"
            )
        ]
        
        # Filter rules by contract type and jurisdiction
        applicable_rules = [
            rule for rule in rules 
            if rule.enabled and (rule.jurisdiction == jurisdiction or rule.jurisdiction == "default")
        ]
        
        return applicable_rules
    
    async def _run_validation_checks(self, 
                                   content: str,
                                   rules: List[ComplianceRule],
                                   options: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Run validation checks against all rules."""
        results = {
            "blockers": [],
            "warnings": [],
            "info": []
        }
        
        for rule in rules:
            try:
                violations = await self._check_rule(content, rule)
                
                for violation in violations:
                    issue = {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "description": rule.description,
                        "severity": rule.severity.value,
                        "category": rule.category,
                        "details": violation,
                        "location": violation.get("location", "unknown"),
                        "suggestion": self._get_rule_suggestion(rule)
                    }
                    
                    if rule.severity == SeverityLevel.BLOCKER:
                        results["blockers"].append(issue)
                    elif rule.severity == SeverityLevel.WARNING:
                        results["warnings"].append(issue)
                    else:
                        results["info"].append(issue)
                        
            except Exception as e:
                logger.error(f"Rule check failed for {rule.id}: {e}")
        
        return results
    
    async def _check_rule(self, content: str, rule: ComplianceRule) -> List[Dict[str, Any]]:
        """Check a single compliance rule."""
        violations = []
        
        if rule.pattern:
            # Pattern-based rule
            matches = list(re.finditer(rule.pattern, content))
            
            if rule.id in ["required_parties", "purchase_price", "signatures"]:
                # These rules require matches to be present
                if not matches:
                    violations.append({
                        "type": "missing_required_element",
                        "message": f"Required element not found: {rule.name}",
                        "location": "document"
                    })
            else:
                # These rules are informational about what was found
                for match in matches:
                    violations.append({
                        "type": "found_element",
                        "message": f"Found: {match.group(0)}",
                        "location": f"position {match.start()}-{match.end()}"
                    })
        
        elif rule.validator_function:
            # Custom validator function
            violations.extend(await self._run_custom_validator(content, rule))
        
        return violations
    
    async def _run_custom_validator(self, content: str, rule: ComplianceRule) -> List[Dict[str, Any]]:
        """Run custom validator function."""
        # This would implement custom validation logic
        # For now, return empty list
        return []
    
    def _get_rule_suggestion(self, rule: ComplianceRule) -> str:
        """Get suggestion for fixing rule violation."""
        suggestions = {
            "required_parties": "Ensure the contract clearly identifies both buyer and seller with full names.",
            "purchase_price": "Include the complete purchase price in dollar format (e.g., $250,000).",
            "property_description": "Add a detailed description of the property including address and legal description.",
            "closing_date": "Specify the exact closing or settlement date.",
            "contingencies": "Review all contingency clauses for completeness and clarity.",
            "signatures": "Include signature blocks for all parties to the contract."
        }
        
        return suggestions.get(rule.id, "Review this section for compliance with applicable regulations.")
    
    def _calculate_compliance_score(self, validation_results: Dict[str, List[Dict[str, Any]]]) -> float:
        """Calculate overall compliance score."""
        blockers = len(validation_results.get("blockers", []))
        warnings = len(validation_results.get("warnings", []))
        info = len(validation_results.get("info", []))
        
        # Weighted scoring
        total_issues = blockers * 3 + warnings * 2 + info * 1
        max_possible_score = 100
        
        if total_issues == 0:
            return 100.0
        
        # Deduct points based on severity
        score = max_possible_score - min(total_issues * 5, max_possible_score)
        return max(score, 0.0)
    
    async def _generate_recommendations(self, validation_results: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        blockers = validation_results.get("blockers", [])
        warnings = validation_results.get("warnings", [])
        
        if blockers:
            recommendations.append(f"CRITICAL: {len(blockers)} blocking issues must be resolved before contract execution.")
            for blocker in blockers[:3]:  # Show top 3 blockers
                recommendations.append(f"• {blocker['rule_name']}: {blocker['suggestion']}")
        
        if warnings:
            recommendations.append(f"WARNING: {len(warnings)} issues should be reviewed and addressed.")
            for warning in warnings[:2]:  # Show top 2 warnings
                recommendations.append(f"• {warning['rule_name']}: {warning['suggestion']}")
        
        if not blockers and not warnings:
            recommendations.append("Contract appears to meet basic compliance requirements.")
        
        return recommendations


class RuleEngineValidationTool(ComplianceTool):
    """Tool for running rule engine validation."""
    
    @property
    def name(self) -> str:
        return "rule_engine_validator"
    
    @property
    def description(self) -> str:
        return "Run advanced rule engine validation with custom business logic"
    
    async def execute(self, input_data: RuleValidationInput) -> ToolResult:
        """Run rule engine validation."""
        try:
            # Load rule set
            rule_set = await self._load_rule_set(input_data.rule_set, input_data.jurisdiction)
            
            # Execute rules
            execution_results = await self._execute_rule_set(
                input_data.content,
                rule_set
            )
            
            return ToolResult(
                success=True,
                data={
                    "rule_set": input_data.rule_set,
                    "execution_results": execution_results,
                    "rules_executed": len(rule_set.get("rules", [])),
                    "passed": execution_results.get("passed", 0),
                    "failed": execution_results.get("failed", 0),
                    "overall_result": execution_results.get("overall_result", "unknown")
                },
                metadata={
                    "rule_set_version": rule_set.get("version", "1.0"),
                    "jurisdiction": input_data.jurisdiction,
                    "execution_timestamp": datetime.utcnow().isoformat()
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Rule engine validation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )
    
    async def _load_rule_set(self, rule_set_name: str, jurisdiction: str) -> Dict[str, Any]:
        """Load rule set configuration."""
        # This would load from a rule set database
        rule_sets = {
            "real_estate_basic": {
                "name": "Real Estate Basic Rules",
                "version": "1.0",
                "jurisdiction": jurisdiction,
                "rules": [
                    {
                        "id": "party_identification",
                        "name": "Party Identification",
                        "logic": "must_contain_buyer_and_seller",
                        "parameters": {"min_parties": 2}
                    },
                    {
                        "id": "financial_terms",
                        "name": "Financial Terms",
                        "logic": "must_contain_price_and_terms",
                        "parameters": {"required_fields": ["purchase_price", "down_payment"]}
                    }
                ]
            }
        }
        
        return rule_sets.get(rule_set_name, {"name": "Unknown", "rules": []})
    
    async def _execute_rule_set(self, content: str, rule_set: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all rules in the rule set."""
        results = {
            "passed": 0,
            "failed": 0,
            "rule_results": [],
            "overall_result": "passed"
        }
        
        for rule in rule_set.get("rules", []):
            rule_result = await self._execute_single_rule(content, rule)
            results["rule_results"].append(rule_result)
            
            if rule_result["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1
        
        # Determine overall result
        if results["failed"] > 0:
            results["overall_result"] = "failed"
        
        return results
    
    async def _execute_single_rule(self, content: str, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single rule."""
        rule_id = rule.get("id", "unknown")
        logic = rule.get("logic", "")
        parameters = rule.get("parameters", {})
        
        try:
            # Simple rule logic implementation
            if logic == "must_contain_buyer_and_seller":
                passed = "buyer" in content.lower() and "seller" in content.lower()
            elif logic == "must_contain_price_and_terms":
                passed = "$" in content and ("price" in content.lower() or "payment" in content.lower())
            else:
                passed = True  # Unknown logic passes by default
            
            return {
                "rule_id": rule_id,
                "rule_name": rule.get("name", "Unknown Rule"),
                "passed": passed,
                "message": "Rule passed" if passed else f"Rule failed: {logic}",
                "parameters": parameters
            }
            
        except Exception as e:
            return {
                "rule_id": rule_id,
                "rule_name": rule.get("name", "Unknown Rule"),
                "passed": False,
                "message": f"Rule execution error: {str(e)}",
                "parameters": parameters
            }


class ComplianceReportTool(ComplianceTool):
    """Tool for generating compliance reports."""
    
    @property
    def name(self) -> str:
        return "compliance_reporter"
    
    @property
    def description(self) -> str:
        return "Generate comprehensive compliance reports with recommendations"
    
    async def execute(self, input_data: ComplianceReportInput) -> ToolResult:
        """Generate a compliance report."""
        try:
            # Generate report sections
            executive_summary = await self._generate_executive_summary(input_data.validation_results)
            detailed_findings = await self._generate_detailed_findings(input_data.validation_results)
            recommendations = await self._generate_action_plan(input_data.validation_results)
            
            # Create full report
            report = {
                "report_id": f"compliance_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "generated_at": datetime.utcnow().isoformat(),
                "executive_summary": executive_summary,
                "detailed_findings": detailed_findings,
                "action_plan": recommendations,
                "metadata": input_data.contract_metadata
            }
            
            return ToolResult(
                success=True,
                data={
                    "report": report,
                    "report_id": report["report_id"],
                    "summary_score": executive_summary.get("compliance_score", 0),
                    "total_issues": executive_summary.get("total_issues", 0),
                    "critical_issues": executive_summary.get("critical_issues", 0)
                },
                metadata={
                    "report_format": "json",
                    "generation_timestamp": datetime.utcnow().isoformat(),
                    "report_options": input_data.report_options
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Compliance report generation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )
    
    async def _generate_executive_summary(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary section."""
        blockers = validation_results.get("blockers", [])
        warnings = validation_results.get("warnings", [])
        info = validation_results.get("info", [])
        
        total_issues = len(blockers) + len(warnings) + len(info)
        compliance_score = validation_results.get("compliance_score", 0)
        
        summary = {
            "compliance_score": compliance_score,
            "total_issues": total_issues,
            "critical_issues": len(blockers),
            "warning_issues": len(warnings),
            "info_issues": len(info),
            "overall_status": "FAIL" if blockers else "PASS" if warnings else "EXCELLENT",
            "key_findings": []
        }
        
        # Add key findings
        if blockers:
            summary["key_findings"].append(f"{len(blockers)} critical issues require immediate attention")
        if warnings:
            summary["key_findings"].append(f"{len(warnings)} warnings should be reviewed")
        if not total_issues:
            summary["key_findings"].append("No compliance issues identified")
        
        return summary
    
    async def _generate_detailed_findings(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed findings section."""
        findings = {
            "critical_findings": validation_results.get("blockers", []),
            "warning_findings": validation_results.get("warnings", []),
            "informational_findings": validation_results.get("info", []),
            "findings_by_category": {}
        }
        
        # Group findings by category
        all_findings = (validation_results.get("blockers", []) + 
                       validation_results.get("warnings", []) + 
                       validation_results.get("info", []))
        
        for finding in all_findings:
            category = finding.get("category", "other")
            if category not in findings["findings_by_category"]:
                findings["findings_by_category"][category] = []
            findings["findings_by_category"][category].append(finding)
        
        return findings
    
    async def _generate_action_plan(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate action plan and recommendations."""
        blockers = validation_results.get("blockers", [])
        warnings = validation_results.get("warnings", [])
        
        action_plan = {
            "immediate_actions": [],
            "recommended_actions": [],
            "priority_order": [],
            "estimated_effort": "low"
        }
        
        # Immediate actions for blockers
        for blocker in blockers:
            action_plan["immediate_actions"].append({
                "action": f"Resolve {blocker['rule_name']}",
                "description": blocker.get("suggestion", "Address this critical issue"),
                "priority": "high",
                "category": blocker.get("category", "unknown")
            })
        
        # Recommended actions for warnings
        for warning in warnings:
            action_plan["recommended_actions"].append({
                "action": f"Review {warning['rule_name']}",
                "description": warning.get("suggestion", "Consider addressing this issue"),
                "priority": "medium",
                "category": warning.get("category", "unknown")
            })
        
        # Set estimated effort
        total_issues = len(blockers) + len(warnings)
        if total_issues > 5:
            action_plan["estimated_effort"] = "high"
        elif total_issues > 2:
            action_plan["estimated_effort"] = "medium"
        
        return action_plan
