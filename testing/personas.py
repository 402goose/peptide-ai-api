"""
Peptide AI - User Personas for Testing

Defines realistic user personas with different:
- Knowledge levels
- Goals and conditions
- Attitudes and communication styles
- Conversation patterns
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import random


class KnowledgeLevel(str, Enum):
    EXPERT = "expert"           # Knows peptide science, protocols, sources
    INTERMEDIATE = "intermediate"  # Has used peptides, knows basics
    BEGINNER = "beginner"       # Curious but new to peptides
    COMPLETE_NOVICE = "novice"  # Heard about peptides, knows nothing


class Attitude(str, Enum):
    ENTHUSIASTIC = "enthusiastic"   # Excited, ready to try
    SKEPTICAL = "skeptical"         # Doubts efficacy, wants proof
    CAUTIOUS = "cautious"           # Worried about safety
    ANALYTICAL = "analytical"       # Wants data and mechanisms
    DESPERATE = "desperate"         # Has tried everything, needs help
    CASUAL = "casual"               # Just exploring, no urgency


class CommunicationStyle(str, Enum):
    DETAILED = "detailed"       # Writes long messages, lots of context
    BRIEF = "brief"             # Short, to the point
    QUESTIONING = "questioning" # Asks lots of follow-ups
    CONVERSATIONAL = "conversational"  # Chatty, friendly
    TECHNICAL = "technical"     # Uses scientific terms


@dataclass
class Persona:
    """A user persona for testing"""
    name: str
    knowledge_level: KnowledgeLevel
    attitude: Attitude
    communication_style: CommunicationStyle
    primary_goals: List[str]
    health_conditions: List[str]
    age_range: str
    background: str
    typical_questions: List[str]
    follow_up_patterns: List[str]
    success_criteria: List[str]  # What would make this persona satisfied
    frustration_triggers: List[str]  # What would frustrate this persona


# Define our test personas
PERSONAS: List[Persona] = [
    # 1. The Hardcore Biohacker
    Persona(
        name="Marcus - The Biohacker",
        knowledge_level=KnowledgeLevel.EXPERT,
        attitude=Attitude.ANALYTICAL,
        communication_style=CommunicationStyle.TECHNICAL,
        primary_goals=["optimize recovery", "enhance cognition", "longevity"],
        health_conditions=["none - preventive optimization"],
        age_range="30-40",
        background="Software engineer who tracks everything. Has used BPC-157, TB-500, and various nootropics. Reads research papers.",
        typical_questions=[
            "What's the optimal BPC-157 and TB-500 stack for tendon repair? I've seen conflicting info on timing.",
            "Has there been any research on Epitalon's effects on telomere length in humans, not just in vitro?",
            "I'm running CJC-1295 with Ipamorelin. Should I cycle off or is continuous use safe based on the literature?",
            "What's the mechanism behind GHK-Cu's wound healing properties? Is it primarily through TGF-beta?",
            "Compare Semax vs Selank for cognitive enhancement - what does the Russian research actually show?",
        ],
        follow_up_patterns=[
            "What's the half-life and optimal dosing frequency?",
            "Are there any studies on long-term use?",
            "What biomarkers should I track?",
            "How does this interact with [other peptide]?",
        ],
        success_criteria=[
            "Provides specific dosing protocols with reasoning",
            "Cites actual research papers",
            "Discusses mechanisms of action",
            "Acknowledges nuance and gaps in research",
        ],
        frustration_triggers=[
            "Generic safety disclaimers without substance",
            "Refusing to discuss protocols",
            "Not knowing about specific peptides",
            "Overly simplified explanations",
        ]
    ),

    # 2. The Curious Beginner
    Persona(
        name="Sarah - The Curious Beginner",
        knowledge_level=KnowledgeLevel.BEGINNER,
        attitude=Attitude.ENTHUSIASTIC,
        communication_style=CommunicationStyle.CONVERSATIONAL,
        primary_goals=["heal knee injury", "general wellness"],
        health_conditions=["ACL tear recovery", "mild anxiety"],
        age_range="28-35",
        background="Yoga instructor recovering from knee surgery. Heard about peptides from a friend who had great results. Wants to try but doesn't know where to start.",
        typical_questions=[
            "I had ACL surgery 3 months ago and recovery is slow. A friend said BPC-157 helped her heal faster - is this legit?",
            "I'm totally new to peptides. Where do I even start? Is this stuff safe?",
            "What's the difference between all these peptides I keep hearing about?",
            "Do I need a prescription for this? Is it legal?",
            "How do peptides actually work? Like, what do they do in your body?",
        ],
        follow_up_patterns=[
            "That sounds complicated - can you explain it more simply?",
            "How would I actually take this? Like injections?",
            "How long until I'd see results?",
            "What if it doesn't work?",
        ],
        success_criteria=[
            "Clear, jargon-free explanations",
            "Specific actionable first steps",
            "Addresses safety concerns directly",
            "Makes her feel confident to try",
        ],
        frustration_triggers=[
            "Too much technical jargon",
            "Vague non-answers",
            "Scary warnings without context",
            "Not addressing her specific situation",
        ]
    ),

    # 3. The Skeptic
    Persona(
        name="David - The Skeptic",
        knowledge_level=KnowledgeLevel.INTERMEDIATE,
        attitude=Attitude.SKEPTICAL,
        communication_style=CommunicationStyle.QUESTIONING,
        primary_goals=["chronic pain relief", "verify claims"],
        health_conditions=["chronic back pain", "previous failed treatments"],
        age_range="45-55",
        background="Accountant with chronic back pain for 10 years. Has tried everything - physical therapy, injections, even surgery. Skeptical of 'miracle cures' but desperate enough to research.",
        typical_questions=[
            "I keep seeing people claim BPC-157 is a miracle for pain. What's the ACTUAL evidence? Not anecdotes.",
            "Why isn't this FDA approved if it's so effective? What's the catch?",
            "How do I know the research isn't just funded by people selling this stuff?",
            "I've been burned by supplements before. Why should I believe peptides are different?",
            "What are the REAL risks? Not the marketing spin.",
        ],
        follow_up_patterns=[
            "But that study was only in rats, right?",
            "What about long-term side effects?",
            "How do I know I'm getting real stuff and not fake?",
            "Why don't more doctors recommend this then?",
        ],
        success_criteria=[
            "Honest about limitations of evidence",
            "Doesn't oversell or hype",
            "Provides balanced risk/benefit analysis",
            "Acknowledges his skepticism is valid",
        ],
        frustration_triggers=[
            "Hype or marketing language",
            "Dismissing his concerns",
            "Cherry-picking positive studies",
            "Not acknowledging risks",
        ]
    ),

    # 4. The Health-Anxious
    Persona(
        name="Jennifer - The Cautious One",
        knowledge_level=KnowledgeLevel.BEGINNER,
        attitude=Attitude.CAUTIOUS,
        communication_style=CommunicationStyle.DETAILED,
        primary_goals=["gut healing", "autoimmune support"],
        health_conditions=["IBS", "Hashimoto's thyroiditis", "multiple food sensitivities"],
        age_range="35-45",
        background="Has multiple autoimmune issues and is very careful about anything she puts in her body. Has had bad reactions to medications before. Researches extensively before trying anything.",
        typical_questions=[
            "I have Hashimoto's and IBS. I've heard BPC-157 might help with gut healing, but I'm worried about it affecting my thyroid. Is this safe for autoimmune conditions?",
            "I react badly to a lot of things. What are ALL the possible side effects of these peptides?",
            "Should I talk to my doctor first? Will they even know about this?",
            "I read something about peptides potentially stimulating cancer cells. Should I be worried?",
            "What's the absolute safest way to try this if I decide to?",
        ],
        follow_up_patterns=[
            "What if I have a bad reaction? How would I know?",
            "Are there any contraindications with my medications?",
            "Should I start with a tiny dose?",
            "How pure/safe are these products typically?",
        ],
        success_criteria=[
            "Takes her health concerns seriously",
            "Provides thorough safety information",
            "Suggests conservative approach",
            "Encourages medical consultation without dismissing peptides",
        ],
        frustration_triggers=[
            "Dismissing her concerns as anxiety",
            "Pushing her to try things quickly",
            "Not acknowledging autoimmune complexity",
            "Generic responses that ignore her conditions",
        ]
    ),

    # 5. The Athlete
    Persona(
        name="Mike - The Competitive Athlete",
        knowledge_level=KnowledgeLevel.INTERMEDIATE,
        attitude=Attitude.ENTHUSIASTIC,
        communication_style=CommunicationStyle.BRIEF,
        primary_goals=["injury recovery", "performance enhancement", "faster healing"],
        health_conditions=["rotator cuff strain", "tennis elbow"],
        age_range="25-35",
        background="CrossFit competitor dealing with overuse injuries. Knows several people at his gym who use peptides. Wants to recover faster and get back to training.",
        typical_questions=[
            "Rotator cuff is killing me. BPC-157 or TB-500? Or both? Need to compete in 6 weeks.",
            "Best protocol for tendon healing? I need fast results.",
            "Will this show up on a drug test?",
            "Can I keep training while using these?",
            "What's the fastest way to heal a tennis elbow?",
        ],
        follow_up_patterns=[
            "How fast will this work?",
            "Can I stack it with anything else?",
            "Local injection or subcutaneous?",
            "What dose do most athletes use?",
        ],
        success_criteria=[
            "Gives direct, actionable protocols",
            "Addresses his timeline/competition",
            "Provides realistic expectations",
            "Understands athletic context",
        ],
        frustration_triggers=[
            "Long-winded explanations",
            "Too many warnings/disclaimers",
            "Not understanding urgency",
            "Vague timelines",
        ]
    ),

    # 6. The Weight Loss Seeker
    Persona(
        name="Lisa - Weight Loss Journey",
        knowledge_level=KnowledgeLevel.COMPLETE_NOVICE,
        attitude=Attitude.DESPERATE,
        communication_style=CommunicationStyle.CONVERSATIONAL,
        primary_goals=["weight loss", "appetite control"],
        health_conditions=["obesity", "pre-diabetic", "high blood pressure"],
        age_range="40-50",
        background="Has struggled with weight her whole life. Recently heard about Semaglutide/Ozempic from friends and social media. Pre-diabetic and doctor is pushing her to lose weight.",
        typical_questions=[
            "Everyone's talking about Ozempic for weight loss. Is this the same as semaglutide? Can I get it without diabetes?",
            "I've tried every diet. Will this actually work for someone like me?",
            "What's the difference between Ozempic, Wegovy, and Mounjaro? So confusing.",
            "How much weight can I realistically lose? I need to lose 80 pounds.",
            "Are the side effects really that bad? My friend was so sick on it.",
        ],
        follow_up_patterns=[
            "Will I gain it all back if I stop?",
            "How long do people usually take this?",
            "Is there a cheaper option?",
            "What about tirzepatide - is that better?",
        ],
        success_criteria=[
            "Empathetic and non-judgmental",
            "Realistic expectations about weight loss",
            "Clear comparison of options",
            "Addresses her specific health conditions",
        ],
        frustration_triggers=[
            "Judgment about weight",
            "Unrealistic promises",
            "Not understanding desperation",
            "Ignoring her pre-existing conditions",
        ]
    ),

    # 7. The Anti-Aging Enthusiast
    Persona(
        name="Robert - The Longevity Seeker",
        knowledge_level=KnowledgeLevel.INTERMEDIATE,
        attitude=Attitude.ANALYTICAL,
        communication_style=CommunicationStyle.DETAILED,
        primary_goals=["anti-aging", "longevity", "cognitive preservation"],
        health_conditions=["age-related concerns", "family history of Alzheimer's"],
        age_range="55-65",
        background="Successful businessman who has the resources to optimize his health. Follows longevity researchers like David Sinclair. Wants to age well and protect his cognition.",
        typical_questions=[
            "I'm interested in Epitalon for longevity. What does the research actually show about telomere effects?",
            "What peptide stack would you recommend for someone my age focused on anti-aging and neuroprotection?",
            "GHK-Cu seems promising for skin and systemic anti-aging. What's the evidence?",
            "Should I be looking at growth hormone secretagogues? Concerned about cancer risk.",
            "What's the current thinking on thymosin alpha-1 for immune aging?",
        ],
        follow_up_patterns=[
            "What biomarkers would show this is working?",
            "How does this compare to other longevity interventions?",
            "What's the long-term safety data?",
            "Are there synergies with other things I'm doing (NAD+, metformin, etc.)?",
        ],
        success_criteria=[
            "Sophisticated discussion of mechanisms",
            "Honest about evidence gaps in longevity",
            "Practical protocols for his age group",
            "Addresses cancer risk concerns thoughtfully",
        ],
        frustration_triggers=[
            "Overpromising on longevity effects",
            "Not knowing about cutting-edge research",
            "Dismissing his interest as vanity",
            "Cookie-cutter recommendations",
        ]
    ),

    # 8. The Skin/Beauty Focused
    Persona(
        name="Emma - The Beauty Optimizer",
        knowledge_level=KnowledgeLevel.BEGINNER,
        attitude=Attitude.ENTHUSIASTIC,
        communication_style=CommunicationStyle.CONVERSATIONAL,
        primary_goals=["skin rejuvenation", "hair growth", "collagen production"],
        health_conditions=["hair thinning", "aging skin"],
        age_range="35-45",
        background="Marketing executive who takes care of her appearance. Has done Botox and fillers. Interested in peptides as a more 'natural' approach to anti-aging.",
        typical_questions=[
            "I keep seeing GHK-Cu in skincare products. Does it actually work? Is it better to inject it?",
            "What peptides are best for collagen and skin elasticity?",
            "My hair is thinning. Are there peptides that help with hair growth?",
            "What's the difference between topical and injectable peptides for skin?",
            "I want to look younger but don't want to look 'done'. What would you recommend?",
        ],
        follow_up_patterns=[
            "How long until I see results?",
            "Can I use this with my other skincare?",
            "Are there before/after photos or studies?",
            "What's the most popular option?",
        ],
        success_criteria=[
            "Practical beauty-focused recommendations",
            "Realistic timeline expectations",
            "Addresses both topical and injectable options",
            "Understands aesthetic goals",
        ],
        frustration_triggers=[
            "Dismissing beauty concerns as superficial",
            "Too much science, not enough practical advice",
            "Not knowing about cosmetic applications",
            "Unrealistic promises",
        ]
    ),
]


def get_random_persona() -> Persona:
    """Get a random persona for testing"""
    return random.choice(PERSONAS)


def get_persona_by_name(name: str) -> Persona:
    """Get a specific persona by name"""
    for persona in PERSONAS:
        if name.lower() in persona.name.lower():
            return persona
    raise ValueError(f"Persona not found: {name}")


def get_personas_by_knowledge(level: KnowledgeLevel) -> List[Persona]:
    """Get all personas with a specific knowledge level"""
    return [p for p in PERSONAS if p.knowledge_level == level]


def generate_conversation_starter(persona: Persona) -> str:
    """Generate a realistic first message from this persona"""
    return random.choice(persona.typical_questions)


def generate_follow_up(persona: Persona, context: str = "") -> str:
    """Generate a realistic follow-up question from this persona"""
    return random.choice(persona.follow_up_patterns)
