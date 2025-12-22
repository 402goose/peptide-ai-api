# Peptide AI - Development TODO

> Last Updated: 2025-12-20

## Legend
- [ ] Not started
- [~] In progress
- [x] Complete
- [!] Blocked

---

## Phase 0: Planning & Research

### Product Definition
- [x] Define core product vision
- [x] Identify target users
- [x] Define subscription tiers
- [x] Map business model (subscription + affiliate)
- [ ] Finalize corporate structure / jurisdiction
- [ ] Legal review of terms / disclaimers

### Market Research
- [x] Analyze competitor products (Examine, health chatbots)
- [x] Research peptide community landscape
- [x] Understand regulatory environment
- [x] Map peptide influencer ecosystem

### Technical Research
- [x] RAG vs fine-tuning decision (chose RAG)
- [x] Vector database selection (chose Weaviate)
- [x] Embedding strategy (hybrid PubMedBERT + OpenAI)
- [x] Data source identification
- [x] Chunking strategy research

---

## Phase 1: MVP Foundation

### Project Setup
- [x] Initialize git repository
- [x] Set up Python project structure
- [x] Create requirements.txt
- [x] Set up Docker Compose for local dev
- [x] Configure environment variables

### Data Ingestion - Core
- [x] Design data models (RawDocument, ProcessedChunk)
- [x] Design PubMed adapter
- [x] Implement PubMed adapter
- [ ] Test PubMed ingestion

### Data Ingestion - Extended
- [x] Design arXiv/bioRxiv adapter
- [ ] Implement arXiv adapter
- [ ] Implement bioRxiv adapter
- [x] Design ChinaXiv adapter (OAI-PMH)
- [ ] Implement ChinaXiv adapter
- [x] Design Reddit adapter
- [ ] Implement Reddit adapter
- [x] Design Firecrawl scraper
- [ ] Implement Firecrawl scraper

### Processing Pipeline
- [x] Design chunking strategy
- [ ] Implement PeptideChunker
- [x] Design enrichment (NER, FDA status)
- [ ] Implement PeptideEnricher
- [x] Design embedding strategy
- [ ] Implement PeptideEmbedder

### Vector Store
- [x] Design Weaviate schema
- [ ] Set up Weaviate Cloud instance
- [x] Implement WeaviateClient
- [ ] Test indexing and retrieval

### Prompt Engineering
- [x] Design query classification system
- [x] Design master system prompt
- [x] Design query-type specific prompts
- [x] Design disclaimer system
- [x] Design safety guardrails
- [x] Design prompt assembler
- [x] Implement all prompt modules
- [ ] Test prompt quality

### Response Generation
- [x] Design response generator architecture
- [x] Implement PeptideResponseGenerator (RAG pipeline)
- [x] Implement safety checks
- [ ] Test end-to-end generation

### API Layer
- [x] Set up FastAPI project
- [x] Implement /chat endpoint
- [x] Implement /search endpoint
- [x] Add rate limiting
- [x] Add basic auth (API key)

### Testing & Evaluation
- [ ] Create test dataset (50-100 queries)
- [ ] Implement evaluation framework
- [ ] Run quality evaluation
- [ ] Iterate on prompts based on results

---

## Phase 2: User Features

### Authentication
- [ ] Choose auth provider (Clerk/Auth0/Supabase)
- [ ] Implement user registration
- [ ] Implement login/logout
- [ ] Add user profile

### Journey Tracking
- [x] Design journey data model
- [x] Create journey logging API
- [ ] Build journey logging UI
- [x] Implement outcome tracking
- [ ] Add journey analytics

### Personalization
- [x] Implement user context builder
- [ ] Add journey history to retrieval
- [ ] Personalized recommendations
- [ ] Test personalization quality

### Conversation Memory
- [x] Implement conversation storage
- [ ] Add multi-turn context handling
- [ ] Test conversation continuity

---

## Phase 3: Monetization

### Subscriptions
- [ ] Choose billing provider (Stripe)
- [ ] Implement subscription plans
- [ ] Build upgrade/downgrade flow
- [ ] Add usage tracking

