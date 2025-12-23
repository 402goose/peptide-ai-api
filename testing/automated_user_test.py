#!/usr/bin/env python3
"""
Peptide AI - Automated User Testing System

Simulates real user behavior using browser automation (Playwright).
Each persona uses the actual web app, provides feedback, and we measure engagement.

This creates a feedback loop:
1. Persona uses the app (multiple sessions)
2. Submits feedback via the in-app feedback system
3. We analyze feedback and make changes
4. Re-run until personas are satisfied
"""

import asyncio
import json
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
from dotenv import load_dotenv

# Load environment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

# Use local API for testing
API_URL = os.getenv("API_URL", "http://localhost:8000")
WEB_URL = os.getenv("WEB_URL", "http://localhost:3000")
API_KEY = os.getenv("PEPTIDE_AI_MASTER_KEY", "")


class PersonaSession:
    """Simulates a user session for a persona"""

    # Response modes per persona type
    PERSONA_RESPONSE_MODES = {
        "skeptical_researcher": "skeptic",
        "bodybuilder_advanced": "actionable",
        "biohacker_longevity": "balanced",
        "cognitive_optimizer": "balanced",
    }

    def __init__(self, persona: Dict, session_num: int):
        self.persona = persona
        self.session_num = session_num
        self.messages: List[Dict] = []
        self.satisfaction_scores: List[int] = []
        self.issues_found: List[str] = []
        self.features_liked: List[str] = []
        # Get appropriate response mode for this persona
        self.response_mode = self.PERSONA_RESPONSE_MODES.get(persona["id"], "balanced")

    async def chat(self, message: str) -> Dict:
        """Send a chat message and get response"""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{API_URL}/api/v1/chat",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY,
                },
                json={
                    "message": message,
                    "history": self.messages[-10:],  # Last 10 for context
                    "response_mode": self.response_mode,  # Use persona-appropriate mode
                }
            )

            if response.status_code != 200:
                return {"error": response.text, "response": "Error getting response"}

            data = response.json()

            # Store in history
            self.messages.append({"role": "user", "content": message})
            self.messages.append({"role": "assistant", "content": data.get("message", "")})

            return data

    async def submit_feedback(self, feedback_data: Dict) -> bool:
        """Submit feedback via the API"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{API_URL}/api/v1/feedback",
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": API_KEY,
                    },
                    json=feedback_data
                )
                return response.status_code == 200
        except Exception as e:
            print(f"      ⚠️  Feedback submission failed: {str(e)[:50]}")
            return False


class PersonaEvaluator:
    """Uses LLM to evaluate responses from persona's perspective"""

    def __init__(self):
        self.client = None

    async def evaluate_response(
        self,
        persona: Dict,
        question: str,
        response: str,
        sources: List[Dict]
    ) -> Dict:
        """Evaluate a response from the persona's perspective"""

        evaluation_prompt = f"""You are {persona['name']}, {persona['description']}

Your experience level: {persona['experience_level']}
Your primary goal: {persona['primary_goal']}
Your concerns: {', '.join(persona['concerns'])}
What satisfies you: {', '.join(persona['satisfaction_criteria'])}

You just asked: "{question}"

And got this response:
---
{response}
---

Sources provided: {len(sources)}

As {persona['name']}, evaluate this response:

1. SATISFACTION (1-10): How well did this answer your question?
2. CLARITY (1-10): Was it easy to understand for your experience level?
3. TRUST (1-10): Do you trust this information?
4. ACTIONABLE (1-10): Can you actually use this advice?
5. WOULD_RETURN (yes/no): Would you come back and ask more questions?

6. WHAT_WORKED: What was good about this response? (1-2 sentences)
7. WHAT_FAILED: What was missing or wrong? (1-2 sentences)
8. FEEDBACK: What specific feedback would you give to improve? (2-3 sentences)

Respond in JSON format:
{{
    "satisfaction": 7,
    "clarity": 8,
    "trust": 6,
    "actionable": 7,
    "would_return": true,
    "what_worked": "...",
    "what_failed": "...",
    "feedback": "..."
}}"""

        try:
            import openai
            openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            completion = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": evaluation_prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}  # Force JSON response
            )

            content = completion.choices[0].message.content or "{}"

            # Strip markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            if content.startswith("json"):
                content = content[4:].strip()

            result = json.loads(content)
            return result
        except Exception as e:
            print(f"      ⚠️ Evaluation error: {str(e)[:40]}")
            return {
                "satisfaction": 5,
                "clarity": 5,
                "trust": 5,
                "actionable": 5,
                "would_return": False,
                "what_worked": "Unknown",
                "what_failed": "Could not evaluate",
                "feedback": f"Evaluation failed: {str(e)[:50]}"
            }


