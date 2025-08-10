"""
Enhanced Conversation Service for AI Assistant Agent

This service provides natural language processing and intelligent conversation
capabilities for the AI Assistant Agent, enabling:
- Natural conversation flow
- Contextual greetings with user personalization
- Intelligent task interpretation
- Proactive follow-up questions
- Context awareness and memory
- Task orchestration and workflow management
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from ..core.logging import get_logger
from ..models.user import User
from .model_router import ModelRouter, ModelRequest

logger = get_logger(__name__)


class ConversationIntent(Enum):
    """Types of conversation intents."""
    GREETING = "greeting"
    TASK_REQUEST = "task_request"
    QUESTION = "question"
    FOLLOW_UP = "follow_up"
    CASUAL = "casual"
    MULTI_TASK = "multi_task"
    STATUS_CHECK = "status_check"
    CLARIFICATION = "clarification"


class ConversationTone(Enum):
    """Conversation tone types."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    URGENT = "urgent"
    CASUAL = "casual"


@dataclass
class ConversationContext:
    """Context information for conversation."""
    user: Optional[User] = None
    current_page: str = "dashboard"
    recent_messages: List[Dict[str, Any]] = None
    active_tasks: List[str] = None
    available_files: List[str] = None
    conversation_history: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.recent_messages is None:
            self.recent_messages = []
        if self.active_tasks is None:
            self.active_tasks = []
        if self.available_files is None:
            self.available_files = []
        if self.conversation_history is None:
            self.conversation_history = []


@dataclass
class ConversationResponse:
    """Response from conversation processing."""
    content: str
    intent: ConversationIntent
    tone: ConversationTone
    suggested_actions: List[Dict[str, Any]] = None
    follow_up_questions: List[str] = None
    requires_clarification: bool = False
    task_breakdown: List[Dict[str, Any]] = None
    confidence: float = 0.8

    def __post_init__(self):
        if self.suggested_actions is None:
            self.suggested_actions = []
        if self.follow_up_questions is None:
            self.follow_up_questions = []
        if self.task_breakdown is None:
            self.task_breakdown = []


