#!/usr/bin/env python3
"""
Peptide AI - Automated Iteration Loop

Runs the full feedback loop:
1. Run persona tests
2. Analyze feedback
3. Generate improvement suggestions
4. Repeat until satisfaction >= 7/10 for all personas
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List
import httpx
from dotenv import load_dotenv

# Load environment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("PEPTIDE_AI_MASTER_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SATISFACTION_TARGET = 7.0
MAX_ITERATIONS = 10


async def get_feedback_summary() -> Dict:
    """Fetch feedback from API and summarize by persona"""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{API_URL}/api/v1/feedback?limit=100",
            headers={"X-API-Key": API_KEY}
        )
        if response.status_code != 200:
            return {"error": "Failed to fetch feedback"}

        feedback_items = response.json()

    # Group by persona
    by_persona = {}
    for item in feedback_items:
        persona_id = item.get("user_context", {}).get("persona_id", "unknown")
        if persona_id not in by_persona:
            by_persona[persona_id] = {
                "feedback": [],
                "satisfaction_scores": [],
                "issues": []
            }

        by_persona[persona_id]["feedback"].append(item)
        satisfaction = item.get("user_context", {}).get("satisfaction")
        if satisfaction:
            by_persona[persona_id]["satisfaction_scores"].append(satisfaction)

        # Extract issues
        for insight in item.get("insights", []):
            if insight and insight not in ["Could not evaluate", "Unknown"]:
                by_persona[persona_id]["issues"].append(insight)

    # Calculate averages
    summary = {}
    for persona_id, data in by_persona.items():
        scores = data["satisfaction_scores"]
        avg_satisfaction = sum(scores) / len(scores) if scores else 0
        summary[persona_id] = {
            "avg_satisfaction": avg_satisfaction,
            "feedback_count": len(data["feedback"]),
            "top_issues": list(set(data["issues"]))[:5],
            "meets_target": avg_satisfaction >= SATISFACTION_TARGET
        }

    return summary


async def generate_improvements(feedback_summary: Dict) -> str:
    """Use LLM to generate improvement suggestions"""
    import openai

    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

    # Build prompt with feedback
    prompt = """You are a product improvement specialist for Peptide AI, a research assistant for peptides.

Based on the user persona feedback below, suggest 3-5 SPECIFIC improvements to make to the AI responses.

## Current Persona Satisfaction:
"""

    struggling_personas = []
    for persona_id, data in feedback_summary.items():
        status = "✅" if data["meets_target"] else "❌"
        prompt += f"\n{status} **{persona_id}**: {data['avg_satisfaction']:.1f}/10"
        if not data["meets_target"]:
            struggling_personas.append(persona_id)
            prompt += f"\n   Issues: {'; '.join(data['top_issues'][:3])}"

    prompt += f"""

## Focus on these struggling personas: {', '.join(struggling_personas)}

## Suggest improvements in this format:

1. **[Improvement Title]**
   - Persona affected: [persona_id]
   - What to change: [Specific change to make to prompts or responses]
   - Why: [How this addresses their concern]

Be SPECIFIC - don't just say "add more detail", say exactly WHAT detail to add.
"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500
    )

    return response.choices[0].message.content


async def check_iteration_status() -> Dict:
    """Check if we've met targets for all personas"""
    summary = await get_feedback_summary()

    all_satisfied = all(
        data["meets_target"]
        for data in summary.values()
        if data["feedback_count"] > 0
    )

    avg_overall = sum(d["avg_satisfaction"] for d in summary.values()) / len(summary) if summary else 0

    return {
        "all_satisfied": all_satisfied,
        "avg_overall": avg_overall,
        "by_persona": summary
    }


async def run_iteration(iteration_num: int) -> Dict:
    """Run a single iteration of tests"""
    from automated_user_test import AutomatedTestRunner

    print(f"\n{'='*60}")
    print(f"🔄 ITERATION {iteration_num}")
    print(f"{'='*60}")

    # Load personas
    personas_path = os.path.join(project_root, "testing", "personas.json")
    with open(personas_path) as f:
        personas = json.load(f)

    # Run tests
    runner = AutomatedTestRunner(personas)
    results = await runner.run_all_personas(sessions_per_persona=2)

    # Save results
    output_path = os.path.join(
        project_root, "testing",
        f"test_results_iteration_{iteration_num}.json"
    )
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    return results


async def main():
    """Main iteration loop"""
    print("\n🚀 Starting Automated Iteration Loop")
    print(f"   Target satisfaction: {SATISFACTION_TARGET}/10")
    print(f"   Max iterations: {MAX_ITERATIONS}")

    for iteration in range(1, MAX_ITERATIONS + 1):
        # Run tests
        results = await run_iteration(iteration)

        # Check status
        status = await check_iteration_status()

        print(f"\n📊 Iteration {iteration} Results:")
        print(f"   Overall: {status['avg_overall']:.1f}/10")

        for persona_id, data in status["by_persona"].items():
            emoji = "✅" if data["meets_target"] else "❌"
            print(f"   {emoji} {persona_id}: {data['avg_satisfaction']:.1f}/10")

        if status["all_satisfied"]:
            print(f"\n✅ All personas satisfied! Stopping after {iteration} iterations.")
            break

        # Generate improvements
        print(f"\n🔧 Generating improvements...")
        improvements = await generate_improvements(status["by_persona"])

        # Save improvements
        improvements_path = os.path.join(
            project_root, "testing",
            f"improvements_iteration_{iteration}.md"
        )
        with open(improvements_path, "w") as f:
            f.write(f"# Iteration {iteration} Improvements\n\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}\n\n")
            f.write(improvements)

        print(f"\n📝 Improvements saved to {improvements_path}")
        print("\n⏸️  Review improvements and update prompts, then run next iteration.")

        # In automated mode, we'd apply improvements here
        # For now, we just report and exit
        break

    print("\n✅ Iteration complete!")


if __name__ == "__main__":
    asyncio.run(main())
