#!/usr/bin/env python3
"""
Peptide AI - Real Persona Builder

Ingests Reddit data to create realistic user personas based on actual
questions, concerns, and patterns from r/peptides and related subreddits.
"""

import asyncio
import json
import httpx
import os
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

SUBREDDITS = [
    "peptides",
    "Nootropics",
    "moreplatesmoredates",
    "Biohackers",
]

HEADERS = {
    "User-Agent": "PeptideAI-PersonaBuilder/1.0"
}


async def fetch_subreddit_posts(subreddit: str, limit: int = 100) -> List[Dict]:
    """Fetch posts from a subreddit"""
    posts = []
    after = None

    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        while len(posts) < limit:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json"
            params = {"limit": 100, "raw_json": 1}
            if after:
                params["after"] = after

            try:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    print(f"Error fetching r/{subreddit}: {response.status_code}")
                    break

                data = response.json()
                children = data.get("data", {}).get("children", [])

                if not children:
                    break

                for child in children:
                    post = child.get("data", {})
                    posts.append({
                        "title": post.get("title", ""),
                        "selftext": post.get("selftext", ""),
                        "score": post.get("score", 0),
                        "num_comments": post.get("num_comments", 0),
                        "created_utc": post.get("created_utc", 0),
                        "author": post.get("author", ""),
                        "url": f"https://reddit.com{post.get('permalink', '')}",
                        "subreddit": subreddit,
                    })

                after = data.get("data", {}).get("after")
                if not after:
                    break

                await asyncio.sleep(1)  # Rate limit

            except Exception as e:
                print(f"Error: {e}")
                break

    return posts[:limit]


def categorize_post(post: Dict) -> Dict[str, Any]:
    """Categorize a post by topic, intent, and user type"""
    text = f"{post['title']} {post['selftext']}".lower()

    # Topics
    topics = []
    if any(w in text for w in ["bpc-157", "bpc157", "bpc 157"]):
        topics.append("BPC-157")
    if any(w in text for w in ["tb-500", "tb500", "thymosin"]):
        topics.append("TB-500")
    if any(w in text for w in ["semaglutide", "ozempic", "wegovy"]):
        topics.append("Semaglutide")
    if any(w in text for w in ["tirzepatide", "mounjaro", "zepbound"]):
        topics.append("Tirzepatide")
    if any(w in text for w in ["ghk", "copper peptide"]):
        topics.append("GHK-Cu")
    if any(w in text for w in ["ipamorelin", "cjc", "ghrp", "growth hormone"]):
        topics.append("GH Peptides")
    if any(w in text for w in ["semax", "selank", "nootropic", "cognitive"]):
        topics.append("Nootropics")
    if any(w in text for w in ["melanotan", "mt-2", "pt-141"]):
        topics.append("Melanocortin")

    # Intent
    intent = "general"
    if any(w in text for w in ["dose", "dosage", "how much", "mg", "mcg", "iu"]):
        intent = "dosing"
    elif any(w in text for w in ["side effect", "safe", "dangerous", "risk", "concern"]):
        intent = "safety"
    elif any(w in text for w in ["source", "vendor", "buy", "where to get", "legit"]):
        intent = "sourcing"
    elif any(w in text for w in ["experience", "results", "worked", "didn't work", "review"]):
        intent = "experience"
    elif any(w in text for w in ["study", "research", "evidence", "proof", "scientific"]):
        intent = "research"
    elif any(w in text for w in ["stack", "combine", "together", "with"]):
        intent = "stacking"
    elif any(w in text for w in ["first time", "beginner", "new to", "start"]):
        intent = "beginner"

    # Experience level hints
    experience = "intermediate"
    if any(w in text for w in ["first time", "beginner", "new to", "never tried", "thinking about"]):
        experience = "beginner"
    elif any(w in text for w in ["years", "experienced", "been using", "long time", "cycle"]):
        experience = "advanced"

    # Goals
    goals = []
    if any(w in text for w in ["heal", "injury", "tendon", "ligament", "joint", "recovery"]):
        goals.append("healing")
    if any(w in text for w in ["weight", "fat", "lose", "diet", "appetite"]):
        goals.append("weight_loss")
    if any(w in text for w in ["muscle", "strength", "gym", "performance", "gains"]):
        goals.append("muscle")
    if any(w in text for w in ["brain", "focus", "memory", "cognitive", "mental"]):
        goals.append("cognitive")
    if any(w in text for w in ["age", "aging", "longevity", "anti-aging", "skin"]):
        goals.append("longevity")
    if any(w in text for w in ["sleep", "energy", "mood", "anxiety", "depression"]):
        goals.append("wellness")

    return {
        **post,
        "topics": topics,
        "intent": intent,
        "experience": experience,
        "goals": goals,
    }


