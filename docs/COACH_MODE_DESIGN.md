# Coach Mode Design Document

## Overview

Transform Peptide AI from a "search engine" to a "responsible coach" that:
1. Detects user intent (researching vs ready to act)
2. Asks qualifying questions before giving practical advice
3. Subtly surfaces relevant features (Journey Tracker, Stack Builder)
4. Ensures users are prepared and informed

---

## 1. Intent Detection

### Signal Words for "Action Mode"
```
READY_TO_ACT_SIGNALS = [
    "I just got", "I have", "I bought", "arrived today",
    "ready to start", "how do I inject", "reconstitute",
    "what needle", "how much bac water", "first dose",
    "starting tomorrow", "my vials", "my peptides"
]

RESEARCH_MODE_SIGNALS = [
    "what is", "tell me about", "benefits of", "vs",
    "compare", "which is better", "should I try",
    "thinking about", "considering", "research on"
]
```

### Auto-Switch Logic
- If message contains READY_TO_ACT_SIGNALS → Switch to Coach/Action Mode
- If message contains peptide names + supplies (needles, bac water) → Coach Mode
- Default: Balanced Mode

---

## 2. Coach Mode System Prompt

```python
COACH_MODE_PROMPT = """
## COACH MODE - READY TO START

The user has indicated they have supplies and are ready to begin. Your role shifts from educator to PRACTICAL COACH.

### CRITICAL: ASK BEFORE ADVISING

Before giving dosing/injection advice, you MUST gather:

1. **What they have:**
   - "What size vial did you get? (mg per vial)"
   - "What concentration of bac water?"
   - "What size insulin syringes?"

2. **Their goals:**
   - "What are you hoping to achieve with [peptide]?"
   - "Any specific symptoms or conditions you're targeting?"

3. **Experience level:**
   - "Is this your first time with peptides/injections?"
   - "Have you done SubQ injections before?"

4. **Tracking plan:**
   - "How do you want to track your progress?"
   - "What metrics matter to you? (energy, sleep, pain levels, etc.)"

### RESPONSE APPROACH

1. **Acknowledge their readiness** - "Great, you've got your supplies ready!"
2. **Ask 1-2 qualifying questions** - Don't ask all at once
3. **Give SPECIFIC practical guidance** based on THEIR supplies
4. **Include safety checks** - Storage, sterile technique, first-dose precautions
5. **Suggest tracking** - Naturally mention Journey Tracker if relevant

### FEATURE AWARENESS

You know about these features and can suggest them naturally:

- **Journey Tracker**: For logging doses, tracking symptoms, seeing progress over time
  - Suggest when: User mentions wanting to track, has a timeline, or multiple peptides
  - Phrase: "Would you like to set this up in your Journey Tracker to log doses and track how you feel?"

- **Stack Builder**: For planning multi-peptide protocols, checking interactions
  - Suggest when: User mentions 2+ peptides, asks about combining, building a stack
  - Phrase: "I can add these to your Stack Builder to check for interactions and plan your protocol."

### SAFETY GATES

Before giving injection instructions, confirm:
- [ ] They understand this is for research purposes
- [ ] They know their vial concentration
- [ ] First-timers get extra guidance on sterile technique
- [ ] Flag concerning doses: "That's higher than typical starting doses - any reason for that?"

### RESPONSE FORMAT FOR COACH MODE

### 🎯 Let's Get You Started

[Acknowledge what they have]

**Quick questions first:**
- [1-2 specific questions based on what's missing]

---

### 💉 Your Protocol (once info gathered)

**Reconstitution:**
- Add X ml bac water to your [X]mg vial
- This gives you [X]mcg per 0.1ml (10 units on insulin syringe)

**Dosing:**
- **Dose:** [specific to their vial]
- **Frequency:** [specific recommendation]
- **Timing:** [when to inject]
- **Duration:** [how long to run]

**First Week:**
- Start with [lower dose] to assess tolerance
- Watch for: [specific sides for this peptide]
- Note how you feel each day

---

### 📊 Track Your Progress

[Natural suggestion for Journey Tracker if applicable]

---

### ⚠️ Safety Reminders
- Store reconstituted peptide in fridge (good for ~4 weeks)
- New needle each injection
- Rotate injection sites
"""
```

---

## 3. UI Components

### A. Contextual Feature Chips (in-message)

When AI mentions a feature, render as an interactive chip:

```tsx
// Component: FeatureChip
interface FeatureChipProps {
  feature: 'journey' | 'stack'
  peptides?: string[]
  action: string // "Track NAD+" or "Add to Stack"
}

// Renders as:
// [📊 Track NAD+ in Journey] [🧪 Add to Stack Builder]
```

**Placement:** Inline in the response where relevant, or at end of message.

**Styling:**
- Subtle, not shouty - muted background, small icon
- Hover reveals more context
- Click opens modal or navigates

---

### B. End-of-Response CTA Bar

After responses about specific peptides the user is starting:

```tsx
// Component: ResponseActions
<div className="response-actions">
  <span className="text-sm text-slate-500">Ready to track this?</span>
  <Button variant="ghost" size="sm">
    <Calendar className="h-4 w-4 mr-1" />
    Start Journey
  </Button>
  <Button variant="ghost" size="sm">
    <Beaker className="h-4 w-4 mr-1" />
    Add to Stack
  </Button>
</div>
```

