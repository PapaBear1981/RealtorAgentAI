"""
Summary Agent Tools.

This module provides specialized tools for the Summary Agent,
including document summarization, diff generation, and executive reporting.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from difflib import unified_diff, SequenceMatcher

import structlog
from pydantic import BaseModel, Field

from .base import BaseTool, ToolInput, ToolResult, ToolCategory
from ...core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class DocumentSummarizationInput(ToolInput):
    """Input for document summarization tool."""
    document_content: str = Field(..., description="Document content to summarize")
    summary_type: str = Field(default="comprehensive", description="Type of summary")
    summary_options: Dict[str, Any] = Field(default_factory=dict, description="Summarization options")


class DiffGenerationInput(ToolInput):
    """Input for diff generation tool."""
    original_content: str = Field(..., description="Original document content")
    modified_content: str = Field(..., description="Modified document content")
    diff_options: Dict[str, Any] = Field(default_factory=dict, description="Diff generation options")


class ChecklistGenerationInput(ToolInput):
    """Input for checklist generation tool."""
    document_content: str = Field(..., description="Document content")
    checklist_type: str = Field(default="completion", description="Type of checklist")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Context data")


class ExecutiveSummaryInput(ToolInput):
    """Input for executive summary tool."""
    workflow_data: Dict[str, Any] = Field(..., description="Workflow data")
    summary_scope: str = Field(default="full", description="Scope of summary")
    audience: str = Field(default="executive", description="Target audience")


class DocumentSummarizationTool(BaseTool):
    """Tool for creating document summaries with key point extraction."""
    
    @property
    def name(self) -> str:
        return "document_summarizer"
    
    @property
    def description(self) -> str:
        return "Create comprehensive document summaries with key point extraction"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SUMMARIZATION
    
    async def execute(self, input_data: DocumentSummarizationInput) -> ToolResult:
        """Generate document summary."""
        try:
            # Extract key sections
            sections = await self._extract_document_sections(input_data.document_content)
            
            # Generate summary based on type
            if input_data.summary_type == "executive":
                summary = await self._generate_executive_summary(sections, input_data.summary_options)
            elif input_data.summary_type == "technical":
                summary = await self._generate_technical_summary(sections, input_data.summary_options)
            elif input_data.summary_type == "legal":
                summary = await self._generate_legal_summary(sections, input_data.summary_options)
            else:
                summary = await self._generate_comprehensive_summary(sections, input_data.summary_options)
            
            # Extract key points
            key_points = await self._extract_key_points(input_data.document_content, sections)
            
            # Generate action items
            action_items = await self._extract_action_items(input_data.document_content)
            
            # Calculate summary metrics
            metrics = await self._calculate_summary_metrics(
                input_data.document_content,
                summary
            )
            
            return ToolResult(
                success=True,
                data={
                    "summary": summary,
                    "key_points": key_points,
                    "action_items": action_items,
                    "sections": sections,
                    "metrics": metrics,
                    "summary_type": input_data.summary_type
                },
                metadata={
                    "original_length": len(input_data.document_content),
                    "summary_length": len(summary.get("content", "")),
                    "compression_ratio": metrics.get("compression_ratio", 0),
                    "generation_timestamp": datetime.utcnow().isoformat()
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Document summarization failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )
    
    async def _extract_document_sections(self, content: str) -> Dict[str, str]:
        """Extract logical sections from document content."""
        sections = {}
        
        # Common real estate contract sections
        section_patterns = {
            "parties": r"(?i)(parties|buyer|seller|purchaser|vendor).*?(?=\n\n|\n[A-Z]|$)",
            "property": r"(?i)(property|premises|real estate|located).*?(?=\n\n|\n[A-Z]|$)",
            "purchase_price": r"(?i)(purchase price|consideration|amount).*?(?=\n\n|\n[A-Z]|$)",
            "financing": r"(?i)(financing|loan|mortgage|contingent).*?(?=\n\n|\n[A-Z]|$)",
            "closing": r"(?i)(closing|settlement|possession).*?(?=\n\n|\n[A-Z]|$)",
            "contingencies": r"(?i)(contingencies|subject to|provided that).*?(?=\n\n|\n[A-Z]|$)",
            "disclosures": r"(?i)(disclosure|warranty|representation).*?(?=\n\n|\n[A-Z]|$)"
        }
        
        for section_name, pattern in section_patterns.items():
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                sections[section_name] = matches[0].strip()
        
        # If no specific sections found, create general sections
        if not sections:
            paragraphs = content.split('\n\n')
            for i, paragraph in enumerate(paragraphs[:5]):  # First 5 paragraphs
                if paragraph.strip():
                    sections[f"section_{i+1}"] = paragraph.strip()
        
        return sections
    
    async def _generate_executive_summary(self, 
                                        sections: Dict[str, str],
                                        options: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive-level summary."""
        summary_points = []
        
        # Extract key business points
        if "parties" in sections:
            summary_points.append("Transaction involves identified buyer and seller parties")
        
        if "purchase_price" in sections:
            price_match = re.search(r'\$[\d,]+\.?\d*', sections["purchase_price"])
            if price_match:
                summary_points.append(f"Purchase price: {price_match.group(0)}")
        
        if "property" in sections:
            summary_points.append("Property details and location specified")
        
        if "financing" in sections:
            summary_points.append("Financing terms and conditions outlined")
        
        if "closing" in sections:
            summary_points.append("Closing timeline and procedures defined")
        
        content = "EXECUTIVE SUMMARY\n\n" + "\n".join(f"• {point}" for point in summary_points)
        
        return {
            "content": content,
            "type": "executive",
            "key_highlights": summary_points,
            "word_count": len(content.split())
        }
    
    async def _generate_technical_summary(self, 
                                        sections: Dict[str, str],
                                        options: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical summary with detailed analysis."""
        technical_points = []
        
        for section_name, section_content in sections.items():
            if section_content:
                # Extract technical details
                word_count = len(section_content.split())
                technical_points.append(f"{section_name.title()}: {word_count} words - {section_content[:100]}...")
        
        content = "TECHNICAL SUMMARY\n\n" + "\n\n".join(technical_points)
        
        return {
            "content": content,
            "type": "technical",
            "sections_analyzed": len(sections),
            "total_sections": list(sections.keys()),
            "word_count": len(content.split())
        }
    
    async def _generate_legal_summary(self, 
                                    sections: Dict[str, str],
                                    options: Dict[str, Any]) -> Dict[str, Any]:
        """Generate legal-focused summary."""
        legal_points = []
        
        # Identify legal terms and obligations
        legal_terms = ["contingent", "warranty", "representation", "covenant", "obligation", "liability"]
        
        for section_name, section_content in sections.items():
            found_terms = [term for term in legal_terms if term.lower() in section_content.lower()]
            if found_terms:
                legal_points.append(f"{section_name.title()}: Contains {', '.join(found_terms)}")
        
        content = "LEGAL SUMMARY\n\n" + "\n".join(f"• {point}" for point in legal_points)
        
        return {
            "content": content,
            "type": "legal",
            "legal_terms_found": legal_points,
            "compliance_notes": ["Review all contingencies", "Verify disclosure requirements"],
            "word_count": len(content.split())
        }
    
    async def _generate_comprehensive_summary(self, 
                                            sections: Dict[str, str],
                                            options: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive summary."""
        summary_parts = []
        
        # Overview
        summary_parts.append("DOCUMENT OVERVIEW")
        summary_parts.append(f"This document contains {len(sections)} main sections covering various aspects of the agreement.")
        
        # Section summaries
        for section_name, section_content in sections.items():
            if section_content:
                # Create brief summary of each section
                first_sentence = section_content.split('.')[0] + '.' if '.' in section_content else section_content[:100] + '...'
                summary_parts.append(f"\n{section_name.title()}: {first_sentence}")
        
        content = "\n".join(summary_parts)
        
        return {
            "content": content,
            "type": "comprehensive",
            "sections_covered": list(sections.keys()),
            "detail_level": "medium",
            "word_count": len(content.split())
        }
    
    async def _extract_key_points(self, 
                                content: str,
                                sections: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract key points from document."""
        key_points = []
        
        # Financial terms
        money_matches = re.findall(r'\$[\d,]+\.?\d*', content)
        for amount in money_matches:
            key_points.append({
                "type": "financial",
                "content": f"Financial amount: {amount}",
                "importance": "high"
            })
        
        # Dates
        date_matches = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', content)
        for date in date_matches:
            key_points.append({
                "type": "timeline",
                "content": f"Important date: {date}",
                "importance": "medium"
            })
        
        # Parties
        if "parties" in sections:
            key_points.append({
                "type": "parties",
                "content": "Parties to the agreement identified",
                "importance": "high"
            })
        
        return key_points
    
    async def _extract_action_items(self, content: str) -> List[Dict[str, Any]]:
        """Extract action items and next steps."""
        action_items = []
        
        # Look for action-oriented language
        action_patterns = [
            r"(?i)(shall|must|will|required to|needs to|should)([^.]+)",
            r"(?i)(deadline|due date|by)([^.]+)",
            r"(?i)(contingent upon|subject to)([^.]+)"
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                action_items.append({
                    "action": match[1].strip(),
                    "type": "requirement",
                    "priority": "medium",
                    "source": "document_analysis"
                })
        
        return action_items[:10]  # Limit to top 10 action items
    
    async def _calculate_summary_metrics(self, 
                                       original_content: str,
                                       summary: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary quality metrics."""
        original_words = len(original_content.split())
        summary_words = len(summary.get("content", "").split())
        
        compression_ratio = (original_words - summary_words) / original_words if original_words > 0 else 0
        
        return {
            "original_word_count": original_words,
            "summary_word_count": summary_words,
            "compression_ratio": round(compression_ratio, 3),
            "compression_percentage": round(compression_ratio * 100, 1),
            "readability_score": 0.75  # Would calculate actual readability
        }


class DiffGenerationTool(BaseTool):
    """Tool for generating diffs between document versions."""
    
    @property
    def name(self) -> str:
        return "diff_generator"
    
    @property
    def description(self) -> str:
        return "Generate detailed diffs between document versions with change analysis"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SUMMARIZATION
    
    async def execute(self, input_data: DiffGenerationInput) -> ToolResult:
        """Generate diff between document versions."""
        try:
            # Generate line-by-line diff
            line_diff = await self._generate_line_diff(
                input_data.original_content,
                input_data.modified_content
            )
            
            # Generate word-level diff for changed lines
            word_diff = await self._generate_word_diff(
                input_data.original_content,
                input_data.modified_content
            )
            
            # Analyze changes
            change_analysis = await self._analyze_changes(
                input_data.original_content,
                input_data.modified_content
            )
            
            # Generate change summary
            change_summary = await self._generate_change_summary(change_analysis)
            
            return ToolResult(
                success=True,
                data={
                    "line_diff": line_diff,
                    "word_diff": word_diff,
                    "change_analysis": change_analysis,
                    "change_summary": change_summary,
                    "diff_stats": {
                        "lines_added": change_analysis.get("lines_added", 0),
                        "lines_removed": change_analysis.get("lines_removed", 0),
                        "lines_modified": change_analysis.get("lines_modified", 0)
                    }
                },
                metadata={
                    "diff_timestamp": datetime.utcnow().isoformat(),
                    "original_size": len(input_data.original_content),
                    "modified_size": len(input_data.modified_content),
                    "similarity_ratio": change_analysis.get("similarity_ratio", 0)
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Diff generation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )
    
    async def _generate_line_diff(self, original: str, modified: str) -> List[str]:
        """Generate line-by-line diff."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = list(unified_diff(
            original_lines,
            modified_lines,
            fromfile='original',
            tofile='modified',
            lineterm=''
        ))
        
        return diff
    
    async def _generate_word_diff(self, original: str, modified: str) -> Dict[str, Any]:
        """Generate word-level diff for better granularity."""
        original_words = original.split()
        modified_words = modified.split()
        
        matcher = SequenceMatcher(None, original_words, modified_words)
        
        word_changes = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'delete':
                word_changes.append({
                    "type": "deletion",
                    "content": " ".join(original_words[i1:i2]),
                    "position": i1
                })
            elif tag == 'insert':
                word_changes.append({
                    "type": "insertion",
                    "content": " ".join(modified_words[j1:j2]),
                    "position": j1
                })
            elif tag == 'replace':
                word_changes.append({
                    "type": "replacement",
                    "original": " ".join(original_words[i1:i2]),
                    "modified": " ".join(modified_words[j1:j2]),
                    "position": i1
                })
        
        return {
            "changes": word_changes,
            "total_changes": len(word_changes)
        }
    
    async def _analyze_changes(self, original: str, modified: str) -> Dict[str, Any]:
        """Analyze the nature and impact of changes."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        matcher = SequenceMatcher(None, original_lines, modified_lines)
        similarity_ratio = matcher.ratio()
        
        # Count different types of changes
        lines_added = 0
        lines_removed = 0
        lines_modified = 0
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'delete':
                lines_removed += i2 - i1
            elif tag == 'insert':
                lines_added += j2 - j1
            elif tag == 'replace':
                lines_modified += max(i2 - i1, j2 - j1)
        
        # Analyze content changes
        content_analysis = await self._analyze_content_changes(original, modified)
        
        return {
            "similarity_ratio": round(similarity_ratio, 3),
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "lines_modified": lines_modified,
            "total_changes": lines_added + lines_removed + lines_modified,
            "content_analysis": content_analysis
        }
    
    async def _analyze_content_changes(self, original: str, modified: str) -> Dict[str, Any]:
        """Analyze specific content changes."""
        analysis = {
            "financial_changes": [],
            "date_changes": [],
            "party_changes": [],
            "legal_changes": []
        }
        
        # Check for financial changes
        original_amounts = set(re.findall(r'\$[\d,]+\.?\d*', original))
        modified_amounts = set(re.findall(r'\$[\d,]+\.?\d*', modified))
        
        if original_amounts != modified_amounts:
            analysis["financial_changes"] = {
                "added": list(modified_amounts - original_amounts),
                "removed": list(original_amounts - modified_amounts)
            }
        
        # Check for date changes
        original_dates = set(re.findall(r'\d{1,2}/\d{1,2}/\d{4}', original))
        modified_dates = set(re.findall(r'\d{1,2}/\d{1,2}/\d{4}', modified))
        
        if original_dates != modified_dates:
            analysis["date_changes"] = {
                "added": list(modified_dates - original_dates),
                "removed": list(original_dates - modified_dates)
            }
        
        return analysis
    
    async def _generate_change_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable change summary."""
        summary_points = []
        
        if analysis.get("lines_added", 0) > 0:
            summary_points.append(f"{analysis['lines_added']} lines added")
        
        if analysis.get("lines_removed", 0) > 0:
            summary_points.append(f"{analysis['lines_removed']} lines removed")
        
        if analysis.get("lines_modified", 0) > 0:
            summary_points.append(f"{analysis['lines_modified']} lines modified")
        
        content_analysis = analysis.get("content_analysis", {})
        
        if content_analysis.get("financial_changes"):
            summary_points.append("Financial terms modified")
        
        if content_analysis.get("date_changes"):
            summary_points.append("Date information updated")
        
        change_magnitude = "minor"
        if analysis.get("total_changes", 0) > 10:
            change_magnitude = "major"
        elif analysis.get("total_changes", 0) > 5:
            change_magnitude = "moderate"
        
        return {
            "summary_text": "; ".join(summary_points) if summary_points else "No significant changes detected",
            "change_magnitude": change_magnitude,
            "similarity_percentage": round(analysis.get("similarity_ratio", 0) * 100, 1),
            "requires_review": analysis.get("total_changes", 0) > 5 or bool(content_analysis.get("financial_changes"))
        }