class ConversationService:
    """Enhanced conversation service for natural AI interactions."""

    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        self.greeting_patterns = [
            r'\b(hello|hi|hey|good\s+(morning|afternoon|evening)|greetings)\b',
            r'\b(what\'s\s+up|how\s+are\s+you|howdy)\b',
            r'\b(start|begin|let\'s\s+get\s+started)\b'
        ]
        self.task_patterns = [
            r'\b(fill|complete|generate|create)\s+(contract|agreement|document)\b',
            r'\b(extract|get|find)\s+(information|data|details)\b',
            r'\b(send|submit)\s+for\s+(signature|review|approval)\b',
            r'\b(search|look\s+for|find)\s+(file|document|contract)\b',
            r'\b(help\s+me|assist\s+me|can\s+you)\b'
        ]
        self.multi_task_patterns = [
            r'\b(let\'s\s+get\s+to\s+work|do\s+.+\s+and\s+.+|first\s+.+\s+then\s+.+)\b',
            r'\b(step\s+\d+|task\s+\d+|next\s+.+|after\s+that)\b'
        ]

    async def process_message(
        self,
        message: str,
        context: ConversationContext
    ) -> ConversationResponse:
        """
        Process a user message and generate an intelligent response.

        Args:
            message: User's message
            context: Conversation context

        Returns:
            ConversationResponse: Intelligent response with actions
        """
        try:
            # Analyze message intent
            intent = self._analyze_intent(message, context)

            # Generate appropriate response based on intent
            if intent == ConversationIntent.GREETING:
                return await self._handle_greeting(message, context)
            elif intent == ConversationIntent.TASK_REQUEST:
                return await self._handle_task_request(message, context)
            elif intent == ConversationIntent.MULTI_TASK:
                return await self._handle_multi_task_request(message, context)
            elif intent == ConversationIntent.QUESTION:
                return await self._handle_question(message, context)
            elif intent == ConversationIntent.STATUS_CHECK:
                return await self._handle_status_check(message, context)
            else:
                return await self._handle_general_conversation(message, context)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return ConversationResponse(
                content="I apologize, but I encountered an error processing your message. Could you please try rephrasing your request?",
                intent=ConversationIntent.CLARIFICATION,
                tone=ConversationTone.PROFESSIONAL,
                requires_clarification=True
            )

    def _analyze_intent(self, message: str, context: ConversationContext) -> ConversationIntent:
        """Analyze the intent of a user message."""
        message_lower = message.lower()

        # Check for greetings
        for pattern in self.greeting_patterns:
            if re.search(pattern, message_lower):
                return ConversationIntent.GREETING

        # Check for multi-task requests
        for pattern in self.multi_task_patterns:
            if re.search(pattern, message_lower):
                return ConversationIntent.MULTI_TASK

        # Check for task requests
        for pattern in self.task_patterns:
            if re.search(pattern, message_lower):
                return ConversationIntent.TASK_REQUEST

        # Check for status/progress questions
        if any(word in message_lower for word in ['status', 'progress', 'done', 'finished', 'complete']):
            return ConversationIntent.STATUS_CHECK

        # Check for questions
        if message.strip().endswith('?') or any(word in message_lower for word in ['what', 'how', 'when', 'where', 'why', 'can you']):
            return ConversationIntent.QUESTION

        return ConversationIntent.CASUAL

    async def _handle_greeting(self, message: str, context: ConversationContext) -> ConversationResponse:
        """Handle greeting messages with personalization."""
        user_name = context.user.name if context.user else "there"

        # Determine time-based greeting
        current_hour = datetime.now().hour
        if current_hour < 12:
            time_greeting = "Good morning"
        elif current_hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"

        # Create personalized greeting
        greeting_content = f"{time_greeting}, {user_name}! I'm your AI Assistant Agent, ready to help you with your real estate contracts and workflows."

        # Add context-aware suggestions
        suggestions = []
        if context.available_files:
            suggestions.append({
                "action": "fill_contract",
                "description": f"Fill out a contract using your {len(context.available_files)} available files",
                "icon": "📄"
            })

        suggestions.extend([
            {
                "action": "extract_info",
                "description": "Extract information from documents",
                "icon": "🔍"
            },
            {
                "action": "search_files",
                "description": "Search through your files and contracts",
                "icon": "📁"
            }
        ])

        content = f"{greeting_content}\n\n**What would you like to accomplish today?**\n\n"
        content += "I can help you with:\n"
        for suggestion in suggestions:
            content += f"• {suggestion['icon']} {suggestion['description']}\n"

        content += "\nJust tell me what you'd like to do, and I'll take care of it!"

        return ConversationResponse(
            content=content,
            intent=ConversationIntent.GREETING,
            tone=ConversationTone.FRIENDLY,
            suggested_actions=suggestions
        )

    async def _handle_task_request(self, message: str, context: ConversationContext) -> ConversationResponse:
        """Handle single task requests with intelligent interpretation."""
        # Use AI to interpret the task request
        task_analysis = await self._analyze_task_with_ai(message, context)

        if task_analysis.get('requires_clarification', False):
            return ConversationResponse(
                content=task_analysis['response'],
                intent=ConversationIntent.CLARIFICATION,
                tone=ConversationTone.PROFESSIONAL,
                requires_clarification=True,
                follow_up_questions=task_analysis.get('clarification_questions', [])
            )

        return ConversationResponse(
            content=task_analysis['response'],
            intent=ConversationIntent.TASK_REQUEST,
            tone=ConversationTone.PROFESSIONAL,
            suggested_actions=task_analysis.get('actions', []),
            task_breakdown=task_analysis.get('task_breakdown', [])
        )

    async def _handle_multi_task_request(self, message: str, context: ConversationContext) -> ConversationResponse:
        """Handle complex multi-task requests with orchestration."""
        # Use AI to break down the multi-task request
        task_breakdown = await self._break_down_multi_task_with_ai(message, context)

        content = f"I understand you want me to handle multiple tasks. Let me break this down:\n\n"

        for i, task in enumerate(task_breakdown.get('tasks', []), 1):
            content += f"**Step {i}: {task['title']}**\n"
            content += f"• {task['description']}\n"
            if task.get('estimated_time'):
                content += f"• Estimated time: {task['estimated_time']}\n"
            content += "\n"

        content += "I'll execute these tasks in sequence and provide updates as I complete each step. "
        content += "Would you like me to proceed with this plan?"

        return ConversationResponse(
            content=content,
            intent=ConversationIntent.MULTI_TASK,
            tone=ConversationTone.PROFESSIONAL,
            task_breakdown=task_breakdown.get('tasks', []),
            requires_clarification=task_breakdown.get('requires_confirmation', True)
        )

    async def _handle_question(self, message: str, context: ConversationContext) -> ConversationResponse:
        """Handle questions with intelligent responses."""
        # Use AI to generate contextual answer
        answer = await self._generate_contextual_answer(message, context)

        return ConversationResponse(
            content=answer['response'],
            intent=ConversationIntent.QUESTION,
            tone=ConversationTone.PROFESSIONAL,
            follow_up_questions=answer.get('follow_up_questions', []),
            suggested_actions=answer.get('suggested_actions', [])
        )

    async def _handle_status_check(self, message: str, context: ConversationContext) -> ConversationResponse:
        """Handle status and progress check requests."""
        status_info = self._get_current_status(context)

        content = "**Current Status Update:**\n\n"

        if context.active_tasks:
            content += f"**Active Tasks:** {len(context.active_tasks)} in progress\n"
            for task in context.active_tasks[:3]:  # Show first 3 tasks
                content += f"• {task}\n"
            if len(context.active_tasks) > 3:
                content += f"• ... and {len(context.active_tasks) - 3} more\n"
        else:
            content += "**Active Tasks:** No tasks currently running\n"

        content += f"\n**Available Files:** {len(context.available_files)} files ready for processing\n"
        content += f"**Current Page:** {context.current_page.title()}\n"

        if context.recent_messages:
            content += f"\n**Recent Activity:** Last interaction {len(context.recent_messages)} messages ago\n"

        content += "\nWhat would you like me to help you with next?"

        return ConversationResponse(
            content=content,
            intent=ConversationIntent.STATUS_CHECK,
            tone=ConversationTone.PROFESSIONAL
        )

    async def _handle_general_conversation(self, message: str, context: ConversationContext) -> ConversationResponse:
        """Handle general conversation with AI assistance."""
        # Use AI to generate appropriate response
        response = await self._generate_general_response(message, context)

        return ConversationResponse(
            content=response['content'],
            intent=ConversationIntent.CASUAL,
            tone=ConversationTone.FRIENDLY,
            suggested_actions=response.get('suggested_actions', [])
        )

    async def _analyze_task_with_ai(self, message: str, context: ConversationContext) -> Dict[str, Any]:
        """Use AI to analyze and interpret task requests."""
        system_prompt = """You are an AI assistant specializing in real estate contract workflows.
        Analyze the user's task request and provide a structured response.

        Consider the available context:
        - Available files for processing
        - Current page/workflow context
        - User's role and permissions

        Respond with JSON containing:
        - response: Clear acknowledgment and next steps
        - requires_clarification: boolean if more info needed
        - clarification_questions: list of specific questions if clarification needed
        - actions: list of suggested actions with type and parameters
        - task_breakdown: list of steps if complex task
        """

        context_info = {
            "message": message,
            "current_page": context.current_page,
            "available_files": context.available_files,
            "user_role": context.user.role if context.user else "unknown"
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this task request: {json.dumps(context_info)}"}
        ]

        try:
            request = ModelRequest(
                messages=messages,
                model_preference="gpt-4",
                max_tokens=1000,
                temperature=0.1
            )

            response = await self.model_router.generate_response(request)
            return json.loads(response.content)

        except Exception as e:
            logger.error(f"AI task analysis failed: {e}")
            return {
                "response": "I understand you want me to help with a task. Could you provide more specific details about what you'd like me to do?",
                "requires_clarification": True,
                "clarification_questions": [
                    "What type of contract or document are you working with?",
                    "What specific action would you like me to perform?",
                    "Are there particular files I should use?"
                ]
            }

    async def _break_down_multi_task_with_ai(self, message: str, context: ConversationContext) -> Dict[str, Any]:
        """Use AI to break down complex multi-task requests."""
        system_prompt = """You are an AI assistant that breaks down complex multi-task requests into manageable steps.

        Analyze the user's request and create a structured task breakdown with:
        - Clear sequence of tasks
        - Dependencies between tasks
        - Estimated completion times
        - Required resources/files

        Respond with JSON containing:
        - tasks: list of task objects with title, description, estimated_time, dependencies
        - requires_confirmation: boolean if user should confirm the plan
        - total_estimated_time: overall time estimate
        """

        context_info = {
            "message": message,
            "current_page": context.current_page,
            "available_files": context.available_files,
            "active_tasks": context.active_tasks
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Break down this multi-task request: {json.dumps(context_info)}"}
        ]

        try:
            request = ModelRequest(
                messages=messages,
                model_preference="gpt-4",
                max_tokens=1500,
                temperature=0.1
            )

            response = await self.model_router.generate_response(request)
            return json.loads(response.content)

        except Exception as e:
            logger.error(f"AI multi-task breakdown failed: {e}")
            return {
                "tasks": [
                    {
                        "title": "Analyze Request",
                        "description": "Review and understand the complete request",
                        "estimated_time": "1-2 minutes"
                    },
                    {
                        "title": "Execute Tasks",
                        "description": "Perform the requested actions in sequence",
                        "estimated_time": "5-10 minutes"
                    }
                ],
                "requires_confirmation": True,
                "total_estimated_time": "6-12 minutes"
            }

    async def _generate_contextual_answer(self, message: str, context: ConversationContext) -> Dict[str, Any]:
        """Generate contextual answers to user questions."""
        system_prompt = """You are an AI assistant specializing in real estate contracts and workflows.
        Provide helpful, accurate answers to user questions based on the available context.

        Consider:
        - User's current workflow context
        - Available files and resources
        - Real estate industry best practices

        Respond with JSON containing:
        - response: Clear, helpful answer
        - follow_up_questions: list of related questions user might have
        - suggested_actions: list of actions user might want to take next
        """

        context_info = {
            "question": message,
            "current_page": context.current_page,
            "available_files": context.available_files,
            "recent_activity": context.recent_messages[-3:] if context.recent_messages else []
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Answer this question: {json.dumps(context_info)}"}
        ]

        try:
            request = ModelRequest(
                messages=messages,
                model_preference="gpt-4",
                max_tokens=800,
                temperature=0.2
            )

            response = await self.model_router.generate_response(request)
            return json.loads(response.content)

        except Exception as e:
            logger.error(f"AI contextual answer failed: {e}")
            return {
                "response": "I'd be happy to help answer your question. Could you provide a bit more context about what specific information you're looking for?",
                "follow_up_questions": [
                    "What specific aspect would you like me to explain?",
                    "Are you looking for information about a particular contract type?",
                    "Would you like me to search through your available files?"
                ]
            }

    async def _generate_general_response(self, message: str, context: ConversationContext) -> Dict[str, Any]:
        """Generate appropriate responses for general conversation."""
        system_prompt = """You are a friendly, professional AI assistant for real estate workflows.
        Respond naturally to casual conversation while staying focused on how you can help with real estate tasks.

        Keep responses:
        - Professional but approachable
        - Focused on real estate workflows
        - Helpful and action-oriented

        Respond with JSON containing:
        - content: Natural, helpful response
        - suggested_actions: optional list of relevant actions
        """

        context_info = {
            "message": message,
            "current_page": context.current_page,
            "user_name": context.user.name if context.user else "there"
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Respond to this message: {json.dumps(context_info)}"}
        ]

        try:
            request = ModelRequest(
                messages=messages,
                model_preference="gpt-4",
                max_tokens=500,
                temperature=0.3
            )

            response = await self.model_router.generate_response(request)
            return json.loads(response.content)

        except Exception as e:
            logger.error(f"AI general response failed: {e}")
            return {
                "content": "I'm here to help you with your real estate contract workflows. What would you like to work on today?",
                "suggested_actions": [
                    {"action": "fill_contract", "description": "Fill out a contract"},
                    {"action": "extract_info", "description": "Extract information from documents"},
                    {"action": "search_files", "description": "Search through your files"}
                ]
            }

    def _get_current_status(self, context: ConversationContext) -> Dict[str, Any]:
        """Get current status information."""
        return {
            "active_tasks": len(context.active_tasks),
            "available_files": len(context.available_files),
            "current_page": context.current_page,
            "recent_messages": len(context.recent_messages)
        }

    def extract_user_preferences(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract user preferences from conversation history."""
        preferences = {
            "preferred_contract_types": [],
            "common_workflows": [],
            "communication_style": "professional",
            "typical_file_sources": []
        }

        # Analyze conversation history for patterns
        for message in conversation_history:
            if message.get('type') == 'user':
                content = message.get('content', '').lower()

                # Extract contract type preferences
                if 'purchase agreement' in content:
                    preferences['preferred_contract_types'].append('purchase_agreement')
                elif 'listing agreement' in content:
                    preferences['preferred_contract_types'].append('listing_agreement')

                # Extract communication style
                if any(word in content for word in ['please', 'thank you', 'appreciate']):
                    preferences['communication_style'] = 'polite'
                elif any(word in content for word in ['quick', 'fast', 'asap', 'urgent']):
                    preferences['communication_style'] = 'direct'

        return preferences
