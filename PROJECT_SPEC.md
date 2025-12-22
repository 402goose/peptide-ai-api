# Peptide AI Platform - Project Specification

> **Status**: Planning & Research Phase
> **Last Updated**: 2024-12-20
> **Document Version**: 0.1.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision](#2-product-vision)
3. [Market Research](#3-market-research)
4. [Business Model](#4-business-model)
5. [Regulatory Considerations](#5-regulatory-considerations)
6. [Technical Architecture](#6-technical-architecture)
7. [RAG System Design](#7-rag-system-design)
8. [Data Ingestion Pipeline](#8-data-ingestion-pipeline)
9. [Prompt Engineering](#9-prompt-engineering)
10. [Data Moat Strategy](#10-data-moat-strategy)
11. [MVP Definition](#11-mvp-definition)
12. [Development Roadmap](#12-development-roadmap)
13. [Open Questions](#13-open-questions)
14. [Resources & References](#14-resources--references)

---

## 1. Executive Summary

### What We're Building

A specialized AI platform focused on peptide research and guidance, combining:
- **RAG-based AI** trained on peptide research, FDA data, and user experiences
- **Creator/influencer network** for distribution and content
- **Subscription model** with physical product fulfillment (peptide shipments)
- **Affiliate monetization** through vendor relationships
- **User journey tracking** that feeds back into AI improvements

### Key Differentiators

1. **Vertical expertise**: Deep focus on peptides vs generic health AI
2. **Proprietary data moat**: User journey outcomes, Chinese research translation
3. **Integrated supply chain**: Manufacturer partnerships (non-US based)
4. **Creator-led growth**: TikTok/Instagram peptide journey influencers
5. **Feedback loop**: User data improves recommendations over time

### Target Users

- Biohackers and self-optimizers
- Athletes seeking recovery solutions
- People exploring peptides for specific health goals
- Content creators documenting peptide journeys

---

## 2. Product Vision

### Core Product Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONT END: AI + CONTENT                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Peptide AI     │  │  Creator        │  │  Journey        │ │
│  │  Research       │  │  Platform       │  │  Tracking       │ │
│  │  Assistant      │  │  Integration    │  │  App            │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────────┘ │
├───────────┴────────────────────┴───────────────────┴────────────┤
│                    MIDDLE: MEMBERSHIP                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Subscription tiers with physical product fulfillment    │   │
│  │  • Free: Basic AI access                                 │   │
│  │  • Pro ($99/mo): Full AI, unlimited logging              │   │
│  │  • Pro+Ship ($199/mo): Pro + 1 peptide/month            │   │
│  │  • Creator: Free Pro+Ship for content creators          │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    BACK END: SUPPLY CHAIN                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Manufacturer   │  │  China Direct   │  │  Affiliate      │ │
│  │  Partners       │  │  Sourcing       │  │  Vendors        │ │
│  │  (2 acquired)   │  │  (connection)   │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### User Journey Flow

1. **Discovery**: User finds platform via creator content or search
2. **Education**: AI helps them understand peptides for their goals
3. **Matching**: AI recommends peptides based on goals + research
4. **Sourcing**: Platform connects to vetted vendors (affiliate)
5. **Tracking**: User logs doses, symptoms, outcomes
6. **Optimization**: AI adjusts recommendations based on data
7. **Community**: User optionally shares journey (creator funnel)

---

## 3. Market Research

### Similar Products Analyzed

| Product | Model | Key Learning |
|---------|-------|--------------|
| **Examine.com** | 100% subscription, no affiliates | Trust through independence, ExamineAI on proprietary data |
| **Ada Health / Babylon** | B2B + D2C health AI | CE certification needed for diagnostic claims |
| **Wholeness AI** | Supplement recommendations | 100+ years practitioner data |
| **Care/of, Persona** | Personalized supplements | Subscription box model works |
| **Athletic Greens** | Influencer-led growth | $115M raised via UGC strategy |

### Peptide Community Landscape

**Where users currently get info:**
- Reddit: r/peptides, r/PEDs, r/longevity, r/Biohackers
- Forums: Peptide Source Forum, AnabolicMinds
- YouTube: Biohacker influencers (Joe Rogan mentions, etc.)
- TikTok: Peptide journey content growing rapidly

**Pain points we solve:**
- Quality verification is difficult
- No centralized research synthesis
- Chinese research inaccessible to English speakers
- Fragmented dosing protocols
- No tracking of personal outcomes

### Market Size Indicators

- Healthcare chatbot market: $10.26B by 2034
- Peptide social media posts: Up 75% 2023→2024
- Peptide marketplace sales: Up 276% YoY
- Therapeutic peptide market: $42.05B (2022)

---

## 4. Business Model

### Revenue Streams

| Stream | Model | Estimated % of Revenue |
|--------|-------|------------------------|
| **Subscriptions** | $99-199/month recurring | 50-60% |
| **Affiliate** | 10-20% commission on vendor sales | 25-35% |
| **Creator partnerships** | Revenue share with creators | 10-15% |
| **Data licensing** | Future: anonymized insights | TBD |

### Subscription Tiers

| Tier | Price | Includes | COGS | Margin |
|------|-------|----------|------|--------|
| **Free** | $0 | Basic AI, 30-day log history | ~$0 | N/A |
| **Pro** | $99/mo | Full AI, unlimited logs, creator tools | ~$10 | 90% |
| **Pro+Ship** | $199/mo | Pro + 1 peptide/month (choose from menu) | ~$50-70 | 65-75% |
| **Creator** | $0 | Pro+Ship free if creating content | ~$60 | Offset by content value |

### Affiliate Strategy

**Separation approach for compliance:**
1. **Main platform** (peptide.ai): Research information only, no commerce
2. **Bridge layer** (peptide-sources.com): Vendor comparison, affiliate links
3. **Vendors**: Direct purchase with "research use" disclaimers

**Attribution:**
- Email sequences (not pixel retargeting due to health restrictions)
- Server-side conversion API
- First-party data only

### Creator Economics

| Tier | What They Get | What We Get |
|------|---------------|-------------|
| **Explorer** | Free product samples, AI access | Content rights, testimonials |
| **Creator** | Monthly free shipments, featured on platform | UGC for ads, social proof |
| **Ambassador** | Revenue share, exclusive peptides, MD consult access | Distribution, audience |

---

## 5. Regulatory Considerations

### Positioning

**Chosen approach**: Research Information Platform
- NOT a wellness tool (avoids FDA wellness device category)
- NOT a medical device (avoids FDA medical device regulation)
- Pure information/research synthesis with appropriate disclaimers

### FDA Status by Peptide Category

| Category | Examples | FDA Status |
|----------|----------|------------|
| **Approved** | Semaglutide, Tirzepatide, PT-141 | Can reference as approved treatments |
| **In Trials** | Some GLP-1 variants | Note trial status |
| **Not Approved** | BPC-157, TB-500, CJC-1295 | Must use "research only" framing |
| **Banned for Compounding** | BPC-157, Melanotan II | Cannot be legally compounded in US |

### Geographic Strategy

| Region | Status | Notes |
|--------|--------|-------|
| **US** | Primary market | "Research only" loophole, FDA gray zone |
| **UK** | Secondary | MHRA allows research possession |
| **EU** | EXCLUDED | EMA too strict |
| **Australia** | Wait and see | TGA new framework 2025 |
| **APAC** | Explore | Less enforcement generally |
| **LATAM** | Explore | Variable by country |

### Required Disclaimers

All responses involving non-FDA-approved peptides must include:
```
⚠️ **Regulatory Notice**: [Peptide] is not FDA-approved for human use.
The information provided is for educational purposes based on research studies.
These compounds are sold for research purposes only.
```

### Key Compliance Rules

1. Never make therapeutic claims for non-approved substances
2. Always note FDA status
3. Always recommend healthcare provider consultation
4. Never provide specific medical advice
5. Sourcing guidance handled separately from main AI responses

---

## 6. Technical Architecture

### High-Level Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                     │
│  Web App (Next.js) │ Mobile PWA │ API                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATION LAYER                               │
│  LangChain Agents + LlamaIndex Retrieval                                   │
│  Query routing, multi-step reasoning, citation generation                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RETRIEVAL LAYER                                   │
│  Hybrid Search (BM25 + Semantic) │ Metadata Filters │ Reranking           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VECTOR STORE                                      │
│  Weaviate (recommended)                                                    │
│  Collections: research_papers, user_journeys, vendor_data, fda_status     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA INGESTION                                    │
│  PubMed │ arXiv │ bioRxiv │ ChinaXiv │ Reddit │ Firecrawl │ User Data    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **AI Approach** | RAG (not fine-tuning) | Faster, cheaper, updatable, less hallucination |
| **Vector DB** | Weaviate | Best hybrid search, self-hostable, good filters |
| **Embeddings** | Hybrid (PubMedBERT + OpenAI) | Domain accuracy + query flexibility |
| **Chunking** | 512 tokens, section-aware | Optimal for research papers |
| **Retrieval** | Hybrid BM25 + semantic + rerank | 10% accuracy improvement |
| **Framework** | LlamaIndex + LangChain | LlamaIndex for retrieval, LangChain for orchestration |
| **LLM** | GPT-4o (primary), Claude (backup) | Quality + cost balance |
| **Creator Platform** | Partner with existing (JoinBrands/Collabstr) | Don't reinvent the wheel |

### Infrastructure (MVP)

| Component | Choice | Cost/month |
|-----------|--------|------------|
| Vector DB | Weaviate Cloud | ~$100-300 |
| LLM | OpenAI GPT-4o | ~$200-500 |
| Embeddings | OpenAI + PubMedBERT | ~$50-100 |
| Backend | Python FastAPI on Railway/Render | ~$50 |
| Ingestion | Celery + Redis | ~$30 |
| Translation | DeepL API | ~$25 |
| **Total MVP** | | **~$500-1000/mo** |

---

## 7. RAG System Design

### Architecture

```
User Query
    │
    ▼
┌─────────────────┐
│ Query Classifier │ → Determines type, entities, disclaimers needed
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query Rewriter  │ → Expands/optimizes for search
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Hybrid Retrieval │ → BM25 + Semantic + Filters
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Reranker        │ → Cross-encoder reranking
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Builder │ → Format with citations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Response Gen    │ → Query-type specific prompt
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Safety Check    │ → Validate, add disclaimers
└────────┬────────┘
         │
         ▼
Final Response
```

### Vector Database Schema

**Collections:**

1. **ResearchPapers**
   - chunk_id, document_id, source_type
   - content, section_type
   - peptides_mentioned[], fda_status
   - conditions_mentioned[]
   - title, authors[], publication_date
   - url, doi, citation
   - original_language
   - Vectors: pubmedbert, openai

2. **UserJourneys**
   - journey_id, user_hash (anonymized)
   - goal, peptide, protocol_summary
   - duration_weeks, outcome_summary
   - efficacy_rating (1-10)
   - side_effects[]
   - demographics (age_range, sex, activity_level)

3. **VendorIntelligence**
   - vendor_name, peptide
   - user_ratings, coa_verified
   - reported_issues

### Retrieval Strategy

1. **Hybrid Search**: BM25 + semantic with RRF fusion (alpha=0.5)
2. **Metadata Filters**: source_type, fda_status, date range, peptides
3. **Reranking**: Cross-encoder (ms-marco-MiniLM-L-6-v2)
4. **Top-K**: Over-retrieve (20), rerank to top 5

### Embedding Strategy

| Content Type | Model | Why |
|--------------|-------|-----|
| Research papers | PubMedBERT / S-PubMedBERT | Domain vocabulary |
| User queries | OpenAI text-embedding-3-large | Casual language handling |
| User journeys | OpenAI | Mix of technical/casual |

---

## 8. Data Ingestion Pipeline

### Data Sources

| Source | Method | Rate | Content |
|--------|--------|------|---------|
| **PubMed** | Entrez E-utilities API | 10/sec with key | Abstracts, metadata |
| **arXiv** | arxiv Python package | 0.5/sec | Full papers |
| **bioRxiv** | REST API | 1/sec | Preprints |
| **ChinaXiv** | OAI-PMH (Sickle) | 1/sec | Chinese preprints (translated) |
| **chinarxiv.org** | Firecrawl scraping | 1/sec | English translations |
| **Reddit** | PRAW | 1/sec | r/peptides, r/PEDs, etc. |
| **Web** | Firecrawl | 1/sec | Blogs, forums |
| **User Data** | Internal API | Realtime | Journey logs |

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INGESTION ORCHESTRATOR                            │
│                          (Celery + Redis Queue)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Scheduled (Daily) │ On-Demand │ Webhook (Realtime) │ Manual (Admin)       │
├─────────────────────────────────────────────────────────────────────────────┤
│                        SOURCE ADAPTERS                                      │
│  PubMed │ arXiv/bioRxiv │ ChinaXiv │ Reddit │ Firecrawl │ User Journeys   │
├─────────────────────────────────────────────────────────────────────────────┤
│                     PROCESSING PIPELINE                                     │
│  Extract → Clean → Chunk → Enrich → Embed → Store                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Chunking Strategy

| Content Type | Strategy | Chunk Size | Overlap |
|--------------|----------|------------|---------|
| Research papers | Section-aware semantic | 512 tokens | 50 tokens |
| User journeys | Keep whole | 1024 tokens | N/A |
| Forum posts | Paragraph-based | 256 tokens | 25 tokens |
| Web content | Recursive character | 512 tokens | 50 tokens |

### Enrichment

1. **Peptide NER**: Extract mentioned peptides, normalize to canonical names
2. **FDA Status**: Tag based on peptide and content mentions
3. **Condition Extraction**: Regex patterns for health conditions/goals
4. **Evidence Type**: Classify as RCT, clinical, animal, anecdotal

### Scheduled Jobs

| Job | Frequency | Description |
|-----|-----------|-------------|
| PubMed update | Daily | Fetch last 24h papers for tracked peptides |
| Reddit scan | Hourly | Scan target subreddits for new posts |
| Full web crawl | Weekly | Re-crawl target sites |
| Chinese research | Weekly | Harvest new ChinaXiv papers |

---

## 9. Prompt Engineering

### Prompt System Architecture

```
Query → Classifier → Rewriter → [Retrieval] → Context Builder → Response Generator → Safety Check → Response
```

### Query Types & Prompts

| Type | Trigger Patterns | Focus |
|------|------------------|-------|
| **research** | "study", "evidence", "trial" | Scientific evidence, citations |
| **protocol** | "how to", "dosage", "dose" | Practical usage info |
| **experience** | "anyone tried", "results" | User reports |
| **comparison** | "vs", "compared to" | Side-by-side analysis |
| **mechanism** | "how does it work" | Biological explanation |
| **safety** | "side effects", "safe" | Risks, contraindications |
| **sourcing** | "where to buy" | Redirect to vendor system |

### Master System Prompt (Summary)

**Core Principles:**
1. Accuracy first - only cite provided sources
2. Citation required - every claim needs [1], [2], etc.
3. FDA transparency - always note regulatory status
4. Evidence hierarchy - RCTs > clinical > animal > anecdotal
5. No medical advice - recommend healthcare providers
6. Honest uncertainty - don't overstate confidence

**Response Format:**
1. Direct answer
2. Evidence summary with citations
3. Practical context
4. Limitations/caveats
5. Required disclaimers

### Disclaimer System

| Trigger | Disclaimer |
|---------|------------|
| Non-FDA-approved peptide | Regulatory notice + research only |
| FDA-approved peptide | Note approved indications |
| Dosing discussion | Dosing disclaimer |
| User experiences | Anecdotal disclaimer |
| Sourcing query | Research use disclaimer |

### Safety Guardrails

**Blocked topics:**
- Self-harm indicators
- Illegal distribution
- Pediatric use
- Pregnancy/breastfeeding
- Replacing prescribed medications

**Response safety check:**
1. Dangerous advice detection
2. Overconfidence check
3. Missing disclaimer detection
4. Citation verification

---

## 10. Data Moat Strategy

### Proprietary Data Assets

| Asset | Description | Defensibility |
|-------|-------------|---------------|
| **User Journey Data** | Goal→Peptide→Outcome mappings at scale | Irreplicable once accumulated |
| **Creator Content Graph** | Licensed journey content, engagement patterns | Exclusive partnerships |
| **Chinese Research Translation** | Curated, translated Chinese papers | Curation + translation effort |
| **Vendor Quality Signals** | COA verification, user ratings | Community-generated |
| **Protocol Efficacy Data** | What dosing actually worked | Longitudinal collection |

### Flywheel Effect

```
Better AI → More Users → More Journey Data → Better Recommendations
    ↑                                              │
    └──────────────────────────────────────────────┘
```

### Competitive Moats

1. **Network effects**: More users = more data = better AI = more users
2. **Switching costs**: Journey history, personalized recommendations
3. **Content moat**: Exclusive creator relationships
4. **Data moat**: Proprietary outcome data competitors can't replicate

---

## 11. MVP Definition

### Phase 1: MVP (4-6 weeks)

**Data:**
- [ ] PubMed papers on top 20 peptides (~10k papers)
- [ ] Basic FDA status database (manual curation)
- [ ] No user journey data yet (cold start)

**Features:**
- [ ] Basic Q&A with citations
- [ ] FDA status lookup
- [ ] Peptide → condition matching
- [ ] Static disclaimers

**Infrastructure:**
- [ ] Weaviate Cloud
- [ ] Single OpenAI embedding model
- [ ] Basic FastAPI backend
- [ ] No auth yet

**Not Included:**
- User accounts/auth
- Journey tracking
- Creator portal
- Subscription billing
- Physical product fulfillment

### Phase 2: Core Platform (2-3 months)

**Data:**
- [ ] Full PubMed/arXiv/bioRxiv ingestion
- [ ] Chinese research pipeline (ChinaXiv)
- [ ] Reddit/forum scraping
- [ ] User journey collection

**Features:**
- [ ] User accounts (Clerk/Auth0)
- [ ] Journey tracking app
- [ ] Personalized recommendations
- [ ] Smart disclaimers based on FDA status
- [ ] Conversation memory

**Infrastructure:**
- [ ] Hybrid embeddings (PubMedBERT + OpenAI)
- [ ] Scheduled ingestion jobs
- [ ] Basic analytics

### Phase 3: Full Platform (3-6 months)

**Data:**
- [ ] Vendor intelligence database
- [ ] Creator content integration
- [ ] Full Chinese research translation

**Features:**
- [ ] Creator portal integration
- [ ] Subscription billing (Stripe)
- [ ] Affiliate tracking system
- [ ] Outcome predictions based on user data

**Infrastructure:**
- [ ] Self-hosted Weaviate
- [ ] Full observability stack
- [ ] A/B testing framework

### Phase 4: Scale & Optimize (6+ months)

- [ ] Physical product fulfillment integration
- [ ] International expansion
- [ ] Mobile app
- [ ] API for partners
- [ ] Advanced analytics dashboard

---

## 12. Development Roadmap

### Week 1-2: Foundation

- [ ] Set up project repository and structure
- [ ] Configure Weaviate Cloud instance
- [ ] Implement basic PubMed adapter
- [ ] Create initial peptide terms list
- [ ] Basic chunking and embedding pipeline

### Week 3-4: Core RAG

- [ ] Implement query classification
- [ ] Build hybrid search retrieval
- [ ] Create response generation prompts
- [ ] Add citation system
- [ ] Implement basic safety checks

### Week 5-6: API & Frontend

- [ ] FastAPI endpoints
- [ ] Basic web UI (can be simple)
- [ ] Test with real queries
- [ ] Iterate on prompt quality
- [ ] Deploy MVP

### Week 7-10: Expand Data

- [ ] Add arXiv/bioRxiv adapters
- [ ] Implement ChinaXiv harvester
- [ ] Add Reddit scraping
- [ ] Build scheduled job system
- [ ] Add user authentication

### Week 11-14: User Features

- [ ] Journey tracking data model
- [ ] Logging UI
- [ ] Personalization system
- [ ] Subscription integration
- [ ] Creator onboarding flow

### Week 15+: Growth Features

- [ ] Affiliate tracking
- [ ] Vendor directory
- [ ] Creator platform integration
- [ ] Analytics dashboard
- [ ] Physical fulfillment (if ready)

---

## 13. Open Questions

### Business

- [ ] What's the exact corporate structure for regulatory optimization?
- [ ] Which specific jurisdiction for company domicile?
- [ ] Terms of service / disclaimer language - needs legal review
- [ ] Insurance / liability considerations?

### Product

- [ ] Mobile app vs PWA for journey tracking?
- [ ] How explicit on sourcing guidance? (retargeting vs in-app)
- [ ] Creator content licensing terms?
- [ ] Minimum viable creator program?

### Technical

- [ ] Self-host Weaviate vs cloud for data privacy?
- [ ] CNKI/Wanfang API access - worth pursuing?
- [ ] How to handle peptide quality verification?
- [ ] User data anonymization standards?

### Go-to-Market

- [ ] First target creator partnerships?
- [ ] Beta user acquisition strategy?
- [ ] Pricing validation approach?

---

## 14. Resources & References

### Key Research Sources

- [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25497/)
- [arXiv API](https://info.arxiv.org/help/api/index.html)
- [bioRxiv API](https://api.biorxiv.org/)
- [ChinaXiv OAI-PMH](http://www.chinaxiv.org/oai/OAIHandler)
- [chinarxiv.org](https://chinarxiv.org/) - English translations

### Tools & Libraries

- [paperscraper](https://github.com/jannisborn/paperscraper) - Multi-source paper scraping
- [Sickle](https://sickle.readthedocs.io/) - OAI-PMH harvesting
- [PRAW](https://praw.readthedocs.io/) - Reddit API
- [Firecrawl](https://docs.firecrawl.dev/) - Web scraping
- [Weaviate](https://weaviate.io/developers/weaviate) - Vector database
- [LlamaIndex](https://docs.llamaindex.ai/) - RAG framework
- [LangChain](https://python.langchain.com/) - LLM orchestration

### Peptide Databases

- [Peptipedia v2.0](https://academic.oup.com/database/article/doi/10.1093/database/baae113/7887558)
- [Antimicrobial Peptide Database](https://aps.unmc.edu/)
- [PeptideAtlas](https://peptideatlas.org/)

### Regulatory References

- [FDA AI Medical Device Guidance (Jan 2025)](https://www.aha.org/news/headline/2025-01-07-fda-issues-draft-guidance-marketing-submissions-ai-enabled-medical-devices)
- [FTC Health Products Compliance](https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance)
- [Peptide Compounding Status 2025](https://www.frierlevitt.com/articles/regulatory-status-of-peptide-compounding-in-2025/)

### Competitor/Inspiration

- [Examine.com](https://examine.com/) - Research-based supplement info
- [Perplexity AI](https://perplexity.ai/) - Citation-first AI search UX
- [PaperQA](https://arxiv.org/abs/2312.07559) - Research paper QA system

---

## Appendix A: Peptide Reference List

### Tracked Peptides by Category

**Healing/Recovery:**
- BPC-157, TB-500 (Thymosin Beta-4), GHK-Cu, Pentadecapeptide

**Growth Hormone:**
- CJC-1295, Ipamorelin, Sermorelin, Tesamorelin, GHRP-2, GHRP-6, MK-677, Hexarelin

**Weight Loss:**
- Semaglutide, Tirzepatide, Liraglutide, AOD-9604, Tesofensine

**Sexual Health:**
- PT-141 (Bremelanotide), Melanotan II, Kisspeptin

**Cognitive:**
- Semax, Selank, Dihexa, P21, Cerebrolysin

**Longevity:**
- Epithalon, FOXO4-DRI, GDF-11, NAD+/NMN/NR, Thymalin

**Immune:**
- Thymosin Alpha-1, LL-37

---

## Appendix B: File Structure

```
peptide-ai/
├── PROJECT_SPEC.md              # This document
├── config/
│   ├── settings.py              # Environment config
│   └── peptide_terms.py         # Canonical peptide list
├── sources/
│   ├── base.py                  # Abstract source adapter
│   ├── pubmed.py                # PubMed/Entrez adapter
│   ├── arxiv_biorxiv.py         # arXiv + bioRxiv adapter
│   ├── chinaxiv.py              # ChinaXiv OAI-PMH adapter
│   ├── reddit.py                # Reddit/forum scraper
│   ├── firecrawl_scraper.py     # Generic web scraper
│   └── user_journeys.py         # User data processor
├── processing/
│   ├── chunker.py               # Semantic chunking
│   ├── enricher.py              # NER, FDA status, metadata
│   ├── embedder.py              # Embedding generation
│   └── deduplicator.py          # Near-duplicate detection
├── storage/
│   ├── weaviate_client.py       # Vector store operations
│   └── cache.py                 # Redis caching
├── prompts/
│   ├── system.py                # Master system prompt
│   ├── classification.py        # Query classifier
│   ├── query_types.py           # Type-specific prompts
│   ├── disclaimers.py           # Disclaimer templates
│   ├── personalization.py       # User context prompts
│   ├── conversation.py          # Multi-turn handling
│   ├── safety.py                # Guardrails
│   ├── assembler.py             # Prompt assembly
│   └── evaluation.py            # Quality evaluation
├── llm/
│   └── generator.py             # Response generation
├── tasks/
│   ├── celery_app.py            # Celery configuration
│   └── ingestion_tasks.py       # Async task definitions
├── api/
│   └── main.py                  # FastAPI endpoints
├── models/
│   └── documents.py             # Pydantic models
├── tests/
├── requirements.txt
└── docker-compose.yml
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2024-12-20 | Initial comprehensive spec from research session |

---

*This is a living document. Update as decisions are made and implementation progresses.*
