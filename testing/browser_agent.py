#!/usr/bin/env python3
"""
Peptide AI - Browser Agent System

Each persona is an AI agent that browses the production web app AND uses the API.
- Browser: Tests landing page, navigation, UX, sign-up flow
- API: Tests authenticated features (chat, stacks, etc.)

This simulates real user behavior over multiple sessions.
"""

import asyncio
import json
import os
import random
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import openai
from playwright.async_api import async_playwright, Page, Browser
from dotenv import load_dotenv

# Load environment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

WEB_URL = os.getenv("WEB_URL", "https://peptide-ai-web-production.up.railway.app")
API_URL = os.getenv("API_URL", "https://peptide-ai-api-production.up.railway.app")
API_KEY = os.getenv("PEPTIDE_AI_MASTER_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class ActionType(Enum):
    """Actions the agent can take"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    ASK_CHAT_API = "ask_chat_api"  # Use API for chat (requires auth)
    EXPLORE_LANDING = "explore_landing"  # Explore landing page content
    CHECK_SIGN_UP = "check_sign_up"  # Evaluate sign-up flow
    VIEW_SOURCES = "view_sources"
    SUBMIT_FEEDBACK_API = "submit_feedback_api"  # Submit feedback via API
    SCROLL = "scroll"
    END_SESSION = "end_session"


@dataclass
class PersonaState:
    """Tracks a persona's journey through the app"""
    persona_id: str
    session_count: int = 0
    total_chats: int = 0
    stacks_created: List[str] = field(default_factory=list)
    peptides_researched: List[str] = field(default_factory=list)
    feedback_submitted: int = 0
    satisfaction_scores: List[int] = field(default_factory=list)
    journey_stage: str = "discovery"  # discovery, research, planning, active, maintaining
    last_session: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class BrowserAction:
    """An action for the browser to execute"""
    action_type: ActionType
    target: Optional[str] = None  # CSS selector or URL
    value: Optional[str] = None   # Text to type or message
    reasoning: str = ""           # Why the agent chose this action


class PersonaBrowserAgent:
    """
    An AI agent that controls a browser as a specific persona.
    Uses LLM to decide what to do next based on persona goals and current state.
    """

    # Response modes per persona type
    PERSONA_RESPONSE_MODES = {
        "skeptical_researcher": "skeptic",
        "bodybuilder_advanced": "actionable",
        "biohacker_longevity": "balanced",
        "cognitive_optimizer": "balanced",
    }

    def __init__(self, persona: Dict, state: Optional[PersonaState] = None):
        self.persona = persona
        self.state = state or PersonaState(persona_id=persona["id"])
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.openai = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.action_history: List[BrowserAction] = []
        self.current_page_content: str = ""
        self.chat_history: List[Dict] = []  # For API chat
        self.response_mode = self.PERSONA_RESPONSE_MODES.get(persona.get("id", ""), "balanced")
        self.landing_page_feedback: List[str] = []  # Feedback about landing page

    async def start_browser(self, headless: bool = True):
        """Start browser instance"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
        context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=f"PeptideAI-PersonaAgent/{self.persona['id']}"
        )
        self.page = await context.new_page()
        print(f"    Browser started for {self.persona['name']}")

    async def close_browser(self):
        """Close browser instance"""
        if self.browser:
            await self.browser.close()

    async def api_chat(self, message: str) -> Dict:
        """Send chat message via API (bypasses browser auth)"""
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(
                    f"{API_URL}/api/v1/chat",
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": API_KEY,
                    },
                    json={
                        "message": message,
                        "history": self.chat_history[-10:],
                        "response_mode": self.response_mode,
                    }
                )

                if response.status_code != 200:
                    return {"error": response.text, "message": "Error getting response"}

                data = response.json()
                self.chat_history.append({"role": "user", "content": message})
                self.chat_history.append({"role": "assistant", "content": data.get("message", "")})
                self.state.total_chats += 1

                # Track peptides mentioned
                for peptide in ["BPC-157", "TB-500", "Semaglutide", "Tirzepatide", "Semax", "Selank", "GHK-Cu"]:
                    if peptide.lower() in message.lower():
                        if peptide not in self.state.peptides_researched:
                            self.state.peptides_researched.append(peptide)

                return data
            except Exception as e:
                return {"error": str(e), "message": "API error"}

    async def api_submit_feedback(self, feedback: Dict) -> bool:
        """Submit feedback via API"""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    f"{API_URL}/api/v1/feedback",
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": API_KEY,
                    },
                    json=feedback
                )
                if response.status_code == 200:
                    self.state.feedback_submitted += 1
                    return True
                return False
            except:
                return False

    async def get_page_state(self) -> str:
        """Get current page state for LLM context"""
        if not self.page:
            return "Browser not started"

        try:
            url = self.page.url
            title = await self.page.title()

            # Get visible text content using simpler approach
            try:
                body_text = await self.page.locator('body').inner_text()
                content = body_text[:1000]  # First 1000 chars
            except:
                content = "Could not read page content"

            # Get button labels
            try:
                buttons = await self.page.locator('button').all_text_contents()
                button_list = [b.strip()[:50] for b in buttons if b.strip()][:10]
            except:
                button_list = []

            # Check for specific UI elements
            has_chat_input = await self.page.locator('textarea, input[type="text"]').count() > 0
            has_feedback_button = await self.page.locator('[data-feedback], .feedback-button, button:has-text("Feedback")').count() > 0
            has_sign_in = await self.page.locator('button:has-text("Sign In"), a:has-text("Sign In")').count() > 0

            return f"""
URL: {url}
Title: {title}
Has chat input: {has_chat_input}
Has feedback button: {has_feedback_button}
Requires sign-in: {has_sign_in and not has_chat_input}
Available buttons: {', '.join(button_list)}

Page content:
{content}
"""
        except Exception as e:
            return f"Error reading page: {str(e)}"

    async def decide_next_action(self) -> BrowserAction:
        """Use LLM to decide what action to take next"""
        page_state = await self.get_page_state()

        # Get sample questions for this persona
        sample_questions = self.persona.get("sample_questions", [
            "What peptides would help with my goals?",
            "What are the side effects?",
            "How do I dose this safely?"
        ])

        prompt = f"""You are {self.persona['name']}, {self.persona['description']}

Your goals: {self.persona['primary_goal']}
Your concerns: {', '.join(self.persona.get('concerns', []))}
Experience level: {self.persona.get('experience_level', 'intermediate')}

CURRENT SESSION STATE:
- Sessions completed: {self.state.session_count}
- Chats so far: {self.state.total_chats}
- Peptides researched: {', '.join(self.state.peptides_researched) or 'None yet'}
- Feedback given: {self.state.feedback_submitted}

RECENT ACTIONS:
{chr(10).join([f"- {a.action_type.value}: {a.value or a.target}" for a in self.action_history[-5:]]) or "None yet"}

CURRENT PAGE STATE:
{page_state}

YOUR SAMPLE QUESTIONS (pick one if asking chat):
{chr(10).join([f"- {q}" for q in sample_questions[:5]])}

AVAILABLE ACTIONS:
1. explore_landing - Explore and evaluate the landing page (first action)
2. click - Click a button on the page (target: button text like "Get Started")
3. scroll - Scroll the page (value: "up" or "down")
4. ask_chat_api - Ask a research question via API (value: your question) - USE THIS FOR RESEARCH
5. submit_feedback_api - Submit your feedback via API (value: your feedback)
6. end_session - End this session (use after 4-6 meaningful actions)

IMPORTANT:
- The web app requires sign-in for the chat UI, so use ask_chat_api for research questions
- First explore the landing page, then ask 2-3 research questions via API
- End with feedback about your experience
- Focus on your actual goals as {self.persona['name']}

Respond in JSON:
{{
    "action": "action_type",
    "target": "selector or url if needed",
    "value": "text if needed",
    "reasoning": "Why you're doing this as {self.persona['name']}"
}}"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content or "{}")

            action_type = ActionType(result.get("action", "end_session"))
            return BrowserAction(
                action_type=action_type,
                target=result.get("target"),
                value=result.get("value"),
                reasoning=result.get("reasoning", "")
            )
        except Exception as e:
            print(f"      Decision error: {e}")
            return BrowserAction(action_type=ActionType.END_SESSION, reasoning="Error occurred")

    async def execute_action(self, action: BrowserAction) -> bool:
        """Execute a browser or API action"""
        try:
            if action.action_type == ActionType.NAVIGATE:
                if not self.page:
                    return False
                url = action.target or WEB_URL
                if not url.startswith("http"):
                    url = f"{WEB_URL}{url}"
                await self.page.goto(url, wait_until="networkidle", timeout=30000)
                print(f"      -> Navigated to {url}")

            elif action.action_type == ActionType.CLICK:
                if not self.page:
                    return False
                # Try multiple selectors
                clicked = False
                selectors = [
                    f'button:has-text("{action.target}")',
                    f'a:has-text("{action.target}")',
                    f'[aria-label="{action.target}"]',
                ]
                for selector in selectors:
                    try:
                        element = self.page.locator(selector).first
                        if await element.is_visible(timeout=2000):
                            await element.click()
                            clicked = True
                            print(f"      -> Clicked: {action.target}")
                            await asyncio.sleep(2)  # Wait for navigation
                            break
                    except:
                        continue
                if not clicked:
                    print(f"      -> Could not find: {action.target}")

            elif action.action_type == ActionType.EXPLORE_LANDING:
                # Evaluate the landing page from persona's perspective
                page_state = await self.get_page_state() if self.page else "No page loaded"
                eval_prompt = f"""You are {self.persona['name']}. Evaluate this landing page:

{page_state}

As a {self.persona.get('experience_level', 'intermediate')} user with goal "{self.persona.get('primary_goal', 'research')}":
- Is the value proposition clear?
- Does it seem trustworthy for peptide research?
- What would make you sign up?
- Any concerns?

Respond in 2-3 sentences."""

                response = await self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": eval_prompt}],
                    temperature=0.7,
                    max_tokens=150
                )
                feedback = response.choices[0].message.content or ""
                self.landing_page_feedback.append(feedback)
                print(f"      -> Landing evaluation: {feedback[:80]}...")

            elif action.action_type == ActionType.ASK_CHAT_API:
                # Use API for chat (bypasses browser auth)
                question = action.value or "What peptides would help with my goals?"
                print(f"      -> Asking via API: {question[:50]}...")
                result = await self.api_chat(question)
                if "error" not in result:
                    response_preview = result.get("message", "")[:100]
                    sources = len(result.get("sources", []))
                    print(f"      -> Got response ({sources} sources): {response_preview}...")
                else:
                    print(f"      -> API error: {result.get('error', 'Unknown')[:50]}")

            elif action.action_type == ActionType.SUBMIT_FEEDBACK_API:
                # Submit feedback via API
                feedback_text = action.value or "Good experience overall"
                feedback_data = {
                    "component_name": "Full App Experience",
                    "component_path": "browser_agent_test",
                    "conversation": self.chat_history[-6:],  # Last 3 exchanges
                    "summary": f"Browser agent feedback from {self.persona['name']}",
                    "product_prompt": f"""## Browser Agent Feedback: {self.persona['name']}

**User Profile:** {self.persona.get('description', '')}
**Experience Level:** {self.persona.get('experience_level', 'intermediate')}
**Goal:** {self.persona.get('primary_goal', '')}
**Chats:** {self.state.total_chats}
**Peptides Researched:** {', '.join(self.state.peptides_researched) or 'None'}

**Landing Page Feedback:**
{chr(10).join(self.landing_page_feedback) or 'No landing page feedback'}

**User Feedback:**
{feedback_text}
""",
                    "insights": [feedback_text],
                    "priority": "medium",
                    "category": "ux",
                    "user_context": {
                        "page": "/browser-agent-test",
                        "persona_id": self.persona.get("id", "unknown"),
                        "session_num": self.state.session_count,
                    }
                }
                success = await self.api_submit_feedback(feedback_data)
                print(f"      -> Feedback submitted: {success}")

            elif action.action_type == ActionType.SCROLL:
                if not self.page:
                    return False
                direction = -300 if action.value == "up" else 300
                await self.page.mouse.wheel(0, direction)
                print(f"      -> Scrolled {action.value}")

            elif action.action_type == ActionType.VIEW_SOURCES:
                if not self.page:
                    return False
                sources_btn = self.page.locator('button:has-text("Sources"), button:has-text("Research")').first
                try:
                    await sources_btn.click()
                    print(f"      -> Viewing sources")
                except:
                    print(f"      -> Sources not found")

            elif action.action_type == ActionType.END_SESSION:
                return False

            # Small delay between actions
            await asyncio.sleep(1)
            return True

        except Exception as e:
            print(f"      Action error: {e}")
            return True  # Continue despite errors

    async def run_session(self, max_actions: int = 10) -> Dict:
        """Run a single browsing session"""
        self.state.session_count += 1
        self.action_history = []
        session_start = datetime.now()

        print(f"\n  Session {self.state.session_count} for {self.persona['name']}")

        # Start at home page
        await self.page.goto(WEB_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        actions_taken = 0
        while actions_taken < max_actions:
            action = await self.decide_next_action()
            self.action_history.append(action)

            print(f"    [{actions_taken+1}] {action.action_type.value}: {action.reasoning[:60]}...")

            should_continue = await self.execute_action(action)
            if not should_continue:
                break

            actions_taken += 1
            await asyncio.sleep(0.5)

        self.state.last_session = datetime.now()

        return {
            "session_num": self.state.session_count,
            "actions_taken": actions_taken,
            "duration_seconds": (datetime.now() - session_start).seconds,
            "chats": self.state.total_chats,
            "peptides_researched": self.state.peptides_researched.copy(),
        }

    async def evaluate_experience(self) -> Dict:
        """Have the persona evaluate their overall experience"""
        prompt = f"""You are {self.persona.get('name', 'User')}, {self.persona.get('description', 'a peptide researcher')}

You've just used Peptide AI for {self.state.session_count} sessions.

YOUR JOURNEY:
- Total chats: {self.state.total_chats}
- Peptides researched: {', '.join(self.state.peptides_researched) or 'None'}
- Stacks created: {len(self.state.stacks_created)}
- Feedback submitted: {self.state.feedback_submitted}
- Landing page impressions: {len(self.landing_page_feedback)}

YOUR GOALS:
- Primary goal: {self.persona.get('primary_goal', 'Research peptides')}
- Concerns: {', '.join(self.persona.get('concerns', []))}
- What satisfies you: {', '.join(self.persona.get('satisfaction_criteria', []))}

Based on your experience, evaluate:

1. OVERALL_SATISFACTION (1-10): How well did the app help you?
2. WOULD_RETURN (yes/no): Would you come back?
3. WHAT_WORKED: What features/aspects were good?
4. WHAT_NEEDS_IMPROVEMENT: What was missing or frustrating?
5. SPECIFIC_FEEDBACK: What would you tell the developers?

Respond as {self.persona['name']} in JSON:
{{
    "overall_satisfaction": 7,
    "would_return": true,
    "what_worked": "...",
    "what_needs_improvement": "...",
    "specific_feedback": "..."
}}"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content or "{}")
        except Exception as e:
            return {"error": str(e), "overall_satisfaction": 5}


class BrowserTestRunner:
    """Orchestrates browser testing for all personas"""

    def __init__(self, personas: List[Dict]):
        self.personas = personas
        self.agents: Dict[str, PersonaBrowserAgent] = {}
        self.results: Dict[str, List[Dict]] = {}

    async def run_persona(
        self,
        persona: Dict,
        sessions: int = 3,
        headless: bool = True
    ) -> Dict:
        """Run multiple sessions for a single persona"""
        agent = PersonaBrowserAgent(persona)
        self.agents[persona["id"]] = agent

        print(f"\n{'='*60}")
        print(f"Starting: {persona.get('name', 'Unknown')} ({persona.get('id', 'unknown')})")
        print(f"Goal: {persona.get('primary_goal', 'Research')} | Level: {persona.get('experience_level', 'intermediate')}")

        try:
            await agent.start_browser(headless=headless)

            session_results = []
            for i in range(sessions):
                result = await agent.run_session(max_actions=8)
                session_results.append(result)
                # Simulate time between sessions
                await asyncio.sleep(2)

            # Get final evaluation
            evaluation = await agent.evaluate_experience()

            return {
                "persona_id": persona["id"],
                "persona_name": persona["name"],
                "sessions": session_results,
                "final_state": {
                    "total_chats": agent.state.total_chats,
                    "peptides_researched": agent.state.peptides_researched,
                    "stacks_created": agent.state.stacks_created,
                    "feedback_submitted": agent.state.feedback_submitted,
                },
                "evaluation": evaluation,
            }

        finally:
            await agent.close_browser()

    async def run_all(
        self,
        sessions_per_persona: int = 2,
        headless: bool = True
    ) -> Dict:
        """Run tests for all personas"""
        print(f"\n{'='*60}")
        print(f"BROWSER AGENT TESTING")
        print(f"{'='*60}")
        print(f"Personas: {len(self.personas)}")
        print(f"Sessions each: {sessions_per_persona}")
        print(f"Target: {WEB_URL}")

        all_results = []

        for persona in self.personas:
            result = await self.run_persona(
                persona,
                sessions=sessions_per_persona,
                headless=headless
            )
            all_results.append(result)
            self.results[persona["id"]] = result

        # Generate summary
        summary = self._generate_summary(all_results)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "target_url": WEB_URL,
            "personas_tested": len(self.personas),
            "sessions_per_persona": sessions_per_persona,
            "summary": summary,
            "results": all_results,
        }

    def _generate_summary(self, results: List[Dict]) -> Dict:
        """Generate test summary"""
        satisfactions = []
        would_return = 0

        for r in results:
            eval_data = r.get("evaluation", {})
            sat = eval_data.get("overall_satisfaction", 5)
            satisfactions.append(sat)
            if eval_data.get("would_return", False):
                would_return += 1

        return {
            "overall_satisfaction": sum(satisfactions) / len(satisfactions) if satisfactions else 0,
            "would_return_rate": would_return / len(results) if results else 0,
            "total_sessions": sum(len(r.get("sessions", [])) for r in results),
            "by_persona": {
                r["persona_id"]: {
                    "satisfaction": r.get("evaluation", {}).get("overall_satisfaction", 5),
                    "would_return": r.get("evaluation", {}).get("would_return", False),
                    "chats": r.get("final_state", {}).get("total_chats", 0),
                }
                for r in results
            }
        }


async def main():
    """Run browser agent testing"""
    # Load personas
    personas_path = os.path.join(project_root, "testing", "personas.json")

    if not os.path.exists(personas_path):
        print("personas.json not found. Run persona_builder.py first.")
        return

    with open(personas_path) as f:
        personas = json.load(f)

    print(f"Loaded {len(personas)} personas")

    # Run tests (start with 2 personas for testing)
    runner = BrowserTestRunner(personas[:2])  # Start small
    results = await runner.run_all(sessions_per_persona=2, headless=True)

    # Save results
    output_path = os.path.join(project_root, "testing", "browser_test_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print("BROWSER TEST SUMMARY")
    print(f"{'='*60}")

    summary = results.get("summary", {})
    print(f"\nOverall Satisfaction: {summary.get('overall_satisfaction', 0):.1f}/10")
    print(f"Would Return Rate: {summary.get('would_return_rate', 0)*100:.0f}%")

    print(f"\nBy Persona:")
    for pid, data in summary.get("by_persona", {}).items():
        status = "✅" if data["satisfaction"] >= 7 else "⚠️"
        print(f"  {status} {pid}: {data['satisfaction']}/10 | Chats: {data['chats']}")

    print(f"\nFull results saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