**When to show:**
- User mentioned specific peptides they have
- User is in "action mode"
- Peptide not already in their active journeys

---

### C. Quick Action Cards

For practical requests, show interactive calculator cards:

```tsx
// Component: ReconstitutionCard
<Card className="my-4 p-4 border-blue-200 bg-blue-50">
  <h4 className="font-medium flex items-center gap-2">
    <Calculator className="h-4 w-4" />
    Reconstitution Calculator
  </h4>

  <div className="grid grid-cols-2 gap-3 mt-3">
    <div>
      <label>Vial size (mg)</label>
      <Input type="number" placeholder="5" />
    </div>
    <div>
      <label>Bac water (ml)</label>
      <Input type="number" placeholder="2" />
    </div>
  </div>

  <div className="mt-3 p-2 bg-white rounded">
    <p className="text-sm">
      <strong>Result:</strong> 250mcg per 0.1ml (10 units)
    </p>
  </div>
</Card>
```

**Trigger:** AI detects reconstitution question or "how much bac water"

---

### D. Safety Checklist (for first-timers)

```tsx
// Component: SafetyChecklist
<Card className="my-4 p-4 border-amber-200 bg-amber-50">
  <h4 className="font-medium flex items-center gap-2">
    <ShieldCheck className="h-4 w-4" />
    First Injection Checklist
  </h4>

  <div className="space-y-2 mt-3">
    <ChecklistItem checked={false}>
      Wash hands thoroughly
    </ChecklistItem>
    <ChecklistItem checked={false}>
      Clean vial top with alcohol
    </ChecklistItem>
    <ChecklistItem checked={false}>
      Draw correct amount (X units)
    </ChecklistItem>
    <ChecklistItem checked={false}>
      Clean injection site with alcohol
    </ChecklistItem>
    <ChecklistItem checked={false}>
      Pinch skin, insert at 45° angle
    </ChecklistItem>
    <ChecklistItem checked={false}>
      Log your dose
    </ChecklistItem>
  </div>

  <Button size="sm" className="mt-3">
    <Play className="h-4 w-4 mr-1" />
    Watch Tutorial Video
  </Button>
</Card>
```

---

### E. "Not Tracking Yet" Nudge

Subtle banner when peptides mentioned aren't in user's journeys:

```tsx
// Shows at top of chat when applicable
<div className="flex items-center gap-2 px-4 py-2 bg-slate-100 text-sm">
  <Info className="h-4 w-4 text-slate-500" />
  <span>You mentioned NAD+ and SR9009 - want to track these?</span>
  <Button variant="link" size="sm">Set up tracking →</Button>
  <Button variant="ghost" size="sm">Dismiss</Button>
</div>
```

---

## 4. Implementation Priority

### Phase 1: Core Coach Mode
1. Add intent detection to classify messages
2. Update system prompt with Coach Mode
3. Add qualifying question logic

### Phase 2: Subtle Feature Discovery
4. End-of-response CTA bar
5. "Not tracking yet" nudge
6. Feature chips in AI responses

### Phase 3: Interactive Tools
7. Reconstitution calculator card
8. Safety checklist component
9. Dose calculator

---

## 5. Data Flow

```
User Message
    ↓
Intent Detection (research vs action)
    ↓
Check User Context:
  - Active journeys
  - Stack builder items
  - Experience level (from onboarding)
    ↓
Select System Prompt Mode
    ↓
Generate Response with:
  - Contextual feature suggestions
  - Safety checks if action mode
  - Specific follow-up questions
    ↓
Frontend renders:
  - Message content
  - Feature chips
  - Action cards (if applicable)
  - CTA bar (if applicable)
```

---

## 6. Example Conversation Flow

**User:** "I just got some peptides NAD and SR9009. I have bac water and insulin needles"

**AI (Coach Mode):**

> ### 🎯 Great, You're Ready to Start!
>
> You've got NAD+ and SR9009 with your supplies ready. Let me help you get set up properly.
>
> **Quick questions:**
> 1. What size are your vials? (NAD+ usually comes in 100mg or 500mg, SR9009 varies)
> 2. Is this your first time doing SubQ injections?
>
> Once I know your vial sizes, I can give you exact reconstitution amounts and dosing.
>
> ---
>
> `[📊 Track NAD+ & SR9009]` `[🧪 Add to Stack Builder]`

**User:** "100mg NAD and 10mg SR9009. Yeah first time injecting"

**AI:**

> ### 💉 Your Personalized Protocol
>
> **NAD+ (100mg vial)**
> - Add **2ml** bac water → gives you **5mg per 0.1ml** (10 units)
> - Starting dose: 50mg (0.1ml / 10 units) every other day
>
> `[Calculator: Verify NAD+ Reconstitution]`
>
> **SR9009 (10mg vial)**
> - Add **1ml** bac water → gives you **1mg per 0.1ml** (10 units)
> - Dose: 5mg (0.5ml / 50 units) twice daily
>
> ---
>
> ### 📋 First Injection Checklist
> Since this is your first time, here's what to do:
>
> `[Interactive Checklist Component]`
>
> ---
>
> ### 📊 Track Your Journey
>
> Want me to set up tracking for these? I can remind you to log doses and help you track:
> - Energy levels
> - Sleep quality
> - Any side effects
>
> `[Start Journey Tracker]` `[Maybe Later]`
