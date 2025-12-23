# Peptide AI - Feedback Loop & Optimization System

## Overview

This system creates a continuous optimization loop that combines:
1. **Persona Testing** - AI agents simulate user behavior
2. **Real User Analytics** - Track actual user behavior
3. **A/B Testing** - Run controlled experiments
4. **Automated Optimization** - Auto-promote winning variants

```
┌─────────────────────────────────────────────────────────────────┐
│                     OPTIMIZATION LOOP                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Persona    │    │   Real User  │    │    A/B       │      │
│  │   Agents     │    │   Analytics  │    │   Testing    │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              FEEDBACK AGGREGATOR                         │   │
│  │  - Generates product briefs                              │   │
│  │  - Creates implementation tasks                          │   │
│  │  - Suggests prompt updates                               │   │
│  └───────────────────────────┬─────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              IMPLEMENT CHANGES                           │   │
│  │  - Update prompts                                        │   │
│  │  - Create experiments                                    │   │
│  │  - Deploy to % of traffic                                │   │
│  └───────────────────────────┬─────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MEASURE & DECIDE                            │   │
│  │  - Track experiment conversions                          │   │
│  │  - Calculate statistical significance                    │   │
│  │  - Auto-promote winners                                  │   │
│  └───────────────────────────┬─────────────────────────────┘   │
│                              │                                  │
│                              └──────────► LOOP                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Persona Testing (`testing/browser_agent.py`)

8 AI personas that simulate real user behavior:
- **Jake** (healing_beginner) - Shoulder injury, first-time researcher
- **Sarah** (weight_loss_mom) - Weight loss goals, safety-conscious
- **David** (skeptical_researcher) - Wants evidence, not hype
- **Marcus** (bodybuilder_advanced) - Experienced, wants stacks
- **Elena** (biohacker_longevity) - Cutting-edge longevity focus
- **Jennifer** (anxious_cautious) - Health anxiety, needs reassurance
- **Alex** (cognitive_optimizer) - Focus/memory enhancement
- **Mike** (budget_practical) - Cost-conscious, practical

**What they test:**
- Landing page UX (Playwright browser automation)
- Chat responses (API calls)
- Information quality
- Overall experience

**Output:** Satisfaction scores (target: 8.0/10), feedback

### 2. Real User Analytics (`api/routes/analytics.py`)

Tracks the SaaS funnel:
```
Page View → Sign Up → First Chat → Source View → Return Visit
```

**Key Metrics:**
- Active users (DAU/WAU/MAU)
- Chats per session
- Source click-through rate
- Return rate
- Feedback submissions

**Endpoints:**
- `POST /api/v1/analytics/track` - Track events
- `GET /api/v1/analytics/funnel` - Funnel analysis
- `GET /api/v1/analytics/metrics` - Key metrics dashboard
- `GET /api/v1/analytics/compare-to-personas` - Validate persona accuracy

### 3. A/B Testing (`api/routes/experiments.py`)

Run controlled experiments:
```python
# Example: Test new prompt structure
experiment = {
    "name": "detailed_dosing_v1",
    "hypothesis": "More detailed dosing increases engagement",
    "metric": "sources_clicked",
    "variants": [
        {"name": "control", "config": {"prompt_version": "v1"}},
        {"name": "treatment", "config": {"prompt_version": "v2_detailed"}}
    ],
    "traffic_percent": 10,  # Start with 10%
    "confidence_threshold": 0.95
}
```

**Workflow:**
1. Create experiment with variants
2. Users get assigned (deterministic hashing)
3. Track conversion events
4. Bayesian analysis calculates P(variant is best)
5. Auto-promote when confident (>95%)

**Endpoints:**
- `POST /api/v1/experiments` - Create experiment
- `GET /api/v1/experiments/{id}/results` - Get results + stats
- `POST /api/v1/experiments/auto-promote` - Check and promote winners

### 4. Feedback Aggregator (`testing/feedback_aggregator.py`)

Processes test results into actionable outputs:

**Generates per run:**
- `product_brief.md` - Executive summary, priorities
- `implementation_tasks.md` - Specific dev tasks
- `prompt_updates.md` - System prompt changes
- `PROGRESS.md` - Track satisfaction over time

## Typical Workflow

### Daily/Weekly Automation

```bash
# 1. Run persona tests
python testing/browser_agent.py