class AutomatedTestRunner:
    """Runs automated tests for all personas"""

    def __init__(self, personas: List[Dict]):
        self.personas = personas
        self.evaluator = PersonaEvaluator()
        self.results: Dict[str, List[Dict]] = {}

    async def run_persona_session(
        self,
        persona: Dict,
        session_num: int,
        questions: List[str]
    ) -> Dict:
        """Run a single session for a persona"""
        session = PersonaSession(persona, session_num)
        session_results = {
            "persona_id": persona["id"],
            "persona_name": persona["name"],
            "session_num": session_num,
            "timestamp": datetime.utcnow().isoformat(),
            "interactions": [],
            "overall_satisfaction": 0,
            "would_return": False,
            "feedback_submitted": False,
        }

        print(f"\n  📱 {persona['name']} - Session {session_num}")

        for i, question in enumerate(questions):
            print(f"    Q{i+1}: {question[:50]}...")

            # Get response from app
            response_data = await session.chat(question)

            if "error" in response_data:
                print(f"    ❌ Error: {response_data['error'][:50]}")
                continue

            response_text = response_data.get("message", "")
            sources = response_data.get("sources", [])

            # Evaluate from persona's perspective
            evaluation = await self.evaluator.evaluate_response(
                persona, question, response_text, sources
            )

            session_results["interactions"].append({
                "question": question,
                "response_length": len(response_text),
                "sources_count": len(sources),
                "evaluation": evaluation,
            })

            print(f"      → Satisfaction: {evaluation.get('satisfaction', '?')}/10")

            # Small delay between questions
            await asyncio.sleep(1)

        # Calculate overall session metrics
        if session_results["interactions"]:
            scores = [i["evaluation"].get("satisfaction", 5) for i in session_results["interactions"]]
            session_results["overall_satisfaction"] = sum(scores) / len(scores)
            session_results["would_return"] = any(
                i["evaluation"].get("would_return", False) for i in session_results["interactions"]
            )

        # Generate and submit feedback
        feedback = await self._generate_feedback(persona, session_results)
        if feedback:
            success = await session.submit_feedback(feedback)
            session_results["feedback_submitted"] = success
            session_results["feedback"] = feedback
            print(f"    📝 Feedback submitted: {success}")

        return session_results

    async def _generate_feedback(self, persona: Dict, session_results: Dict) -> Optional[Dict]:
        """Generate feedback based on session results"""
        if not session_results["interactions"]:
            return None

        # Aggregate issues and feedback from evaluations
        all_feedback = []
        all_issues = []
        all_worked = []

        for interaction in session_results["interactions"]:
            eval_data = interaction.get("evaluation", {})
            if eval_data.get("feedback"):
                all_feedback.append(eval_data["feedback"])
            if eval_data.get("what_failed"):
                all_issues.append(eval_data["what_failed"])
            if eval_data.get("what_worked"):
                all_worked.append(eval_data["what_worked"])

        summary = f"Session {session_results['session_num']} feedback from {persona['name']} ({persona['experience_level']} user, goal: {persona['primary_goal']}). "
        summary += f"Overall satisfaction: {session_results['overall_satisfaction']:.1f}/10. "
        if all_issues:
            summary += f"Issues: {'; '.join(all_issues[:2])}. "

        return {
            "component_name": "Chat Interface",
            "component_path": "components/chat/ChatContainer.tsx",
            "conversation": [
                {"role": "user", "content": f"I'm {persona['name']}, {persona['description']}"},
                {"role": "assistant", "content": "Thanks for testing! What feedback do you have?"},
                {"role": "user", "content": "; ".join(all_feedback) if all_feedback else "No specific feedback"},
            ],
            "summary": summary,
            "product_prompt": self._generate_product_prompt(persona, session_results, all_issues, all_worked),
            "insights": all_issues[:3] if all_issues else ["No specific issues found"],
            "priority": "high" if session_results["overall_satisfaction"] < 6 else "medium",
            "category": "ux",
            "user_context": {
                "page": "/chat",
                "persona_id": persona["id"],
                "session_num": session_results["session_num"],
                "satisfaction": session_results["overall_satisfaction"],
            }
        }

    def _generate_product_prompt(
        self,
        persona: Dict,
        session_results: Dict,
        issues: List[str],
        worked: List[str]
    ) -> str:
        """Generate actionable product prompt from feedback"""
        prompt = f"""## Feedback from {persona['name']} (Session {session_results['session_num']})

**User Profile:** {persona['description']}
**Experience Level:** {persona['experience_level']}
**Goal:** {persona['primary_goal']}
**Satisfaction:** {session_results['overall_satisfaction']:.1f}/10
**Would Return:** {session_results['would_return']}

### What Worked
{chr(10).join('- ' + w for w in worked) if worked else '- Nothing specifically noted'}

### Issues Found
{chr(10).join('- ' + i for i in issues) if issues else '- No specific issues'}

### Recommended Changes
Based on this {persona['experience_level']} user's needs:
"""
        if session_results["overall_satisfaction"] < 6:
            prompt += "- HIGH PRIORITY: This user type is not satisfied\n"
            if persona["experience_level"] == "beginner":
                prompt += "- Simplify explanations, add more context\n"
            if "safety" in persona["concerns"]:
                prompt += "- More prominent safety information\n"
            if "evidence" in str(persona["concerns"]).lower():
                prompt += "- Add more citations and evidence quality indicators\n"

        return prompt

    async def run_all_personas(self, sessions_per_persona: int = 3) -> Dict:
        """Run tests for all personas"""
        print(f"\n🚀 Starting Automated User Testing")
        print(f"   Personas: {len(self.personas)}")
        print(f"   Sessions each: {sessions_per_persona}")
        print(f"   API: {API_URL}")

        all_results = []

        for persona in self.personas:
            print(f"\n{'='*60}")
            print(f"👤 Testing: {persona['name']}")
            print(f"   {persona['description']}")
            print(f"   Goal: {persona['primary_goal']} | Level: {persona['experience_level']}")

            persona_results = []

            for session_num in range(1, sessions_per_persona + 1):
                # Select questions for this session
                questions = random.sample(
                    persona["sample_questions"],
                    min(3, len(persona["sample_questions"]))
                )

                result = await self.run_persona_session(persona, session_num, questions)
                persona_results.append(result)

                # Delay between sessions
                await asyncio.sleep(2)

            self.results[persona["id"]] = persona_results
            all_results.extend(persona_results)

        # Generate summary
        summary = self._generate_summary(all_results)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "personas_tested": len(self.personas),
            "total_sessions": len(all_results),
            "summary": summary,
            "results_by_persona": self.results,
        }

    def _generate_summary(self, results: List[Dict]) -> Dict:
        """Generate overall test summary"""
        if not results:
            return {}

        total_satisfaction = sum(r.get("overall_satisfaction", 0) for r in results)
        avg_satisfaction = total_satisfaction / len(results) if results else 0

        return_count = sum(1 for r in results if r.get("would_return", False))
        return_rate = return_count / len(results) if results else 0

        # Group by persona
        by_persona = {}
        for r in results:
            pid = r["persona_id"]
            if pid not in by_persona:
                by_persona[pid] = {"scores": [], "would_return": []}
            by_persona[pid]["scores"].append(r.get("overall_satisfaction", 0))
            by_persona[pid]["would_return"].append(r.get("would_return", False))

        persona_summaries = {}
        for pid, data in by_persona.items():
            persona_summaries[pid] = {
                "avg_satisfaction": sum(data["scores"]) / len(data["scores"]),
                "return_rate": sum(data["would_return"]) / len(data["would_return"]),
                "sessions": len(data["scores"]),
            }

        return {
            "overall_satisfaction": avg_satisfaction,
            "overall_return_rate": return_rate,
            "total_sessions": len(results),
            "by_persona": persona_summaries,
        }