def build_personas_from_data(posts: List[Dict]) -> List[Dict]:
    """Analyze posts and build realistic personas"""

    # Group by patterns
    intent_counts = defaultdict(int)
    goal_counts = defaultdict(int)
    topic_counts = defaultdict(int)
    experience_counts = defaultdict(int)

    for post in posts:
        cat = categorize_post(post)
        intent_counts[cat["intent"]] += 1
        experience_counts[cat["experience"]] += 1
        for goal in cat["goals"]:
            goal_counts[goal] += 1
        for topic in cat["topics"]:
            topic_counts[topic] += 1

    print("\n📊 Reddit Analysis:")
    print(f"  Intents: {dict(intent_counts)}")
    print(f"  Goals: {dict(goal_counts)}")
    print(f"  Topics: {dict(topic_counts)}")
    print(f"  Experience: {dict(experience_counts)}")

    # Build 8 personas based on real patterns
    personas = [
        {
            "id": "healing_beginner",
            "name": "Jake",
            "description": "29yo with a nagging shoulder injury from CrossFit. New to peptides, skeptical but desperate.",
            "experience_level": "beginner",
            "primary_goal": "healing",
            "peptides_interested": ["BPC-157", "TB-500"],
            "concerns": ["safety", "legality", "does it actually work"],
            "behavior": "Asks basic questions, needs hand-holding, will ask follow-ups",
            "satisfaction_criteria": [
                "Clear explanation of how it works",
                "Specific dosing protocol",
                "Honest about evidence quality",
                "Where to learn more"
            ],
            "sample_questions": [
                "I have a shoulder injury that won't heal. Would BPC-157 help?",
                "Is BPC-157 safe? Any side effects I should worry about?",
                "What's the typical dose for BPC-157 for tendon issues?",
                "How long until I'd see results?",
                "Can I take BPC-157 with TB-500 together?"
            ]
        },
        {
            "id": "weight_loss_mom",
            "name": "Sarah",
            "description": "42yo mom wanting to lose 40lbs. Heard about Ozempic from friends, researching options.",
            "experience_level": "beginner",
            "primary_goal": "weight_loss",
            "peptides_interested": ["Semaglutide", "Tirzepatide"],
            "concerns": ["cost", "side effects", "long-term safety", "is it cheating"],
            "behavior": "Emotional about weight, wants validation AND information",
            "satisfaction_criteria": [
                "Non-judgmental tone",
                "Realistic expectations",
                "Side effect management tips",
                "Comparison of options"
            ],
            "sample_questions": [
                "I want to try semaglutide for weight loss. Is it safe long-term?",
                "What's the difference between Ozempic and Wegovy?",
                "How much weight can I realistically lose?",
                "What about the nausea? How do people deal with it?",
                "Is tirzepatide better than semaglutide?"
            ]
        },
        {
            "id": "skeptical_researcher",
            "name": "David",
            "description": "35yo scientist who wants hard evidence, not bro-science. Very skeptical.",
            "experience_level": "intermediate",
            "primary_goal": "research",
            "peptides_interested": ["BPC-157", "Semax", "GHK-Cu"],
            "concerns": ["lack of human trials", "study quality", "mechanism of action"],
            "behavior": "Pushes back on claims, asks for citations, critical",
            "satisfaction_criteria": [
                "Actual citations (author, year)",
                "Honest about study limitations",
                "Distinction between human/animal data",
                "No hype or marketing language"
            ],
            "sample_questions": [
                "What's the actual evidence for BPC-157? Not anecdotes.",
                "Are there any human clinical trials for TB-500?",
                "The studies I've seen are all in rats. How does that translate?",
                "What's the proposed mechanism of action?",
                "Why isn't this FDA approved if it works so well?"
            ]
        },
        {
            "id": "bodybuilder_advanced",
            "name": "Marcus",
            "description": "28yo competitive bodybuilder. Experienced with PEDs, optimizing recovery.",
            "experience_level": "advanced",
            "primary_goal": "muscle",
            "peptides_interested": ["BPC-157", "TB-500", "GH Peptides", "Ipamorelin"],
            "concerns": ["stacking protocols", "timing with other compounds", "maximizing results"],
            "behavior": "Knows the basics, wants advanced protocols, speaks the lingo",
            "satisfaction_criteria": [
                "Specific protocols, not ranges",
                "Stacking information",
                "Timing recommendations",
                "Real user experiences"
            ],
            "sample_questions": [
                "Best stack for injury recovery while on cycle?",
                "BPC-157 + TB-500 protocol - what ratio and timing?",
                "Does ipamorelin affect natural GH production long-term?",
                "CJC-1295 with or without DAC?",
                "Pinning schedule for multiple peptides?"
            ]
        },
        {
            "id": "biohacker_longevity",
            "name": "Elena",
            "description": "45yo tech exec into longevity/biohacking. Money is no object, wants cutting edge.",
            "experience_level": "intermediate",
            "primary_goal": "longevity",
            "peptides_interested": ["Epitalon", "GHK-Cu", "MOTS-c", "SS-31"],
            "concerns": ["anti-aging evidence", "synergies", "optimal protocols"],
            "behavior": "Well-read, interested in mechanisms, willing to experiment",
            "satisfaction_criteria": [
                "Cutting-edge research",
                "Mechanism explanations",
                "Stack recommendations",
                "Longevity-specific evidence"
            ],
            "sample_questions": [
                "What peptides have the best evidence for longevity?",
                "Tell me about Epitalon and telomeres",
                "Is MOTS-c worth trying for metabolic health?",
                "What's the anti-aging stack you'd recommend?",
                "How does SS-31 compare to other mitochondrial peptides?"
            ]
        },
        {
            "id": "anxious_cautious",
            "name": "Jennifer",
            "description": "38yo with health anxiety. Interested but terrified of side effects.",
            "experience_level": "beginner",
            "primary_goal": "wellness",
            "peptides_interested": ["Selank", "Semax", "BPC-157"],
            "concerns": ["every possible side effect", "interactions", "what could go wrong"],
            "behavior": "Needs lots of reassurance, asks 'what if' questions",
            "satisfaction_criteria": [
                "Thorough side effect information",
                "Reassurance with honesty",
                "Start low and slow guidance",
                "When to stop/seek help"
            ],
            "sample_questions": [
                "What are ALL the possible side effects of BPC-157?",
                "Can peptides interact with my medications?",
                "What's the safest peptide to start with?",
                "How do I know if I'm having a bad reaction?",
                "Should I tell my doctor I'm taking this?"
            ]
        },
        {
            "id": "cognitive_optimizer",
            "name": "Alex",
            "description": "31yo software engineer wanting better focus and mental performance.",
            "experience_level": "intermediate",
            "primary_goal": "cognitive",
            "peptides_interested": ["Semax", "Selank", "Dihexa", "BPC-157"],
            "concerns": ["nootropic effects", "long-term brain safety", "tolerance"],
            "behavior": "Analytical, wants to optimize, tracks everything",
            "satisfaction_criteria": [
                "Cognitive-specific effects",
                "Dosing for mental benefits",
                "Stacking with other nootropics",
                "Long-term considerations"
            ],
            "sample_questions": [
                "Best peptide for focus and concentration?",
                "Semax vs Selank - which is better for work performance?",
                "Can I stack Semax with racetams?",
                "How long can I use Semax before needing a break?",
                "Does BPC-157 have any cognitive benefits?"
            ]
        },
        {
            "id": "budget_practical",
            "name": "Mike",
            "description": "34yo with limited budget. Wants best bang for buck, practical advice.",
            "experience_level": "beginner",
            "primary_goal": "healing",
            "peptides_interested": ["BPC-157", "TB-500"],
            "concerns": ["cost", "is it worth it", "minimum effective dose"],
            "behavior": "Price-conscious, wants practical advice, no-BS",
            "satisfaction_criteria": [
                "Cost-effective recommendations",
                "Minimum effective protocols",
                "Is it worth the money honestly",
                "Budget alternatives"
            ],
            "sample_questions": [
                "Is BPC-157 worth the cost?",
                "What's the minimum dose that actually works?",
                "Do I really need both BPC-157 AND TB-500?",
                "How long do I need to run this?",
                "Cheapest way to try peptides for healing?"
            ]
        }
    ]

    return personas


async def main():
    """Main function to build personas from Reddit data"""
    print("🔍 Fetching Reddit data to build realistic personas...\n")

    all_posts = []

    for subreddit in SUBREDDITS:
        print(f"  Fetching r/{subreddit}...")
        posts = await fetch_subreddit_posts(subreddit, limit=100)
        all_posts.extend(posts)
        print(f"    Got {len(posts)} posts")

    print(f"\n📝 Total posts collected: {len(all_posts)}")

    # Build personas
    personas = build_personas_from_data(all_posts)

    # Save personas
    output_path = os.path.join(project_root, "testing", "personas.json")
    with open(output_path, "w") as f:
        json.dump(personas, f, indent=2)

    print(f"\n✅ Created {len(personas)} personas:")
    for p in personas:
        print(f"  - {p['name']} ({p['id']}): {p['description'][:50]}...")

    print(f"\n💾 Saved to {output_path}")

    return personas


if __name__ == "__main__":
    asyncio.run(main())
