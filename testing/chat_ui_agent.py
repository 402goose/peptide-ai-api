#!/usr/bin/env python3
"""
Peptide AI - Chat UI Browser Agent

This agent actually interacts with the chat UI using Playwright:
- Types in the message input
- Clicks send button
- Waits for streaming response
- Clicks follow-up chips
- Expands research card
- Tracks all metrics

Used for A/B testing different UI variants with persona-based testing.
"""

import asyncio
import json
import os
import random
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import openai
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from dotenv import load_dotenv

# Load environment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

WEB_URL = os.getenv("WEB_URL", "https://peptide-ai-web-production.up.railway.app")
API_URL = os.getenv("API_URL", "https://peptide-ai-api-production.up.railway.app")
API_KEY = os.getenv("PEPTIDE_AI_MASTER_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


@dataclass
class InteractionMetrics:
    """Tracks all interactions during a test session"""
    session_id: str
    persona_id: str
    experiment_variant: Optional[str] = None

    # Timing metrics
    page_load_time_ms: int = 0
    time_to_first_message_ms: int = 0
    response_stream_time_ms: int = 0
    total_session_time_ms: int = 0

    # Interaction counts
    messages_sent: int = 0
    follow_ups_clicked: int = 0
    research_card_expanded: int = 0
    sources_viewed: int = 0

    # Engagement signals
    scrolled_to_sources: bool = False
    clicked_external_link: bool = False
    submitted_feedback: bool = False

    # Outcomes
    completed_conversation: bool = False
    would_return: bool = False
    satisfaction_score: int = 0

    # Raw data
    actions: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class PersonaConfig:
    """Configuration for a test persona"""
    id: str
    name: str
    description: str
    experience_level: str
    primary_goal: str
    concerns: List[str]
    sample_questions: List[str]
    satisfaction_criteria: List[str]


class ChatUIAgent:
    """
    Browser agent that interacts with the actual chat UI.
    Tracks all metrics for A/B testing analysis.
    """

    def __init__(self, persona: PersonaConfig, experiment_id: Optional[str] = None):
        self.persona = persona
        self.experiment_id = experiment_id
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.openai = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.metrics = InteractionMetrics(
            session_id=f"{persona.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            persona_id=persona.id
        )
        self.conversation_history: List[Dict] = []

    async def start_browser(self, headless: bool = True):
        """Start browser instance"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
        context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=f"PeptideAI-ChatUIAgent/{self.persona.id}"
        )
        self.page = await context.new_page()

        # Set up request interception to track API calls
        await self.page.route("**/*", self._handle_request)

        print(f"  🌐 Browser started for {self.persona.name}")

    async def _handle_request(self, route):
        """Intercept requests to track API calls"""
        request = route.request
        # Just continue for now, but we could track API timing here
        await route.continue_()

    async def close_browser(self):
        """Close browser instance"""
        if self.browser:
            await self.browser.close()

    async def assign_experiment_variant(self) -> Optional[str]:
        """Get A/B experiment variant assignment from API"""
        if not self.experiment_id:
            return None

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{API_URL}/api/v1/experiments/{self.experiment_id}/assign",
                    headers={"X-API-Key": API_KEY},
                    json={"user_id": f"persona-{self.persona.id}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    self.metrics.experiment_variant = data.get("variant")
                    return self.metrics.experiment_variant
        except Exception as e:
            self.metrics.errors.append(f"Experiment assignment error: {e}")
        return None

    async def navigate_to_chat(self) -> bool:
        """Navigate to chat page and wait for it to load"""
        if not self.page:
            return False

        start_time = datetime.now()
        try:
            await self.page.goto(f"{WEB_URL}/chat", wait_until="networkidle", timeout=30000)
            self.metrics.page_load_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Wait for chat input to be ready (handles both onboarding and chat modes)
            await self.page.wait_for_selector('textarea, input[type="text"]', timeout=10000)

            # Close any modal that might be open (feedback modal, etc.)
            try:
                close_button = self.page.locator('button:has(svg.lucide-x), [class*="modal"] button:first-child')
                if await close_button.count() > 0:
                    await close_button.first.click()
                    await asyncio.sleep(0.3)
            except:
                pass

            self._log_action("navigate", {"url": f"{WEB_URL}/chat", "load_time_ms": self.metrics.page_load_time_ms})
            print(f"    📍 Loaded chat page in {self.metrics.page_load_time_ms}ms")
            return True

        except Exception as e:
            self.metrics.errors.append(f"Navigation error: {e}")
            print(f"    ❌ Navigation failed: {e}")
            return False

    async def _close_modal_if_open(self):
        """Close any modal that might be blocking the UI"""
        try:
            modal = self.page.locator('.fixed.inset-0.z-50')
            if await modal.count() > 0:
                close_btn = self.page.locator('.fixed.inset-0.z-50 button:has(svg)').first
                await close_btn.click()
                await asyncio.sleep(0.3)
        except:
            pass

    async def send_message(self, message: str) -> bool:
        """Type a message and send it"""
        if not self.page:
            return False

        start_time = datetime.now()
        try:
            # Close any modal that might be blocking
            await self._close_modal_if_open()

            # Find and click the textarea (works in both onboarding and chat modes)
            textarea = self.page.locator('textarea').first
            await textarea.click()

            # Type the message (with slight delay for realism)
            await textarea.fill(message)
            await asyncio.sleep(0.3)

            # Find and click send button
            send_button = self.page.locator('button[type="submit"], button:has(svg)').last
            await send_button.click()

            if self.metrics.messages_sent == 0:
                self.metrics.time_to_first_message_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            self.metrics.messages_sent += 1
            self.conversation_history.append({"role": "user", "content": message})

            self._log_action("send_message", {"message": message[:100], "message_num": self.metrics.messages_sent})
            print(f"    💬 Sent: {message[:50]}...")

            return True

        except Exception as e:
            self.metrics.errors.append(f"Send message error: {e}")
            print(f"    ❌ Send failed: {e}")
            return False

    async def wait_for_response(self, timeout: int = 60000) -> Optional[str]:
        """Wait for the assistant response to complete streaming"""
        if not self.page:
            return None

        start_time = datetime.now()
        try:
            # Count assistant messages using data-testid attribute
            assistant_msg_locator = self.page.locator('[data-testid="assistant-message"]')
            initial_count = await assistant_msg_locator.count()
            print(f"    📊 Initial assistant message count: {initial_count}")

            # Wait for a new assistant message bubble to appear
            # Poll until we see more assistant messages than before
            new_message_appeared = False
            for i in range(60):  # 30 seconds max wait for response to start
                await asyncio.sleep(0.5)
                current_count = await assistant_msg_locator.count()
                if current_count > initial_count:
                    new_message_appeared = True
                    print(f"    📊 New assistant message appeared (count: {current_count})")
                    break
                if i % 10 == 0 and i > 0:
                    print(f"    ⏳ Waiting for response... ({i * 0.5}s)")

            if not new_message_appeared:
                print(f"    ⏱️ Response timeout (no new message)")
                return None

            # Now wait for streaming to complete (content stabilizes)
            last_content = ""
            stable_count = 0

            while stable_count < 4:  # Content stable for 2 seconds
                await asyncio.sleep(0.5)

                try:
                    # Get the last message bubble's text
                    messages = self.page.locator('.mb-4.flex.gap-3 .rounded-2xl')
                    count = await messages.count()
                    if count > 0:
                        current_content = await messages.last.inner_text()
                        if current_content == last_content and len(current_content) > 20:
                            stable_count += 1
                        else:
                            stable_count = 0
                            last_content = current_content
                except Exception as e:
                    pass

                # Timeout check
                if (datetime.now() - start_time).total_seconds() * 1000 > timeout:
                    break

            self.metrics.response_stream_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if last_content:
                self.conversation_history.append({"role": "assistant", "content": last_content[:500]})
                self._log_action("received_response", {
                    "length": len(last_content),
                    "time_ms": self.metrics.response_stream_time_ms
                })
                print(f"    🤖 Response received in {self.metrics.response_stream_time_ms}ms ({len(last_content)} chars)")
                return last_content

            return None

        except PlaywrightTimeout:
            self.metrics.errors.append("Response timeout")
            print(f"    ⏱️ Response timeout")
            return None
        except Exception as e:
            self.metrics.errors.append(f"Response error: {e}")
            print(f"    ❌ Response error: {e}")
            return None

    async def click_follow_up(self) -> Optional[str]:
        """Click a follow-up question chip"""
        if not self.page:
            return None

        try:
            # Find follow-up chips (rounded-full buttons in the scrollable container)
            chips = self.page.locator('.scrollbar-hide button, button.rounded-full:not([type="submit"])')
            count = await chips.count()

            if count == 0:
                print(f"    ℹ️ No follow-up chips found")
                return None

            # Pick a random chip
            index = random.randint(0, min(count - 1, 3))
            chip = chips.nth(index)

            text = await chip.inner_text()
            await chip.click()

            self.metrics.follow_ups_clicked += 1
            self._log_action("click_follow_up", {"text": text[:100], "index": index})
            print(f"    🔘 Clicked follow-up: {text[:40]}...")

            return text

        except Exception as e:
            self.metrics.errors.append(f"Follow-up click error: {e}")
            return None

    async def expand_research_card(self) -> bool:
        """Click to expand the collapsible research card"""
        if not self.page:
            return False

        try:
            # Look for the collapsed research card summary bar
            card_button = self.page.locator('button:has([class*="FlaskConical"]), button:has-text("papers"), button:has-text("research")').first

            if await card_button.is_visible(timeout=2000):
                await card_button.click()
                self.metrics.research_card_expanded += 1
                self._log_action("expand_research_card", {})
                print(f"    📚 Expanded research card")
                await asyncio.sleep(0.5)
                return True

        except Exception as e:
            pass  # Card might not exist
        return False

    async def view_source(self) -> bool:
        """Click on a source link in the research card"""
        if not self.page:
            return False

        try:
            # Find source links
            source_links = self.page.locator('a:has-text("PubMed"), a:has-text("View"), a[target="_blank"]')
            count = await source_links.count()

            if count > 0:
                # Click first source (but don't actually navigate away)
                link = source_links.first
                href = await link.get_attribute('href')
                self.metrics.sources_viewed += 1
                self.metrics.clicked_external_link = True
                self._log_action("view_source", {"href": href})
                print(f"    🔗 Would view source: {href[:50] if href else 'unknown'}...")
                return True

        except Exception as e:
            pass
        return False

    async def scroll_page(self, direction: str = "down") -> bool:
        """Scroll the page"""
        if not self.page:
            return False

        try:
            delta = 400 if direction == "down" else -400
            await self.page.mouse.wheel(0, delta)

            if direction == "down":
                self.metrics.scrolled_to_sources = True

            self._log_action("scroll", {"direction": direction})
            await asyncio.sleep(0.3)
            return True

        except Exception as e:
            return False

    async def evaluate_experience(self) -> Dict:
        """Have the persona evaluate their experience using LLM"""
        prompt = f"""You are {self.persona.name}, {self.persona.description}

You just used a peptide research chat app. Here's what happened:

CONVERSATION:
{json.dumps(self.conversation_history[-6:], indent=2)}

YOUR GOALS: {self.persona.primary_goal}
YOUR CONCERNS: {', '.join(self.persona.concerns)}
WHAT SATISFIES YOU: {', '.join(self.persona.satisfaction_criteria)}

METRICS:
- Messages sent: {self.metrics.messages_sent}
- Response time: {self.metrics.response_stream_time_ms}ms
- Follow-ups clicked: {self.metrics.follow_ups_clicked}
- Sources viewed: {self.metrics.sources_viewed}
- Errors encountered: {len(self.metrics.errors)}

Based on this experience as {self.persona.name}, evaluate:

1. SATISFACTION (1-10): How well did the app help with your goals?
2. WOULD_RETURN (true/false): Would you come back to use this again?
3. WHAT_WORKED: What was good about the experience?
4. WHAT_NEEDS_IMPROVEMENT: What was frustrating or missing?
5. SPECIFIC_FEEDBACK: One actionable suggestion for the developers

Respond in JSON:
{{
    "satisfaction": 7,
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
            result = json.loads(response.choices[0].message.content or "{}")

            self.metrics.satisfaction_score = result.get("satisfaction", 5)
            self.metrics.would_return = result.get("would_return", False)

            return result

        except Exception as e:
            return {"error": str(e), "satisfaction": 5, "would_return": False}

    def _log_action(self, action_type: str, data: Dict):
        """Log an action for metrics"""
        self.metrics.actions.append({
            "type": action_type,
            "timestamp": datetime.utcnow().isoformat(),
            **data
        })

    async def run_session(self, num_messages: int = 3) -> Dict:
        """Run a complete test session"""
        session_start = datetime.now()

        print(f"\n  🧪 Starting session for {self.persona.name}")

        # Assign experiment variant if applicable
        if self.experiment_id:
            variant = await self.assign_experiment_variant()
            print(f"    🎲 Assigned variant: {variant}")

        # Navigate to chat
        if not await self.navigate_to_chat():
            return self._build_result(session_start)

        # Skip onboarding if present (click "Skip to chat" or just start typing)
        try:
            skip_button = self.page.locator('button:has-text("Skip"), button:has-text("skip")')
            if await skip_button.is_visible(timeout=2000):
                await skip_button.click()
                await asyncio.sleep(1)
        except:
            pass

        # Send initial message
        question = random.choice(self.persona.sample_questions)
        if await self.send_message(question):
            response = await self.wait_for_response()

            if response:
                # Scroll to see more content
                await self.scroll_page("down")
                await asyncio.sleep(0.5)

                # Try to expand research card
                await self.expand_research_card()

                # View a source
                await self.view_source()

        # Send follow-up messages
        for i in range(num_messages - 1):
            await asyncio.sleep(1)

            # Try clicking a follow-up chip first
            follow_up = await self.click_follow_up()

            if follow_up:
                # Wait for response from follow-up
                await self.wait_for_response()
            else:
                # Send another question
                remaining_questions = [q for q in self.persona.sample_questions
                                      if q not in [m["content"] for m in self.conversation_history if m["role"] == "user"]]
                if remaining_questions:
                    question = random.choice(remaining_questions)
                    if await self.send_message(question):
                        await self.wait_for_response()

        # Scroll through content
        await self.scroll_page("down")
        await asyncio.sleep(0.5)
        await self.scroll_page("down")

        # Final metrics
        self.metrics.total_session_time_ms = int((datetime.now() - session_start).total_seconds() * 1000)
        self.metrics.completed_conversation = self.metrics.messages_sent >= 2

        # Evaluate experience
        evaluation = await self.evaluate_experience()

        return self._build_result(session_start, evaluation)

    def _build_result(self, start_time: datetime, evaluation: Dict = None) -> Dict:
        """Build the result dictionary"""
        return {
            "session_id": self.metrics.session_id,
            "persona_id": self.persona.id,
            "persona_name": self.persona.name,
            "experiment_variant": self.metrics.experiment_variant,
            "timestamp": start_time.isoformat(),
            "metrics": {
                "page_load_time_ms": self.metrics.page_load_time_ms,
                "time_to_first_message_ms": self.metrics.time_to_first_message_ms,
                "response_stream_time_ms": self.metrics.response_stream_time_ms,
                "total_session_time_ms": self.metrics.total_session_time_ms,
                "messages_sent": self.metrics.messages_sent,
                "follow_ups_clicked": self.metrics.follow_ups_clicked,
                "research_card_expanded": self.metrics.research_card_expanded,
                "sources_viewed": self.metrics.sources_viewed,
                "scrolled_to_sources": self.metrics.scrolled_to_sources,
                "clicked_external_link": self.metrics.clicked_external_link,
                "completed_conversation": self.metrics.completed_conversation,
            },
            "evaluation": evaluation or {},
            "satisfaction": self.metrics.satisfaction_score,
            "would_return": self.metrics.would_return,
            "actions": self.metrics.actions,
            "errors": self.metrics.errors,
            "conversation": self.conversation_history,
        }


async def load_personas() -> List[PersonaConfig]:
    """Load personas from JSON file"""
    personas_path = os.path.join(project_root, "testing", "personas.json")

    if not os.path.exists(personas_path):
        # Default personas if file doesn't exist
        return [
            PersonaConfig(
                id="healing_beginner",
                name="Jake",
                description="32-year-old recovering from injury, new to peptides",
                experience_level="beginner",
                primary_goal="Recover from injury faster",
                concerns=["Safety", "Side effects", "How to start"],
                sample_questions=[
                    "What peptides help with injury recovery?",
                    "Is BPC-157 safe for beginners?",
                    "How do I dose TB-500 for tendon healing?",
                ],
                satisfaction_criteria=["Clear dosing info", "Safety warnings", "Scientific sources"]
            ),
            PersonaConfig(
                id="weight_loss_mom",
                name="Sarah",
                description="45-year-old looking for weight loss help",
                experience_level="beginner",
                primary_goal="Lose weight safely",
                concerns=["Cost", "Long-term effects", "Medical supervision"],
                sample_questions=[
                    "What's the difference between Semaglutide and Tirzepatide?",
                    "What are the side effects of GLP-1 peptides?",
                    "How much weight can I expect to lose?",
                ],
                satisfaction_criteria=["Realistic expectations", "Cost info", "Doctor consultation advice"]
            ),
        ]

    with open(personas_path) as f:
        data = json.load(f)

    return [
        PersonaConfig(
            id=p.get("id", f"persona_{i}"),
            name=p.get("name", f"Persona {i}"),
            description=p.get("description", ""),
            experience_level=p.get("experience_level", "intermediate"),
            primary_goal=p.get("primary_goal", "Research peptides"),
            concerns=p.get("concerns", []),
            sample_questions=p.get("sample_questions", ["What peptides should I research?"]),
            satisfaction_criteria=p.get("satisfaction_criteria", [])
        )
        for i, p in enumerate(data)
    ]


async def run_persona_test(
    persona: PersonaConfig,
    experiment_id: Optional[str] = None,
    headless: bool = True,
    num_messages: int = 3
) -> Dict:
    """Run a single persona test"""
    agent = ChatUIAgent(persona, experiment_id)

    try:
        await agent.start_browser(headless=headless)
        result = await agent.run_session(num_messages=num_messages)
        return result
    finally:
        await agent.close_browser()


async def run_all_personas(
    experiment_id: Optional[str] = None,
    headless: bool = True,
    personas_to_test: Optional[List[str]] = None
) -> Dict:
    """Run tests for all personas"""
    personas = await load_personas()

    if personas_to_test:
        personas = [p for p in personas if p.id in personas_to_test]

    print(f"\n{'='*60}")
    print(f"CHAT UI PERSONA TESTING")
    print(f"{'='*60}")
    print(f"Personas: {len(personas)}")
    print(f"Target: {WEB_URL}/chat")
    if experiment_id:
        print(f"Experiment: {experiment_id}")
    print()

    results = []

    for persona in personas:
        result = await run_persona_test(
            persona,
            experiment_id=experiment_id,
            headless=headless
        )
        results.append(result)

    # Generate summary
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "target_url": f"{WEB_URL}/chat",
        "experiment_id": experiment_id,
        "personas_tested": len(personas),
        "avg_satisfaction": sum(r.get("satisfaction", 0) for r in results) / len(results) if results else 0,
        "would_return_rate": sum(1 for r in results if r.get("would_return")) / len(results) if results else 0,
        "avg_messages": sum(r.get("metrics", {}).get("messages_sent", 0) for r in results) / len(results) if results else 0,
        "avg_response_time_ms": sum(r.get("metrics", {}).get("response_stream_time_ms", 0) for r in results) / len(results) if results else 0,
        "results": results
    }

    return summary


async def upload_results(results: Dict) -> bool:
    """Upload results to API"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{API_URL}/api/v1/analytics/chat-ui-tests",
                json=results,
                headers={"X-API-Key": API_KEY, "Content-Type": "application/json"}
            )
            return response.status_code == 200
    except:
        return False


async def main():
    """Run chat UI persona testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Chat UI Persona Testing")
    parser.add_argument("--personas", nargs="+", help="Specific persona IDs to test")
    parser.add_argument("--experiment", type=str, help="Experiment ID for A/B testing")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless")
    parser.add_argument("--show", action="store_true", help="Show browser (not headless)")

    args = parser.parse_args()

    headless = not args.show

    results = await run_all_personas(
        experiment_id=args.experiment,
        headless=headless,
        personas_to_test=args.personas
    )

    # Save locally
    output_path = os.path.join(project_root, "testing", "chat_ui_test_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Upload to API
    if await upload_results(results):
        print(f"\n✅ Results uploaded to API")
    else:
        print(f"\n⚠️ Could not upload to API")

    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Avg Satisfaction: {results['avg_satisfaction']:.1f}/10")
    print(f"Would Return Rate: {results['would_return_rate']*100:.0f}%")
    print(f"Avg Messages: {results['avg_messages']:.1f}")
    print(f"Avg Response Time: {results['avg_response_time_ms']:.0f}ms")

    print(f"\nBy Persona:")
    for r in results['results']:
        status = "✅" if r.get('satisfaction', 0) >= 7 else "⚠️"
        print(f"  {status} {r['persona_name']}: {r.get('satisfaction', 0)}/10 | Messages: {r['metrics']['messages_sent']}")

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
