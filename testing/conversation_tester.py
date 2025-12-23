"""
Peptide AI - Automated Conversation Testing

Simulates realistic conversations with different personas,
evaluates responses, and generates actionable feedback.
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import httpx
from dotenv import load_dotenv
import openai

from personas import (
    PERSONAS, Persona, get_random_persona,
    generate_conversation_starter, generate_follow_up
)

# Load .env from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """A single turn in a conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str


@dataclass
class ConversationEvaluation:
    """Evaluation of a single conversation"""
    persona_name: str
    conversation_id: str
    turns: List[ConversationTurn]
    scores: Dict[str, int]  # 1-10 scores for different criteria
    strengths: List[str]
    weaknesses: List[str]
    specific_feedback: str
    would_persona_return: bool
    suggested_improvements: List[str]


@dataclass
class TestResult:
    """Result of a complete test run"""
    test_id: str
    timestamp: str
    total_conversations: int
    evaluations: List[ConversationEvaluation]
    aggregate_scores: Dict[str, float]
    top_issues: List[str]
    top_strengths: List[str]
    recommendations: List[str]


class ConversationTester:
    """
    Automated conversation testing system

    Simulates realistic user conversations and evaluates responses
    using LLM-based evaluation.
    """

    def __init__(
        self,
        api_url: str = None,
        api_key: str = None,
        openai_api_key: str = None
    ):
        self.api_url = api_url or os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("PEPTIDE_AI_MASTER_KEY", "test-key")
        self.openai_client = openai.AsyncOpenAI(
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
        )
        self.results: List[ConversationEvaluation] = []

    async def run_conversation(
        self,
        persona: Persona,
        num_turns: int = 4
    ) -> List[ConversationTurn]:
        """
        Run a simulated conversation with a persona
        """
        conversation: List[ConversationTurn] = []
        history = []

        # Generate initial message based on persona
        first_message = await self._generate_persona_message(
            persona,
            conversation_context=[],
            is_first_message=True
        )

        for turn in range(num_turns):
            # User message
            if turn == 0:
                user_message = first_message
            else:
                user_message = await self._generate_persona_message(
                    persona,
                    conversation_context=conversation,
                    is_first_message=False
                )

            conversation.append(ConversationTurn(
                role="user",
                content=user_message,
                timestamp=datetime.utcnow().isoformat()
            ))
            history.append({"role": "user", "content": user_message})

            # Get assistant response
            try:
                assistant_response = await self._get_chat_response(
                    message=user_message,
                    history=history[:-1]  # Don't include current message in history
                )

                conversation.append(ConversationTurn(
                    role="assistant",
                    content=assistant_response,
                    timestamp=datetime.utcnow().isoformat()
                ))
                history.append({"role": "assistant", "content": assistant_response})

            except Exception as e:
                logger.error(f"Error getting response: {e}")
                conversation.append(ConversationTurn(
                    role="assistant",
                    content=f"[ERROR: {str(e)}]",
                    timestamp=datetime.utcnow().isoformat()
                ))
                break

        return conversation

    async def _generate_persona_message(
        self,
        persona: Persona,
        conversation_context: List[ConversationTurn],
        is_first_message: bool
    ) -> str:
        """Generate a realistic message from the persona using LLM"""

        context_str = ""
        if conversation_context:
            context_str = "\n".join([
                f"{turn.role.upper()}: {turn.content[:200]}..."
                for turn in conversation_context[-4:]
            ])

        prompt = f"""You are simulating a user named {persona.name} chatting with a peptide research AI.

PERSONA PROFILE:
- Knowledge Level: {persona.knowledge_level.value}
- Attitude: {persona.attitude.value}
- Communication Style: {persona.communication_style.value}
- Goals: {', '.join(persona.primary_goals)}
- Health Conditions: {', '.join(persona.health_conditions)}
- Background: {persona.background}

EXAMPLE QUESTIONS THIS PERSONA WOULD ASK:
{chr(10).join('- ' + q for q in persona.typical_questions[:3])}

FOLLOW-UP PATTERNS:
{chr(10).join('- ' + p for p in persona.follow_up_patterns[:3])}

{"CONVERSATION SO FAR:" + chr(10) + context_str if context_str else "This is the START of the conversation."}

Generate a {'first message' if is_first_message else 'follow-up message'} that this persona would realistically send.
{'The message should introduce their situation and ask their main question.' if is_first_message else 'The message should follow up on the previous response - ask for clarification, dig deeper, or move to a related topic.'}

Match their communication style ({persona.communication_style.value}) and attitude ({persona.attitude.value}).

Respond with ONLY the message, no quotes or explanation."""

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=300
        )

        return response.choices[0].message.content.strip()

    async def _get_chat_response(
        self,
        message: str,
        history: List[Dict[str, str]]
    ) -> str:
        """Get response from the Peptide AI chat API"""

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.api_url}/api/v1/chat",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key
                },
                json={
                    "message": message,
                    "history": history
                }
            )

            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")

            data = response.json()
            return data.get("message", data.get("response", ""))

    async def evaluate_conversation(
        self,
        persona: Persona,
        conversation: List[ConversationTurn]
    ) -> ConversationEvaluation:
        """Evaluate a conversation from the persona's perspective"""

        conv_text = "\n\n".join([
            f"{'USER' if turn.role == 'user' else 'ASSISTANT'}: {turn.content}"
            for turn in conversation
        ])

        eval_prompt = f"""You are evaluating a conversation between a user and Peptide AI from the USER's perspective.

THE USER'S PERSONA:
- Name: {persona.name}
- Knowledge Level: {persona.knowledge_level.value}
- Attitude: {persona.attitude.value}
- Goals: {', '.join(persona.primary_goals)}
- Health Conditions: {', '.join(persona.health_conditions)}
- Background: {persona.background}

WHAT WOULD SATISFY THIS USER:
{chr(10).join('- ' + c for c in persona.success_criteria)}

WHAT WOULD FRUSTRATE THIS USER:
{chr(10).join('- ' + t for t in persona.frustration_triggers)}

THE CONVERSATION:
{conv_text}

Evaluate this conversation from {persona.name}'s perspective. Be critical but fair.

Return a JSON object with:
{{
    "scores": {{
        "relevance": <1-10, did it address their specific situation?>,
        "helpfulness": <1-10, did it give actionable information?>,
        "accuracy": <1-10, was the information correct and well-sourced?>,
        "tone": <1-10, was the tone appropriate for this user?>,
        "conversation_memory": <1-10, did it remember context from earlier messages?>,
        "formatting": <1-10, was it easy to read and well-structured?>,
        "depth": <1-10, did it go deep enough vs. too shallow?>,
        "safety_balance": <1-10, balanced safety info without being preachy?>
    }},
    "strengths": ["strength1", "strength2", "strength3"],
    "weaknesses": ["weakness1", "weakness2", "weakness3"],
    "specific_feedback": "2-3 sentences of specific feedback from this persona's voice",
    "would_return": true/false,
    "improvements": ["specific improvement 1", "specific improvement 2", "specific improvement 3"]
}}

Return ONLY the JSON, no markdown."""

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": eval_prompt}],
            temperature=0.3,
            max_tokens=1000
        )

        try:
            eval_data = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            content = response.choices[0].message.content
            start = content.find('{')
            end = content.rfind('}') + 1
            eval_data = json.loads(content[start:end])

        return ConversationEvaluation(
            persona_name=persona.name,
            conversation_id=f"{persona.name}-{datetime.utcnow().timestamp()}",
            turns=conversation,
            scores=eval_data.get("scores", {}),
            strengths=eval_data.get("strengths", []),
            weaknesses=eval_data.get("weaknesses", []),
            specific_feedback=eval_data.get("specific_feedback", ""),
            would_persona_return=eval_data.get("would_return", False),
            suggested_improvements=eval_data.get("improvements", [])
        )

    async def run_test_batch(
        self,
        num_conversations: int = 10,
        turns_per_conversation: int = 4,
        personas: Optional[List[Persona]] = None
    ) -> TestResult:
        """Run a batch of test conversations"""

        test_id = f"test-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        logger.info(f"Starting test batch {test_id} with {num_conversations} conversations")

        if personas is None:
            personas = PERSONAS

        evaluations: List[ConversationEvaluation] = []

        for i in range(num_conversations):
            persona = random.choice(personas)
            logger.info(f"[{i+1}/{num_conversations}] Testing with {persona.name}")

            try:
                # Run conversation
                conversation = await self.run_conversation(
                    persona=persona,
                    num_turns=turns_per_conversation
                )

                # Evaluate
                evaluation = await self.evaluate_conversation(persona, conversation)
                evaluations.append(evaluation)

                # Log progress
                avg_score = sum(evaluation.scores.values()) / len(evaluation.scores) if evaluation.scores else 0
                logger.info(f"  Average score: {avg_score:.1f}/10, Would return: {evaluation.would_persona_return}")

            except Exception as e:
                logger.error(f"  Error in conversation: {e}")
                continue

            # Small delay to avoid rate limits
            await asyncio.sleep(1)

        # Aggregate results
        result = self._aggregate_results(test_id, evaluations)

        return result

    def _aggregate_results(
        self,
        test_id: str,
        evaluations: List[ConversationEvaluation]
    ) -> TestResult:
        """Aggregate evaluation results"""

        if not evaluations:
            return TestResult(
                test_id=test_id,
                timestamp=datetime.utcnow().isoformat(),
                total_conversations=0,
                evaluations=[],
                aggregate_scores={},
                top_issues=[],
                top_strengths=[],
                recommendations=[]
            )

        # Calculate aggregate scores
        score_totals: Dict[str, List[int]] = {}
        all_strengths: List[str] = []
        all_weaknesses: List[str] = []
        all_improvements: List[str] = []

        for eval in evaluations:
            for metric, score in eval.scores.items():
                if metric not in score_totals:
                    score_totals[metric] = []
                score_totals[metric].append(score)

            all_strengths.extend(eval.strengths)
            all_weaknesses.extend(eval.weaknesses)
            all_improvements.extend(eval.suggested_improvements)

        aggregate_scores = {
            metric: sum(scores) / len(scores)
            for metric, scores in score_totals.items()
        }

        # Count frequency of issues and strengths
        from collections import Counter
        weakness_counts = Counter(all_weaknesses)
        strength_counts = Counter(all_strengths)
        improvement_counts = Counter(all_improvements)

        return TestResult(
            test_id=test_id,
            timestamp=datetime.utcnow().isoformat(),
            total_conversations=len(evaluations),
            evaluations=evaluations,
            aggregate_scores=aggregate_scores,
            top_issues=[w for w, _ in weakness_counts.most_common(5)],
            top_strengths=[s for s, _ in strength_counts.most_common(5)],
            recommendations=[i for i, _ in improvement_counts.most_common(5)]
        )

    def save_results(self, result: TestResult, filepath: str = None):
        """Save test results to JSON file"""
        if filepath is None:
            filepath = f"testing/results/{result.test_id}.json"

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Convert to dict for JSON serialization
        result_dict = {
            "test_id": result.test_id,
            "timestamp": result.timestamp,
            "total_conversations": result.total_conversations,
            "aggregate_scores": result.aggregate_scores,
            "top_issues": result.top_issues,
            "top_strengths": result.top_strengths,
            "recommendations": result.recommendations,
            "return_rate": sum(1 for e in result.evaluations if e.would_persona_return) / len(result.evaluations) if result.evaluations else 0,
            "evaluations": [
                {
                    "persona": e.persona_name,
                    "scores": e.scores,
                    "strengths": e.strengths,
                    "weaknesses": e.weaknesses,
                    "feedback": e.specific_feedback,
                    "would_return": e.would_persona_return,
                    "improvements": e.suggested_improvements,
                    "conversation": [
                        {"role": t.role, "content": t.content}
                        for t in e.turns
                    ]
                }
                for e in result.evaluations
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(result_dict, f, indent=2)

        logger.info(f"Results saved to {filepath}")
        return filepath

    def print_summary(self, result: TestResult):
        """Print a summary of test results"""
        print("\n" + "="*60)
        print(f"TEST RESULTS: {result.test_id}")
        print("="*60)

        print(f"\nConversations tested: {result.total_conversations}")

        return_rate = sum(1 for e in result.evaluations if e.would_persona_return) / len(result.evaluations) if result.evaluations else 0
        print(f"Would return rate: {return_rate*100:.1f}%")

        print("\n📊 AGGREGATE SCORES (out of 10):")
        for metric, score in sorted(result.aggregate_scores.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(score) + "░" * (10 - int(score))
            print(f"  {metric:20s} {bar} {score:.1f}")

        print("\n✅ TOP STRENGTHS:")
        for s in result.top_strengths[:5]:
            print(f"  • {s}")

        print("\n❌ TOP ISSUES:")
        for i in result.top_issues[:5]:
            print(f"  • {i}")

        print("\n💡 TOP RECOMMENDATIONS:")
        for r in result.recommendations[:5]:
            print(f"  • {r}")

        print("\n" + "="*60)


async def main():
    """Run the test suite"""
    tester = ConversationTester()

    # Run test batch
    result = await tester.run_test_batch(
        num_conversations=10,  # Start with 10, scale up to 100
        turns_per_conversation=4
    )

    # Save and print results
    tester.save_results(result)
    tester.print_summary(result)


if __name__ == "__main__":
    asyncio.run(main())
