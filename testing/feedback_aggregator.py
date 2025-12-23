#!/usr/bin/env python3
"""
Peptide AI - Feedback Aggregator

Takes browser agent test results and generates:
1. Master product brief (prioritized issues across all personas)
2. Implementation tasks (actionable MDs)
3. System prompt updates (based on what's working/not working)
4. Progress tracking across runs
"""

import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import openai
from dotenv import load_dotenv

# Load environment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
RUNS_DIR = os.path.join(project_root, "testing", "runs")
PROMPTS_DIR = os.path.join(project_root, "prompts")


class FeedbackAggregator:
    """Aggregates feedback from browser agent tests into actionable outputs"""

    def __init__(self):
        self.openai = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        os.makedirs(RUNS_DIR, exist_ok=True)
        os.makedirs(PROMPTS_DIR, exist_ok=True)

    async def process_run(self, results_path: str) -> Dict:
        """Process a test run and generate all outputs"""

        # Load results
        with open(results_path) as f:
            results = json.load(f)

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(RUNS_DIR, run_id)
        os.makedirs(run_dir, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"PROCESSING RUN: {run_id}")
        print(f"{'='*60}")

        # 1. Generate master product brief
        print("\n1. Generating master product brief...")
        product_brief = await self._generate_product_brief(results)
        brief_path = os.path.join(run_dir, "product_brief.md")
        with open(brief_path, "w") as f:
            f.write(product_brief)
        print(f"   Saved to {brief_path}")

        # 2. Generate implementation tasks
        print("\n2. Generating implementation tasks...")
        impl_tasks = await self._generate_implementation_tasks(results, product_brief)
        tasks_path = os.path.join(run_dir, "implementation_tasks.md")
        with open(tasks_path, "w") as f:
            f.write(impl_tasks)
        print(f"   Saved to {tasks_path}")

        # 3. Generate system prompt updates
        print("\n3. Generating system prompt updates...")
        prompt_updates = await self._generate_prompt_updates(results)
        prompts_path = os.path.join(run_dir, "prompt_updates.md")
        with open(prompts_path, "w") as f:
            f.write(prompt_updates)
        print(f"   Saved to {prompts_path}")

        # 4. Update progress tracker
        print("\n4. Updating progress tracker...")
        progress = self._update_progress_tracker(results, run_id)

        # 5. Save run summary
        summary = {
            "run_id": run_id,
            "timestamp": results.get("timestamp"),
            "overall_satisfaction": results.get("summary", {}).get("overall_satisfaction", 0),
            "would_return_rate": results.get("summary", {}).get("would_return_rate", 0),
            "personas_at_target": sum(
                1 for p in results.get("summary", {}).get("by_persona", {}).values()
                if p.get("satisfaction", 0) >= 7
            ),
            "total_personas": len(results.get("summary", {}).get("by_persona", {})),
            "outputs": {
                "product_brief": brief_path,
                "implementation_tasks": tasks_path,
                "prompt_updates": prompts_path,
            }
        }

        summary_path = os.path.join(run_dir, "run_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'='*60}")
        print(f"RUN {run_id} COMPLETE")
        print(f"{'='*60}")
        print(f"Overall Satisfaction: {summary['overall_satisfaction']:.1f}/10")
        print(f"Personas at Target (7+): {summary['personas_at_target']}/{summary['total_personas']}")
        print(f"\nOutputs saved to: {run_dir}")

        return summary

    async def _generate_product_brief(self, results: Dict) -> str:
        """Generate a master product brief from all persona feedback"""

        # Collect all feedback
        feedback_items = []
        for persona_result in results.get("results", []):
            persona_name = persona_result.get("persona_name", "Unknown")
            persona_id = persona_result.get("persona_id", "unknown")
            evaluation = persona_result.get("evaluation", {})
            final_state = persona_result.get("final_state", {})

            feedback_items.append({
                "persona": persona_name,
                "persona_id": persona_id,
                "satisfaction": evaluation.get("overall_satisfaction", 5),
                "would_return": evaluation.get("would_return", False),
                "what_worked": evaluation.get("what_worked", ""),
                "what_needs_improvement": evaluation.get("what_needs_improvement", ""),
                "specific_feedback": evaluation.get("specific_feedback", ""),
                "chats": final_state.get("total_chats", 0),
                "peptides_researched": final_state.get("peptides_researched", []),
            })

        prompt = f"""You are a product manager analyzing user feedback for Peptide AI, a research assistant for peptide science.

Here is feedback from {len(feedback_items)} different user personas who tested the app:

{json.dumps(feedback_items, indent=2)}

Generate a comprehensive PRODUCT BRIEF in markdown format with:

1. **Executive Summary** - Overall findings in 2-3 sentences

2. **Satisfaction Metrics**
   - Overall satisfaction score and trend
   - Return rate
   - Personas at target (7+) vs not

3. **What's Working Well** (prioritized list)
   - Features/aspects that multiple personas praised
   - Include which personas mentioned each

4. **Critical Issues** (prioritized by impact)
   - Issues mentioned by multiple personas = higher priority
   - Issues from low-satisfaction personas = higher priority
   - Include specific persona quotes

5. **Feature Requests** (prioritized)
   - Requested features with persona attribution
   - Group similar requests

6. **Persona-Specific Insights**
   - Brief summary for each persona type
   - What would move them from 7 to 9+?

7. **Recommended Actions** (top 5)
   - Specific, actionable items
   - Expected impact on satisfaction

Format as clean markdown. Be specific and actionable."""

        response = await self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3000
        )

        content = response.choices[0].message.content or ""

        # Add header
        header = f"""# Peptide AI - Product Brief
**Run Date:** {results.get('timestamp', 'Unknown')}
**Personas Tested:** {len(feedback_items)}
**Overall Satisfaction:** {results.get('summary', {}).get('overall_satisfaction', 0):.1f}/10

---

"""
        return header + content

    async def _generate_implementation_tasks(self, results: Dict, product_brief: str) -> str:
        """Generate specific implementation tasks from the product brief"""

        prompt = f"""You are a technical lead converting a product brief into implementation tasks.

Here is the product brief:
---
{product_brief}
---

Generate an IMPLEMENTATION TASKS document in markdown with:

1. **High Priority Tasks** (do this week)
   - Tasks that will have immediate impact on satisfaction
   - Include estimated effort (S/M/L)
   - Include which file(s) likely need changes

2. **Medium Priority Tasks** (do this month)
   - Important but not urgent
   - Include effort and files

3. **Low Priority / Nice to Have**
   - Future improvements
   - Include effort and files

4. **System Prompt Updates Needed**
   - Specific changes to RAG prompts
   - Changes to response formatting

5. **Technical Debt / Infrastructure**
   - Any underlying issues to address

For each task include:
- [ ] Task description
- **Effort:** S/M/L
- **Impact:** Which personas benefit
- **Files:** Likely files to modify
- **Notes:** Implementation hints

Format as clean markdown with checkboxes."""

        response = await self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2500
        )

        content = response.choices[0].message.content or ""

        header = f"""# Peptide AI - Implementation Tasks
**Generated:** {datetime.now().isoformat()}
**Based on:** Product Brief from {results.get('timestamp', 'Unknown')}

---

"""
        return header + content

    async def _generate_prompt_updates(self, results: Dict) -> str:
        """Generate specific system prompt updates based on feedback"""

        # Collect feedback about response quality
        response_feedback = []
        for persona_result in results.get("results", []):
            evaluation = persona_result.get("evaluation", {})
            response_feedback.append({
                "persona": persona_result.get("persona_name"),
                "persona_id": persona_result.get("persona_id"),
                "satisfaction": evaluation.get("overall_satisfaction", 5),
                "what_worked": evaluation.get("what_worked", ""),
                "what_needs_improvement": evaluation.get("what_needs_improvement", ""),
            })

        prompt = f"""You are an AI prompt engineer optimizing the system prompts for Peptide AI.

Current feedback from user testing:
{json.dumps(response_feedback, indent=2)}

The main system prompt is in llm/rag_pipeline.py and controls how the AI responds to peptide questions.

Generate a PROMPT UPDATES document with:

1. **Current Issues Identified**
   - What's not working based on feedback
   - Which personas are affected

2. **Proposed System Prompt Additions**
   - Specific text to ADD to the system prompt
   - Explain why each addition helps

3. **Proposed System Prompt Modifications**
   - Text to CHANGE in the system prompt
   - Before/after examples

4. **Response Mode Adjustments**
   - Changes needed for each mode (balanced, skeptic, actionable)

5. **Citation/Source Improvements**
   - How to better present evidence
   - Format changes

6. **Persona-Specific Adaptations**
   - Should responses adapt based on user type?
   - How to detect user type from questions

Provide specific, copy-paste ready text for prompt changes."""

        response = await self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2500
        )

        content = response.choices[0].message.content or ""

        header = f"""# Peptide AI - System Prompt Updates
**Generated:** {datetime.now().isoformat()}
**Purpose:** Improve AI responses based on user feedback

---

"""
        return header + content

    def _update_progress_tracker(self, results: Dict, run_id: str) -> Dict:
        """Update the progress tracker with this run's results"""

        tracker_path = os.path.join(RUNS_DIR, "progress_tracker.json")

        # Load existing tracker or create new
        if os.path.exists(tracker_path):
            with open(tracker_path) as f:
                tracker = json.load(f)
        else:
            tracker = {
                "runs": [],
                "best_satisfaction": 0,
                "target_satisfaction": 8.0,
                "iterations_to_target": None,
            }

        # Add this run
        summary = results.get("summary", {})
        by_persona = summary.get("by_persona", {})

        run_entry = {
            "run_id": run_id,
            "timestamp": results.get("timestamp"),
            "overall_satisfaction": summary.get("overall_satisfaction", 0),
            "would_return_rate": summary.get("would_return_rate", 0),
            "personas_at_target": sum(1 for p in by_persona.values() if p.get("satisfaction", 0) >= 7),
            "total_personas": len(by_persona),
            "by_persona": {
                pid: {
                    "satisfaction": data.get("satisfaction", 0),
                    "would_return": data.get("would_return", False),
                    "chats": data.get("chats", 0),
                }
                for pid, data in by_persona.items()
            }
        }

        tracker["runs"].append(run_entry)

        # Update best
        if run_entry["overall_satisfaction"] > tracker["best_satisfaction"]:
            tracker["best_satisfaction"] = run_entry["overall_satisfaction"]

        # Check if target reached
        if run_entry["overall_satisfaction"] >= tracker["target_satisfaction"] and tracker["iterations_to_target"] is None:
            tracker["iterations_to_target"] = len(tracker["runs"])

        # Save tracker
        with open(tracker_path, "w") as f:
            json.dump(tracker, f, indent=2)

        # Generate progress report
        self._generate_progress_report(tracker)

        return tracker

    def _generate_progress_report(self, tracker: Dict):
        """Generate a markdown progress report"""

        report_path = os.path.join(RUNS_DIR, "PROGRESS.md")

        runs = tracker.get("runs", [])

        # Build report
        lines = [
            "# Peptide AI - Testing Progress Report",
            "",
            f"**Target Satisfaction:** {tracker.get('target_satisfaction', 8.0)}/10",
            f"**Best Achieved:** {tracker.get('best_satisfaction', 0):.1f}/10",
            f"**Total Runs:** {len(runs)}",
            "",
            "---",
            "",
            "## Satisfaction Over Time",
            "",
            "| Run | Date | Overall | Return Rate | At Target |",
            "|-----|------|---------|-------------|-----------|",
        ]

        for run in runs:
            date = run.get("timestamp", "")[:10] if run.get("timestamp") else "Unknown"
            lines.append(
                f"| {run.get('run_id', 'N/A')} | {date} | "
                f"{run.get('overall_satisfaction', 0):.1f}/10 | "
                f"{run.get('would_return_rate', 0)*100:.0f}% | "
                f"{run.get('personas_at_target', 0)}/{run.get('total_personas', 0)} |"
            )

        lines.extend([
            "",
            "## Persona Progress",
            "",
        ])

        # Track persona progress across runs
        if runs:
            persona_ids = list(runs[-1].get("by_persona", {}).keys())

            lines.append("| Persona | " + " | ".join([f"Run {i+1}" for i in range(len(runs))]) + " |")
            lines.append("|---------|" + "|".join(["-------" for _ in runs]) + "|")

            for pid in persona_ids:
                scores = []
                for run in runs:
                    score = run.get("by_persona", {}).get(pid, {}).get("satisfaction", "N/A")
                    if isinstance(score, (int, float)):
                        emoji = "✅" if score >= 7 else "⚠️" if score >= 5 else "❌"
                        scores.append(f"{emoji} {score}")
                    else:
                        scores.append("N/A")
                lines.append(f"| {pid} | " + " | ".join(scores) + " |")

        lines.extend([
            "",
            "## Next Steps",
            "",
            "See latest run's `implementation_tasks.md` for specific actions.",
            "",
            "---",
            f"*Last updated: {datetime.now().isoformat()}*",
        ])

        with open(report_path, "w") as f:
            f.write("\n".join(lines))

        print(f"   Progress report saved to {report_path}")


async def main():
    """Process the latest browser test results"""

    results_path = os.path.join(project_root, "testing", "browser_test_results.json")

    if not os.path.exists(results_path):
        print("No browser test results found. Run browser_agent.py first.")
        return

    aggregator = FeedbackAggregator()
    summary = await aggregator.process_run(results_path)

    print("\n" + "="*60)
    print("FEEDBACK AGGREGATION COMPLETE")
    print("="*60)
    print(f"\nRun ID: {summary['run_id']}")
    print(f"Overall Satisfaction: {summary['overall_satisfaction']:.1f}/10")
    print(f"Personas at Target: {summary['personas_at_target']}/{summary['total_personas']}")
    print(f"\nOutputs:")
    for name, path in summary['outputs'].items():
        print(f"  - {name}: {path}")


if __name__ == "__main__":
    asyncio.run(main())