### Affiliate System
- [ ] Design affiliate tracking schema
- [ ] Build vendor directory
- [ ] Implement email-based attribution
- [ ] Set up server-side conversion API
- [ ] Test attribution accuracy

### Creator Program
- [ ] Define creator tiers
- [ ] Create creator onboarding flow
- [ ] Integrate with creator platform (JoinBrands?)
- [ ] Build creator dashboard

---

## Phase 4: Growth & Scale

### Mobile
- [ ] Decide PWA vs native
- [ ] Build mobile-responsive UI
- [ ] Implement push notifications

### Content
- [ ] Creator content integration
- [ ] UGC display on platform
- [ ] Content moderation system

### Analytics
- [ ] Set up analytics (Mixpanel/Amplitude)
- [ ] Build admin dashboard
- [ ] Track key metrics (engagement, conversion, retention)

### Infrastructure
- [ ] Migrate to self-hosted Weaviate (if needed)
- [ ] Set up observability (LangSmith + Datadog)
- [ ] Implement caching layer
- [ ] Load testing

---

## Ongoing

### Data Quality
- [ ] Regular ingestion job monitoring
- [ ] Data freshness checks
- [ ] Duplicate detection
- [ ] Quality audits

### Prompt Improvement
- [ ] Collect user feedback
- [ ] A/B test prompt variations
- [ ] Update based on failure modes

### Regulatory Monitoring
- [ ] Track FDA peptide status changes
- [ ] Monitor regulatory news
- [ ] Update disclaimers as needed

---

## Blockers & Dependencies

| Blocker | Status | Notes |
|---------|--------|-------|
| Legal entity setup | Not started | Need to decide jurisdiction |
| NCBI API key | Not started | Register for higher rate limits |
| Weaviate Cloud account | Not started | Need to sign up |
| OpenAI API key | Available | Check existing 402.cat keys |
| Firecrawl API key | Not started | Sign up for account |
| Reddit API credentials | Not started | Create Reddit app |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-12-20 | RAG over fine-tuning | Faster to build, updatable, less hallucination |
| 2024-12-20 | Weaviate for vector DB | Best hybrid search, self-hostable option |
| 2024-12-20 | Hybrid embeddings | PubMedBERT for domain, OpenAI for queries |
| 2024-12-20 | Research platform positioning | Avoids medical device / FDA classification |
| 2024-12-20 | Exclude EU market | EMA too strict for peptide guidance |
| 2024-12-20 | Partner for creator platform | Don't build what exists (JoinBrands, etc.) |

---

## Notes

### Next Session Priorities
1. Test PubMed ingestion - run first data pull
2. Set up Weaviate Cloud - or test locally with Docker
3. Implement document chunker
4. Test end-to-end chat with real data

### Questions to Answer
- Mobile: PWA vs native?
- Auth: Clerk vs Auth0 vs Supabase?
- Billing: Stripe vs Paddle?
- Analytics: Mixpanel vs Amplitude vs PostHog?

### Completed This Session (2025-12-20)
**API Layer:**
- FastAPI application structure (main.py, deps.py)
- Authentication middleware with API keys
- Rate limiting middleware with tier support
- Chat endpoints with conversation history
- Search endpoints with Weaviate integration
- Journey management REST API (full CRUD + logging)

**Data Models:**
- User journey data models (documents.py)
- Journey service with full CRUD and logging (journey_service.py)

**Data Ingestion:**
- PubMed adapter with Entrez API (sources/pubmed.py)
- Base adapter interface (sources/base.py)

**Vector Storage:**
- Weaviate client with hybrid search (storage/weaviate_client.py)
- Schema for chunks and outcomes collections

**RAG Pipeline:**
- Query classifier with type/risk detection (llm/query_classifier.py)
- Full RAG pipeline with context retrieval (llm/rag_pipeline.py)
- Safety filtering and disclaimer injection

**Infrastructure:**
- Docker Compose with MongoDB, Weaviate, Redis
- Dockerfile for API container
- Environment variables template (.env.example)
- requirements.txt with all dependencies