# 2. Generate product docs
python testing/feedback_aggregator.py

# 3. Check A/B experiment status
curl -X POST /api/v1/experiments/auto-promote

# 4. Review outputs in testing/runs/latest/
```

### Creating an Experiment

When you have an idea to test:

```python
# 1. Create experiment
POST /api/v1/experiments
{
    "name": "evidence_badges_v2",
    "description": "Test more prominent evidence badges",
    "hypothesis": "Clearer evidence display increases trust and engagement",
    "metric": "chat_engagement",  # or "sources_clicked", "return_rate"
    "variants": [
        {"name": "control", "weight": 1},
        {"name": "prominent_badges", "config": {"badge_size": "large"}, "weight": 1}
    ],
    "traffic_percent": 20,
    "min_sample_size": 200,
    "confidence_threshold": 0.95
}

# 2. In your code, check user's variant
GET /api/v1/experiments/{id}/assign?user_id=xxx
# Returns: {"variant": "prominent_badges", "in_experiment": true}

# 3. Track conversions
POST /api/v1/analytics/track
{
    "event_type": "experiment_conversion",
    "experiment_id": "xxx",
    "variant": "prominent_badges",
    "properties": {"metric": "chat_engagement"}
}

# 4. Check results
GET /api/v1/experiments/{id}/results
# Returns statistical analysis + recommendation
```

### Comparing Real vs Persona Data

Validate that persona testing reflects reality:

```bash
GET /api/v1/analytics/compare-to-personas
```

Returns:
```json
{
    "real_users": {
        "avg_chats_per_session": 3.2,
        "return_rate": 0.45,
        "active_users_30d": 1250
    },
    "persona_tests": {
        "avg_chats_per_session": 3.5,
        "return_rate": 1.0,
        "satisfaction": 7.0
    },
    "alignment": {
        "chats_diff": 0.3,  # Good alignment
        "return_diff": 0.55  # Personas more optimistic
    }
}
```

## File Structure

```
testing/
├── browser_agent.py          # Persona browser automation
├── automated_user_test.py    # API-only persona testing
├── feedback_aggregator.py    # Generate product docs
├── personas.json             # 8 persona definitions
├── browser_test_results.json # Latest browser test results
└── runs/
    ├── PROGRESS.md           # Satisfaction over time
    └── {run_id}/
        ├── product_brief.md
        ├── implementation_tasks.md
        ├── prompt_updates.md
        └── run_summary.json

api/routes/
├── analytics.py              # Event tracking & funnel
├── experiments.py            # A/B testing framework
└── feedback.py               # User feedback collection
```

## Key Metrics to Track

### Acquisition
- Landing page views
- Sign-up conversion rate
- Traffic sources

### Activation (First Value Moment)
- Time to first chat
- First chat completion rate
- First source click

### Engagement
- Chats per session
- Session duration
- Sources viewed per session
- Follow-up click rate

### Retention
- Day 1/7/30 return rates
- Time between sessions
- Churn indicators

### Satisfaction
- Persona satisfaction scores
- Real user feedback ratings
- NPS (if implemented)

## Success Criteria

**Persona Testing:**
- All 8 personas at 7.0+ satisfaction ✓
- Target: 8.0+ overall satisfaction

**Real User Metrics:**
- Sign-up → First Chat conversion > 60%
- Day 7 return rate > 30%
- Average 3+ chats per session

**A/B Testing:**
- Run 2-3 experiments per month
- 95% confidence before promoting
- Measure impact on key metrics

## Next Steps

1. **Deploy analytics tracking** to production frontend
2. **Create first experiment** based on persona feedback
3. **Set up weekly automation** (cron job for testing + promotion)
4. **Build analytics dashboard** in web app
5. **Add NPS tracking** for direct user satisfaction measurement
