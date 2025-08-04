"""
Enhanced Help Agent Tools.

This module provides specialized tools for the Enhanced Help Agent,
including contextual Q&A, workflow guidance, and knowledge base management.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import structlog
from pydantic import BaseModel, Field

from .base import BaseTool, ToolInput, ToolResult, ToolCategory
from ...core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ContextualQAInput(ToolInput):
    """Input for contextual Q&A tool."""
    question: str = Field(..., description="User question")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Context data")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="Previous conversation")
    qa_options: Dict[str, Any] = Field(default_factory=dict, description="Q&A options")


class WorkflowGuidanceInput(ToolInput):
    """Input for workflow guidance tool."""
    current_step: str = Field(..., description="Current workflow step")
    workflow_type: str = Field(..., description="Type of workflow")
    user_progress: Dict[str, Any] = Field(default_factory=dict, description="User progress data")
    guidance_options: Dict[str, Any] = Field(default_factory=dict, description="Guidance options")


class KnowledgeBaseInput(ToolInput):
    """Input for knowledge base tool."""
    query: str = Field(..., description="Knowledge base query")
    knowledge_domain: str = Field(default="real_estate", description="Knowledge domain")
    search_options: Dict[str, Any] = Field(default_factory=dict, description="Search options")


class ClauseExplanationInput(ToolInput):
    """Input for clause explanation tool."""
    clause_text: str = Field(..., description="Clause text to explain")
    clause_type: str = Field(default="unknown", description="Type of clause")
    explanation_level: str = Field(default="intermediate", description="Explanation complexity level")


class ContextualQATool(BaseTool):
    """Tool for providing contextual Q&A with deal-specific knowledge."""
    
    @property
    def name(self) -> str:
        return "contextual_qa"
    
    @property
    def description(self) -> str:
        return "Provide contextual answers to questions using deal-specific knowledge and conversation history"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.KNOWLEDGE_BASE
    
    async def execute(self, input_data: ContextualQAInput) -> ToolResult:
        """Provide contextual answer to user question."""
        try:
            # Analyze question intent
            question_analysis = await self._analyze_question_intent(
                input_data.question,
                input_data.context_data
            )
            
            # Search relevant knowledge
            relevant_knowledge = await self._search_relevant_knowledge(
                input_data.question,
                question_analysis,
                input_data.context_data
            )
            
            # Generate contextual answer
            answer = await self._generate_contextual_answer(
                input_data.question,
                relevant_knowledge,
                input_data.context_data,
                input_data.conversation_history
            )
            
            # Generate follow-up suggestions
            follow_ups = await self._generate_follow_up_suggestions(
                input_data.question,
                answer,
                input_data.context_data
            )
            
            return ToolResult(
                success=True,
                data={
                    "question": input_data.question,
                    "answer": answer,
                    "question_analysis": question_analysis,
                    "relevant_knowledge": relevant_knowledge,
                    "follow_up_suggestions": follow_ups,
                    "confidence_score": answer.get("confidence", 0.8)
                },
                metadata={
                    "response_timestamp": datetime.utcnow().isoformat(),
                    "knowledge_sources": relevant_knowledge.get("sources", []),
                    "context_used": bool(input_data.context_data)
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Contextual Q&A failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )
    
    async def _analyze_question_intent(self, 
                                     question: str,
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the intent and type of the user's question."""
        question_lower = question.lower()
        
        # Question type classification
        question_types = {
            "definition": ["what is", "define", "meaning of", "explain"],
            "process": ["how to", "how do", "steps", "process"],
            "status": ["status", "where are we", "current", "progress"],
            "timeline": ["when", "deadline", "timeline", "schedule"],
            "requirements": ["required", "need", "must", "necessary"],
            "troubleshooting": ["problem", "issue", "error", "wrong", "fix"],
            "comparison": ["difference", "compare", "versus", "vs", "better"],
            "recommendation": ["should", "recommend", "suggest", "best"]
        }
        
        detected_types = []
        for q_type, keywords in question_types.items():
            if any(keyword in question_lower for keyword in keywords):
                detected_types.append(q_type)
        
        # Domain classification
        domains = {
            "legal": ["legal", "law", "contract", "clause", "liability", "warranty"],
            "financial": ["price", "cost", "payment", "loan", "mortgage", "financing"],
            "process": ["workflow", "step", "procedure", "process", "next"],
            "technical": ["system", "platform", "feature", "function", "tool"],
            "timeline": ["date", "deadline", "schedule", "timeline", "when"]
        }
        
        detected_domains = []
        for domain, keywords in domains.items():
            if any(keyword in question_lower for keyword in keywords):
                detected_domains.append(domain)
        
        return {
            "question_types": detected_types or ["general"],
            "domains": detected_domains or ["general"],
            "complexity": self._assess_question_complexity(question),
            "requires_context": self._requires_context_data(question, context),
            "urgency": self._assess_question_urgency(question)
        }
    
    def _assess_question_complexity(self, question: str) -> str:
        """Assess the complexity level of the question."""
        if len(question.split()) > 20 or "?" in question[:-1]:  # Multiple questions
            return "complex"
        elif len(question.split()) > 10:
            return "moderate"
        else:
            return "simple"
    
    def _requires_context_data(self, question: str, context: Dict[str, Any]) -> bool:
        """Determine if the question requires context data to answer properly."""
        context_indicators = ["this", "current", "my", "our", "the contract", "this deal"]
        return any(indicator in question.lower() for indicator in context_indicators)
    
    def _assess_question_urgency(self, question: str) -> str:
        """Assess the urgency level of the question."""
        urgent_keywords = ["urgent", "asap", "immediately", "deadline", "problem", "issue"]
        if any(keyword in question.lower() for keyword in urgent_keywords):
            return "high"
        elif "?" in question and ("when" in question.lower() or "how long" in question.lower()):
            return "medium"
        else:
            return "low"
    
    async def _search_relevant_knowledge(self, 
                                       question: str,
                                       analysis: Dict[str, Any],
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Search for relevant knowledge to answer the question."""
        # This would integrate with a real knowledge base
        # For now, return mock relevant knowledge
        
        knowledge_base = {
            "contract_basics": {
                "content": "A real estate contract is a legally binding agreement between buyer and seller that outlines the terms and conditions of a property sale.",
                "relevance": 0.9,
                "source": "real_estate_fundamentals"
            },
            "closing_process": {
                "content": "The closing process typically takes 30-45 days and involves loan approval, inspections, appraisal, and final walkthrough.",
                "relevance": 0.8,
                "source": "process_guide"
            },
            "contingencies": {
                "content": "Contingencies are conditions that must be met for the contract to proceed. Common contingencies include financing, inspection, and appraisal.",
                "relevance": 0.85,
                "source": "legal_guide"
            }
        }
        
        # Simple keyword matching for relevance
        question_words = set(question.lower().split())
        relevant_items = []
        
        for item_id, item_data in knowledge_base.items():
            content_words = set(item_data["content"].lower().split())
            overlap = len(question_words.intersection(content_words))
            
            if overlap > 0:
                relevance_score = overlap / len(question_words)
                relevant_items.append({
                    "id": item_id,
                    "content": item_data["content"],
                    "relevance_score": relevance_score,
                    "source": item_data["source"]
                })
        
        # Sort by relevance
        relevant_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return {
            "items": relevant_items[:3],  # Top 3 most relevant
            "sources": list(set(item["source"] for item in relevant_items)),
            "total_found": len(relevant_items)
        }
    
    async def _generate_contextual_answer(self, 
                                        question: str,
                                        knowledge: Dict[str, Any],
                                        context: Dict[str, Any],
                                        history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate a contextual answer using available knowledge and context."""
        # Combine relevant knowledge
        knowledge_content = []
        for item in knowledge.get("items", []):
            knowledge_content.append(item["content"])
        
        # Generate answer based on question type and available information
        if not knowledge_content:
            answer_text = "I don't have specific information about that topic in my knowledge base. Could you provide more details or rephrase your question?"
            confidence = 0.3
        else:
            # Use the most relevant knowledge item as the base answer
            base_answer = knowledge_content[0]
            
            # Enhance with context if available
            if context and self._requires_context_data(question, context):
                context_enhancement = self._add_context_enhancement(base_answer, context)
                answer_text = f"{base_answer}\n\n{context_enhancement}"
                confidence = 0.85
            else:
                answer_text = base_answer
                confidence = 0.75
        
        return {
            "content": answer_text,
            "confidence": confidence,
            "sources_used": len(knowledge.get("items", [])),
            "context_applied": bool(context),
            "answer_type": "informational"
        }
    
    def _add_context_enhancement(self, base_answer: str, context: Dict[str, Any]) -> str:
        """Add context-specific enhancement to the answer."""
        enhancements = []
        
        if "contract_id" in context:
            enhancements.append(f"For your current contract (ID: {context['contract_id']}), this means...")
        
        if "workflow_step" in context:
            enhancements.append(f"At your current step ({context['workflow_step']}), you should...")
        
        if "user_role" in context:
            enhancements.append(f"As a {context['user_role']}, you may want to consider...")
        
        return " ".join(enhancements) if enhancements else "Based on your current situation, this information applies directly to your case."
    
    async def _generate_follow_up_suggestions(self, 
                                            question: str,
                                            answer: Dict[str, Any],
                                            context: Dict[str, Any]) -> List[str]:
        """Generate follow-up question suggestions."""
        suggestions = []
        
        question_lower = question.lower()
        
        if "contract" in question_lower:
            suggestions.extend([
                "What are the key terms I should review in my contract?",
                "How long does the contract review process typically take?",
                "What happens if contingencies are not met?"
            ])
        
        if "closing" in question_lower:
            suggestions.extend([
                "What documents do I need for closing?",
                "How should I prepare for the final walkthrough?",
                "What costs should I expect at closing?"
            ])
        
        if "timeline" in question_lower or "when" in question_lower:
            suggestions.extend([
                "What are the typical milestones in this process?",
                "How can I track the progress of my transaction?",
                "What could cause delays in the timeline?"
            ])
        
        # Limit to 3 most relevant suggestions
        return suggestions[:3]


class WorkflowGuidanceTool(BaseTool):
    """Tool for providing workflow guidance and next-step recommendations."""
    
    @property
    def name(self) -> str:
        return "workflow_guide"
    
    @property
    def description(self) -> str:
        return "Provide workflow guidance and next-step recommendations based on current progress"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WORKFLOW_MANAGEMENT
    
    async def execute(self, input_data: WorkflowGuidanceInput) -> ToolResult:
        """Provide workflow guidance."""
        try:
            # Get workflow definition
            workflow_def = await self._get_workflow_definition(input_data.workflow_type)
            
            # Analyze current progress
            progress_analysis = await self._analyze_progress(
                input_data.current_step,
                input_data.user_progress,
                workflow_def
            )
            
            # Generate next steps
            next_steps = await self._generate_next_steps(
                input_data.current_step,
                progress_analysis,
                workflow_def
            )
            
            # Identify potential issues
            potential_issues = await self._identify_potential_issues(
                progress_analysis,
                workflow_def
            )
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(
                progress_analysis,
                next_steps,
                potential_issues
            )
            
            return ToolResult(
                success=True,
                data={
                    "current_step": input_data.current_step,
                    "workflow_type": input_data.workflow_type,
                    "progress_analysis": progress_analysis,
                    "next_steps": next_steps,
                    "potential_issues": potential_issues,
                    "recommendations": recommendations,
                    "completion_percentage": progress_analysis.get("completion_percentage", 0)
                },
                metadata={
                    "guidance_timestamp": datetime.utcnow().isoformat(),
                    "workflow_version": workflow_def.get("version", "1.0"),
                    "total_steps": len(workflow_def.get("steps", []))
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Workflow guidance failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )
    
    async def _get_workflow_definition(self, workflow_type: str) -> Dict[str, Any]:
        """Get workflow definition for the specified type."""
        # This would load from a workflow definition database
        workflows = {
            "contract_creation": {
                "name": "Contract Creation Workflow",
                "version": "1.0",
                "steps": [
                    {"id": "document_upload", "name": "Upload Documents", "required": True},
                    {"id": "data_extraction", "name": "Extract Data", "required": True},
                    {"id": "template_selection", "name": "Select Template", "required": True},
                    {"id": "contract_generation", "name": "Generate Contract", "required": True},
                    {"id": "compliance_check", "name": "Compliance Review", "required": True},
                    {"id": "signature_setup", "name": "Setup Signatures", "required": True},
                    {"id": "contract_execution", "name": "Execute Contract", "required": True}
                ]
            },
            "contract_review": {
                "name": "Contract Review Workflow",
                "version": "1.0",
                "steps": [
                    {"id": "contract_upload", "name": "Upload Contract", "required": True},
                    {"id": "initial_review", "name": "Initial Review", "required": True},
                    {"id": "compliance_check", "name": "Compliance Check", "required": True},
                    {"id": "legal_review", "name": "Legal Review", "required": False},
                    {"id": "approval", "name": "Final Approval", "required": True}
                ]
            }
        }
        
        return workflows.get(workflow_type, {
            "name": "Unknown Workflow",
            "steps": []
        })
    
    async def _analyze_progress(self, 
                              current_step: str,
                              user_progress: Dict[str, Any],
                              workflow_def: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current workflow progress."""
        steps = workflow_def.get("steps", [])
        
        # Find current step index
        current_step_index = -1
        for i, step in enumerate(steps):
            if step["id"] == current_step:
                current_step_index = i
                break
        
        if current_step_index == -1:
            return {
                "error": "Current step not found in workflow",
                "completion_percentage": 0
            }
        
        # Calculate completion percentage
        completion_percentage = (current_step_index / len(steps)) * 100
        
        # Analyze completed steps
        completed_steps = []
        pending_steps = []
        
        for i, step in enumerate(steps):
            if i < current_step_index:
                completed_steps.append(step)
            elif i > current_step_index:
                pending_steps.append(step)
        
        return {
            "current_step_index": current_step_index,
            "completion_percentage": round(completion_percentage, 1),
            "completed_steps": completed_steps,
            "pending_steps": pending_steps,
            "total_steps": len(steps),
            "is_final_step": current_step_index == len(steps) - 1
        }
    
    async def _generate_next_steps(self, 
                                 current_step: str,
                                 progress: Dict[str, Any],
                                 workflow_def: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate next steps based on current progress."""
        next_steps = []
        
        if progress.get("is_final_step"):
            next_steps.append({
                "action": "Complete workflow",
                "description": "You've reached the final step. Review and finalize your work.",
                "priority": "high",
                "estimated_time": "15 minutes"
            })
        else:
            pending_steps = progress.get("pending_steps", [])
            if pending_steps:
                next_step = pending_steps[0]
                next_steps.append({
                    "action": f"Proceed to {next_step['name']}",
                    "description": f"Complete the {next_step['name']} step",
                    "priority": "high" if next_step.get("required") else "medium",
                    "estimated_time": "30 minutes"
                })
                
                # Add subsequent steps as future actions
                for step in pending_steps[1:3]:  # Next 2 steps
                    next_steps.append({
                        "action": f"Prepare for {step['name']}",
                        "description": f"Upcoming: {step['name']}",
                        "priority": "low",
                        "estimated_time": "TBD"
                    })
        
        return next_steps
    
    async def _identify_potential_issues(self, 
                                       progress: Dict[str, Any],
                                       workflow_def: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify potential issues or blockers."""
        issues = []
        
        # Check for missing required steps
        completed_steps = progress.get("completed_steps", [])
        required_completed = [s for s in completed_steps if s.get("required")]
        
        if len(required_completed) < len(completed_steps):
            issues.append({
                "type": "missing_requirements",
                "severity": "medium",
                "description": "Some completed steps may not meet all requirements",
                "recommendation": "Review previous steps for completeness"
            })
        
        # Check for workflow delays
        completion_percentage = progress.get("completion_percentage", 0)
        if completion_percentage < 50:
            issues.append({
                "type": "progress_delay",
                "severity": "low",
                "description": "Workflow progress is in early stages",
                "recommendation": "Consider setting up regular check-ins to maintain momentum"
            })
        
        return issues
    
    async def _generate_recommendations(self, 
                                      progress: Dict[str, Any],
                                      next_steps: List[Dict[str, Any]],
                                      issues: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Progress-based recommendations
        completion = progress.get("completion_percentage", 0)
        
        if completion < 25:
            recommendations.append("Focus on completing the foundational steps to build momentum")
        elif completion < 75:
            recommendations.append("You're making good progress. Stay focused on the current step")
        else:
            recommendations.append("You're in the final stretch. Pay attention to details for a successful completion")
        
        # Issue-based recommendations
        for issue in issues:
            if issue.get("recommendation"):
                recommendations.append(issue["recommendation"])
        
        # Next step recommendations
        high_priority_steps = [s for s in next_steps if s.get("priority") == "high"]
        if high_priority_steps:
            recommendations.append(f"Prioritize: {high_priority_steps[0]['action']}")
        
        return recommendations[:5]  # Limit to top 5 recommendations


class ClauseExplanationTool(BaseTool):
    """Tool for explaining legal clauses and contract terms."""
    
    @property
    def name(self) -> str:
        return "clause_explainer"
    
    @property
    def description(self) -> str:
        return "Explain legal clauses and contract terms in plain language"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.KNOWLEDGE_BASE
    
    async def execute(self, input_data: ClauseExplanationInput) -> ToolResult:
        """Explain a legal clause in plain language."""
        try:
            # Identify clause type if not provided
            if input_data.clause_type == "unknown":
                clause_type = await self._identify_clause_type(input_data.clause_text)
            else:
                clause_type = input_data.clause_type
            
            # Generate explanation
            explanation = await self._generate_clause_explanation(
                input_data.clause_text,
                clause_type,
                input_data.explanation_level
            )
            
            # Identify key terms
            key_terms = await self._identify_key_terms(input_data.clause_text)
            
            # Generate practical implications
            implications = await self._generate_practical_implications(
                input_data.clause_text,
                clause_type
            )
            
            # Suggest questions to ask
            questions = await self._suggest_questions(clause_type, explanation)
            
            return ToolResult(
                success=True,
                data={
                    "clause_text": input_data.clause_text,
                    "clause_type": clause_type,
                    "explanation": explanation,
                    "key_terms": key_terms,
                    "practical_implications": implications,
                    "suggested_questions": questions,
                    "explanation_level": input_data.explanation_level
                },
                metadata={
                    "explanation_timestamp": datetime.utcnow().isoformat(),
                    "clause_length": len(input_data.clause_text),
                    "complexity_score": self._assess_clause_complexity(input_data.clause_text)
                },
                execution_time=0.0,
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Clause explanation failed: {str(e)}"],
                execution_time=0.0,
                tool_name=self.name
            )
    
    async def _identify_clause_type(self, clause_text: str) -> str:
        """Identify the type of legal clause."""
        clause_text_lower = clause_text.lower()
        
        clause_indicators = {
            "contingency": ["contingent", "subject to", "provided that", "condition"],
            "warranty": ["warranty", "warrant", "guarantee", "represent"],
            "liability": ["liable", "liability", "responsible", "damages"],
            "termination": ["terminate", "termination", "end", "cancel"],
            "payment": ["payment", "pay", "consideration", "amount"],
            "inspection": ["inspect", "inspection", "examine", "review"],
            "financing": ["financing", "loan", "mortgage", "lender"],
            "disclosure": ["disclose", "disclosure", "inform", "notify"],
            "default": ["default", "breach", "violation", "failure"],
            "arbitration": ["arbitration", "arbitrate", "dispute", "mediation"]
        }
        
        for clause_type, indicators in clause_indicators.items():
            if any(indicator in clause_text_lower for indicator in indicators):
                return clause_type
        
        return "general"
    
    async def _generate_clause_explanation(self, 
                                         clause_text: str,
                                         clause_type: str,
                                         level: str) -> Dict[str, Any]:
        """Generate explanation based on clause type and complexity level."""
        explanations = {
            "contingency": {
                "simple": "This clause means the contract depends on certain conditions being met. If these conditions aren't satisfied, you may be able to cancel the contract.",
                "intermediate": "This is a contingency clause that creates conditions that must be fulfilled for the contract to proceed. It protects you by allowing contract cancellation if specific requirements aren't met within the specified timeframe.",
                "advanced": "This contingency clause establishes conditional obligations that must be satisfied for contract performance. It serves as a risk mitigation mechanism, providing legal grounds for contract termination without penalty if the specified conditions precedent are not fulfilled within the stipulated time period."
            },
            "warranty": {
                "simple": "This clause is a promise or guarantee about something. The person making the warranty is saying they'll be responsible if it's not true.",
                "intermediate": "This warranty clause represents a legal promise or guarantee about specific facts or conditions. If the warranty proves false, the warranting party may be liable for damages or other remedies.",
                "advanced": "This warranty provision constitutes a contractual representation and guarantee regarding specific facts, conditions, or performance standards. It creates legal liability for the warrantor if the warranted conditions are breached, potentially triggering damage claims or other contractual remedies."
            }
        }
        
        explanation_text = explanations.get(clause_type, {}).get(level, 
            "This clause contains important legal terms that define rights and obligations under the contract.")
        
        return {
            "text": explanation_text,
            "complexity_level": level,
            "clause_type": clause_type,
            "plain_language_summary": self._create_plain_language_summary(clause_text)
        }
    
    def _create_plain_language_summary(self, clause_text: str) -> str:
        """Create a plain language summary of the clause."""
        # Simple transformation to plain language
        summary = clause_text
        
        # Replace legal jargon with plain language
        replacements = {
            "shall": "will",
            "heretofore": "before this",
            "hereinafter": "from now on",
            "whereas": "since",
            "notwithstanding": "despite",
            "pursuant to": "according to"
        }
        
        for legal_term, plain_term in replacements.items():
            summary = re.sub(rf'\b{legal_term}\b', plain_term, summary, flags=re.IGNORECASE)
        
        return summary
    
    async def _identify_key_terms(self, clause_text: str) -> List[Dict[str, str]]:
        """Identify and define key legal terms in the clause."""
        key_terms = []
        
        # Common legal terms and their definitions
        term_definitions = {
            "contingent": "Dependent on certain conditions being met",
            "warranty": "A promise or guarantee about something",
            "liability": "Legal responsibility for damages or obligations",
            "default": "Failure to meet contractual obligations",
            "breach": "Violation of contract terms",
            "consideration": "Something of value exchanged in a contract",
            "escrow": "Money or documents held by a third party until conditions are met",
            "lien": "A legal claim against property as security for debt"
        }
        
        clause_lower = clause_text.lower()
        for term, definition in term_definitions.items():
            if term in clause_lower:
                key_terms.append({
                    "term": term,
                    "definition": definition
                })
        
        return key_terms
    
    async def _generate_practical_implications(self, 
                                             clause_text: str,
                                             clause_type: str) -> List[str]:
        """Generate practical implications of the clause."""
        implications = []
        
        if clause_type == "contingency":
            implications.extend([
                "You have the right to cancel if conditions aren't met",
                "Make sure you understand the timeline for meeting conditions",
                "Consider what happens to your earnest money if you cancel"
            ])
        elif clause_type == "warranty":
            implications.extend([
                "The other party is legally promising something is true",
                "You may have recourse if the warranty is breached",
                "Document any warranty claims promptly"
            ])
        elif clause_type == "liability":
            implications.extend([
                "This defines who is responsible for what",
                "Understand your potential financial exposure",
                "Consider insurance coverage for liability risks"
            ])
        else:
            implications.append("Review this clause carefully with your attorney if you have questions")
        
        return implications
    
    async def _suggest_questions(self, 
                               clause_type: str,
                               explanation: Dict[str, Any]) -> List[str]:
        """Suggest questions the user should ask about this clause."""
        questions = []
        
        if clause_type == "contingency":
            questions.extend([
                "What exactly needs to happen to satisfy this contingency?",
                "What is the deadline for meeting this condition?",
                "What happens if the contingency isn't met?"
            ])
        elif clause_type == "warranty":
            questions.extend([
                "What specific things are being warranted?",
                "How long does this warranty last?",
                "What remedies do I have if the warranty is breached?"
            ])
        else:
            questions.extend([
                "What are my obligations under this clause?",
                "What are the consequences if this clause is violated?",
                "Should I have my attorney review this clause?"
            ])
        
        return questions
    
    def _assess_clause_complexity(self, clause_text: str) -> float:
        """Assess the complexity of the clause text."""
        # Simple complexity scoring based on length and legal terms
        word_count = len(clause_text.split())
        legal_terms = ["whereas", "heretofore", "notwithstanding", "pursuant", "shall"]
        legal_term_count = sum(1 for term in legal_terms if term in clause_text.lower())
        
        # Normalize scores
        length_score = min(word_count / 100, 1.0)  # Normalize to 0-1
        legal_score = min(legal_term_count / 5, 1.0)  # Normalize to 0-1
        
        complexity = (length_score + legal_score) / 2
        return round(complexity, 2)
