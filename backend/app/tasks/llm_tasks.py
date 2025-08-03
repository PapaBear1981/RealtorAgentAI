"""
LLM tasks for AI model interactions and contract processing.

This module contains Celery tasks for AI-powered contract analysis,
content generation, entity extraction, and compliance validation.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from celery import current_task
import structlog
import openai
from anthropic import Anthropic

from ..core.celery_app import celery_app, DatabaseTask
from ..core.config import get_settings
from ..models.contract import Contract
from ..models.template import Template
from ..models.audit_log import AuditLog, AuditAction

logger = structlog.get_logger(__name__)
settings = get_settings()

# Initialize AI clients
openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY) if hasattr(settings, 'OPENAI_API_KEY') else None
anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY) if hasattr(settings, 'ANTHROPIC_API_KEY') else None


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.llm_tasks.analyze_contract_content")
def analyze_contract_content(
    self,
    contract_id: int,
    user_id: int,
    analysis_type: str = "comprehensive",
    model_preference: str = "gpt-4"
) -> Dict[str, Any]:
    """
    Analyze contract content using AI models.
    
    Args:
        contract_id: Database contract record ID
        user_id: User requesting the analysis
        analysis_type: Type of analysis (comprehensive, legal, financial, risk)
        model_preference: Preferred AI model (gpt-4, claude-3-sonnet)
        
    Returns:
        Dict: Analysis results with insights and recommendations
    """
    try:
        logger.info(
            "Starting contract content analysis",
            contract_id=contract_id,
            user_id=user_id,
            analysis_type=analysis_type,
            model_preference=model_preference
        )
        
        # Get contract record
        contract = self.session.get(Contract, contract_id)
        if not contract:
            raise ValueError(f"Contract record not found: {contract_id}")
        
        # Get contract content
        contract_text = contract.content or ""
        if not contract_text:
            raise ValueError("Contract has no content to analyze")
        
        # Prepare analysis prompt based on type
        analysis_prompts = {
            "comprehensive": """
            Analyze this real estate contract comprehensively. Provide insights on:
            1. Key terms and conditions
            2. Parties involved and their obligations
            3. Financial terms and payment schedules
            4. Important dates and deadlines
            5. Potential risks or concerns
            6. Compliance with standard practices
            7. Recommendations for improvement
            """,
            "legal": """
            Perform a legal analysis of this real estate contract. Focus on:
            1. Legal compliance and regulatory adherence
            2. Enforceability of terms
            3. Potential legal risks
            4. Missing standard clauses
            5. Ambiguous language that could cause disputes
            """,
            "financial": """
            Analyze the financial aspects of this real estate contract:
            1. Purchase price and payment terms
            2. Financing conditions
            3. Closing costs and fee allocations
            4. Contingencies affecting financial obligations
            5. Risk assessment of financial terms
            """,
            "risk": """
            Conduct a risk assessment of this real estate contract:
            1. Identify potential risks for all parties
            2. Assess likelihood and impact of identified risks
            3. Suggest risk mitigation strategies
            4. Highlight critical decision points
            """
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["comprehensive"])
        
        # Perform AI analysis
        if model_preference.startswith("gpt") and openai_client:
            analysis_result = self._analyze_with_openai(contract_text, prompt, model_preference)
        elif model_preference.startswith("claude") and anthropic_client:
            analysis_result = self._analyze_with_anthropic(contract_text, prompt, model_preference)
        else:
            # Fallback to available model
            if openai_client:
                analysis_result = self._analyze_with_openai(contract_text, prompt, "gpt-4")
            elif anthropic_client:
                analysis_result = self._analyze_with_anthropic(contract_text, prompt, "claude-3-sonnet")
            else:
                raise ValueError("No AI models available for analysis")
        
        # Structure the analysis results
        structured_results = {
            "contract_id": contract_id,
            "analysis_type": analysis_type,
            "model_used": analysis_result.get("model_used"),
            "analysis": analysis_result.get("analysis"),
            "key_insights": analysis_result.get("key_insights", []),
            "recommendations": analysis_result.get("recommendations", []),
            "risk_factors": analysis_result.get("risk_factors", []),
            "confidence_score": analysis_result.get("confidence_score", 0.8),
            "metadata": {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "contract_length": len(contract_text),
                "processing_time": analysis_result.get("processing_time", 0),
                "task_id": self.request.id
            }
        }
        
        # Update contract with analysis results
        current_metadata = contract.metadata or {}
        current_metadata[f"ai_analysis_{analysis_type}"] = structured_results
        contract.metadata = current_metadata
        self.session.add(contract)
        
        # Create audit log
        audit_log = AuditLog(
            user_id=user_id,
            actor=f"system:llm_task:{self.request.id}",
            action=AuditAction.CONTRACT_ANALYZE,
            resource_type="contract",
            resource_id=str(contract_id),
            success=True,
            meta={
                "contract_id": contract_id,
                "analysis_type": analysis_type,
                "model_used": analysis_result.get("model_used"),
                "insights_count": len(structured_results["key_insights"]),
                "recommendations_count": len(structured_results["recommendations"])
            }
        )
        self.session.add(audit_log)
        self.session.commit()
        
        logger.info(
            "Contract content analysis completed",
            contract_id=contract_id,
            analysis_type=analysis_type,
            insights=len(structured_results["key_insights"]),
            recommendations=len(structured_results["recommendations"])
        )
        
        return structured_results
        
    except Exception as exc:
        logger.error(
            "Contract content analysis failed",
            contract_id=contract_id,
            error=str(exc),
            exc_info=True
        )
        
        # Create error audit log
        audit_log = AuditLog(
            user_id=user_id,
            actor=f"system:llm_task:{self.request.id}",
            action=AuditAction.CONTRACT_ANALYZE,
            resource_type="contract",
            resource_id=str(contract_id),
            success=False,
            error_message=str(exc),
            meta={"contract_id": contract_id, "analysis_type": analysis_type}
        )
        self.session.add(audit_log)
        self.session.commit()
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    def _analyze_with_openai(self, contract_text: str, prompt: str, model: str) -> Dict[str, Any]:
        """Analyze contract using OpenAI models."""
        try:
            start_time = datetime.utcnow()
            
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert real estate attorney and contract analyst."},
                    {"role": "user", "content": f"{prompt}\n\nContract:\n{contract_text}"}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            analysis_text = response.choices[0].message.content
            
            # Parse structured response
            return self._parse_analysis_response(analysis_text, model, processing_time)
            
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {str(e)}")
            raise

    def _analyze_with_anthropic(self, contract_text: str, prompt: str, model: str) -> Dict[str, Any]:
        """Analyze contract using Anthropic models."""
        try:
            start_time = datetime.utcnow()
            
            response = anthropic_client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": f"{prompt}\n\nContract:\n{contract_text}"}
                ]
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            analysis_text = response.content[0].text
            
            # Parse structured response
            return self._parse_analysis_response(analysis_text, model, processing_time)
            
        except Exception as e:
            logger.error(f"Anthropic analysis failed: {str(e)}")
            raise

    def _parse_analysis_response(self, analysis_text: str, model: str, processing_time: float) -> Dict[str, Any]:
        """Parse AI analysis response into structured format."""
        # Basic parsing - in production, would use more sophisticated NLP
        lines = analysis_text.split('\n')
        
        key_insights = []
        recommendations = []
        risk_factors = []
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "insight" in line.lower() or "key" in line.lower():
                current_section = "insights"
            elif "recommend" in line.lower():
                current_section = "recommendations"
            elif "risk" in line.lower():
                current_section = "risks"
            elif line.startswith(('-', '•', '*')) or line[0].isdigit():
                if current_section == "insights":
                    key_insights.append(line.lstrip('-•* 0123456789.'))
                elif current_section == "recommendations":
                    recommendations.append(line.lstrip('-•* 0123456789.'))
                elif current_section == "risks":
                    risk_factors.append(line.lstrip('-•* 0123456789.'))
        
        return {
            "analysis": analysis_text,
            "key_insights": key_insights,
            "recommendations": recommendations,
            "risk_factors": risk_factors,
            "model_used": model,
            "processing_time": processing_time,
            "confidence_score": 0.85  # Would be calculated based on model confidence
        }


@celery_app.task(bind=True, name="app.tasks.llm_tasks.generate_contract_summary")
def generate_contract_summary(
    self,
    contract_text: str,
    summary_type: str = "executive",
    max_length: int = 500
) -> Dict[str, Any]:
    """
    Generate contract summary using AI models.
    
    Args:
        contract_text: Contract content to summarize
        summary_type: Type of summary (executive, technical, legal)
        max_length: Maximum summary length in words
        
    Returns:
        Dict: Generated summary and metadata
    """
    try:
        logger.info(
            "Starting contract summary generation",
            text_length=len(contract_text),
            summary_type=summary_type,
            max_length=max_length
        )
        
        # Prepare summary prompt
        summary_prompts = {
            "executive": f"Create a concise executive summary of this real estate contract in {max_length} words or less. Focus on key business terms, parties, and critical dates.",
            "technical": f"Provide a technical summary of this real estate contract in {max_length} words or less. Include specific terms, conditions, and technical requirements.",
            "legal": f"Generate a legal summary of this real estate contract in {max_length} words or less. Highlight legal obligations, rights, and compliance requirements."
        }
        
        prompt = summary_prompts.get(summary_type, summary_prompts["executive"])
        
        # Generate summary using available AI model
        if openai_client:
            start_time = datetime.utcnow()
            
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert real estate contract analyst."},
                    {"role": "user", "content": f"{prompt}\n\nContract:\n{contract_text}"}
                ],
                temperature=0.2,
                max_tokens=max_length * 2  # Allow some buffer for token estimation
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            summary = response.choices[0].message.content
            model_used = "gpt-4"
            
        elif anthropic_client:
            start_time = datetime.utcnow()
            
            response = anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=max_length * 2,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": f"{prompt}\n\nContract:\n{contract_text}"}
                ]
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            summary = response.content[0].text
            model_used = "claude-3-sonnet"
            
        else:
            raise ValueError("No AI models available for summary generation")
        
        results = {
            "summary": summary,
            "summary_type": summary_type,
            "word_count": len(summary.split()),
            "model_used": model_used,
            "metadata": {
                "original_length": len(contract_text),
                "compression_ratio": len(summary) / len(contract_text),
                "processing_time": processing_time,
                "generation_timestamp": datetime.utcnow().isoformat()
            },
            "success": True
        }
        
        logger.info(
            "Contract summary generation completed",
            summary_length=len(summary),
            word_count=results["word_count"],
            processing_time=processing_time
        )
        
        return results
        
    except Exception as exc:
        logger.error("Contract summary generation failed", error=str(exc), exc_info=True)
        
        return {
            "summary": "",
            "summary_type": summary_type,
            "word_count": 0,
            "model_used": "none",
            "metadata": {
                "original_length": len(contract_text),
                "generation_error": str(exc),
                "generation_timestamp": datetime.utcnow().isoformat()
            },
            "success": False,
            "error": str(exc)
        }


@celery_app.task(bind=True, name="app.tasks.llm_tasks.extract_contract_entities")
def extract_contract_entities(
    self,
    contract_text: str,
    entity_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Extract entities from contract text using AI models.
    
    Args:
        contract_text: Contract content to analyze
        entity_types: Specific entity types to extract
        
    Returns:
        Dict: Extracted entities and metadata
    """
    try:
        logger.info(
            "Starting contract entity extraction",
            text_length=len(contract_text),
            entity_types=entity_types
        )
        
        # Default entity types for real estate contracts
        if not entity_types:
            entity_types = [
                "parties", "properties", "dates", "amounts", "addresses",
                "legal_descriptions", "contingencies", "deadlines"
            ]
        
        # Prepare extraction prompt
        prompt = f"""
        Extract the following entities from this real estate contract:
        {', '.join(entity_types)}
        
        Return the results in JSON format with each entity type as a key and a list of found entities as values.
        Include confidence scores and locations in the text where possible.
        
        Contract:
        {contract_text}
        """
        
        # Extract entities using available AI model
        if openai_client:
            start_time = datetime.utcnow()
            
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured information from real estate contracts. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            entities_text = response.choices[0].message.content
            model_used = "gpt-4"
            
        else:
            raise ValueError("No AI models available for entity extraction")
        
        # Parse JSON response
        try:
            entities = json.loads(entities_text)
        except json.JSONDecodeError:
            # Fallback parsing if JSON is malformed
            entities = {"parsing_error": "Could not parse AI response as JSON"}
        
        results = {
            "entities": entities,
            "entity_types": entity_types,
            "model_used": model_used,
            "metadata": {
                "original_length": len(contract_text),
                "processing_time": processing_time,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "total_entities": sum(len(v) if isinstance(v, list) else 1 for v in entities.values())
            },
            "success": True
        }
        
        logger.info(
            "Contract entity extraction completed",
            entity_count=results["metadata"]["total_entities"],
            processing_time=processing_time
        )
        
        return results
        
    except Exception as exc:
        logger.error("Contract entity extraction failed", error=str(exc), exc_info=True)
        
        return {
            "entities": {},
            "entity_types": entity_types or [],
            "model_used": "none",
            "metadata": {
                "original_length": len(contract_text),
                "extraction_error": str(exc),
                "extraction_timestamp": datetime.utcnow().isoformat()
            },
            "success": False,
            "error": str(exc)
        }