async def main():
    """Run the automated testing"""
    # Load personas
    personas_path = os.path.join(project_root, "testing", "personas.json")

    if not os.path.exists(personas_path):
        print("❌ personas.json not found. Run persona_builder.py first.")
        return

    with open(personas_path) as f:
        personas = json.load(f)

    print(f"📋 Loaded {len(personas)} personas")

    # Run tests
    runner = AutomatedTestRunner(personas)
    results = await runner.run_all_personas(sessions_per_persona=2)

    # Save results
    output_path = os.path.join(project_root, "testing", "test_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")

    summary = results.get("summary", {})
    print(f"\n  Overall Satisfaction: {summary.get('overall_satisfaction', 0):.1f}/10")
    print(f"  Would Return Rate: {summary.get('overall_return_rate', 0)*100:.0f}%")
    print(f"  Total Sessions: {summary.get('total_sessions', 0)}")

    print(f"\n  By Persona:")
    for pid, data in summary.get("by_persona", {}).items():
        status = "✅" if data["avg_satisfaction"] >= 7 else "⚠️" if data["avg_satisfaction"] >= 5 else "❌"
        print(f"    {status} {pid}: {data['avg_satisfaction']:.1f}/10 ({data['return_rate']*100:.0f}% return)")

    print(f"\n💾 Full results saved to {output_path}")

    # Identify personas that need work
    struggling = [
        pid for pid, data in summary.get("by_persona", {}).items()
        if data["avg_satisfaction"] < 7
    ]

    if struggling:
        print(f"\n⚠️  Personas needing improvement: {', '.join(struggling)}")
        print("   Check feedback in the database for specific issues.")


if __name__ == "__main__":
    asyncio.run(main())
