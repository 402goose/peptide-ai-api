"""
Peptide AI - Search Endpoints

Direct search interface for the knowledge base.
"""

from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from api.deps import get_database, get_settings, get_weaviate
from api.middleware.auth import get_current_user

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SearchType(str, Enum):
    """Types of search queries"""
    SEMANTIC = "semantic"  # Vector similarity search
    KEYWORD = "keyword"  # BM25 keyword search
    HYBRID = "hybrid"  # Combined (default)


class SourceFilter(str, Enum):
    """Filter by source type"""
    ALL = "all"
    RESEARCH = "research"  # PubMed, arXiv, bioRxiv
    USER_JOURNEYS = "user_journeys"
    REDDIT = "reddit"
    CHINAXIV = "chinaxiv"


class SearchRequest(BaseModel):
    """Search request body"""
    query: str = Field(..., min_length=1, max_length=1000)
    search_type: SearchType = SearchType.HYBRID
    source_filter: SourceFilter = SourceFilter.ALL
    peptide_filter: Optional[List[str]] = None  # Filter to specific peptides
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_metadata: bool = True


class SearchResult(BaseModel):
    """A single search result"""
    chunk_id: str
    content: str
    score: float
    source_type: str
    title: str
    url: Optional[str] = None
    citation: Optional[str] = None
    publication_date: Optional[datetime] = None
    peptides_mentioned: List[str] = []
    fda_status: Optional[str] = None
    highlight: Optional[str] = None  # Snippet with search terms highlighted


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    total_results: int
    results: List[SearchResult]
    search_type: str
    took_ms: int
    filters_applied: dict


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@router.post("/search", response_model=SearchResponse)
async def search(
    request: Request,
    body: SearchRequest,
    user: dict = Depends(get_current_user)
):
    """
    Search the peptide knowledge base

    Supports:
    - Semantic search (vector similarity)
    - Keyword search (BM25)
    - Hybrid search (combined - recommended)
    - Filtering by source type and peptides
    """
    start_time = datetime.utcnow()

    # TODO: Implement actual Weaviate search
    # For now, return placeholder results

    results = await _perform_search(
        query=body.query,
        search_type=body.search_type,
        source_filter=body.source_filter,
        peptide_filter=body.peptide_filter,
        limit=body.limit,
        offset=body.offset
    )

    elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    return SearchResponse(
        query=body.query,
        total_results=len(results),  # TODO: Get actual total from Weaviate
        results=results,
        search_type=body.search_type.value,
        took_ms=elapsed_ms,
        filters_applied={
            "source": body.source_filter.value,
            "peptides": body.peptide_filter
        }
    )


@router.get("/search/peptides")
async def search_peptides(
    q: str = Query(..., min_length=1, description="Peptide name query"),
    limit: int = Query(default=10, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    """
    Search/autocomplete for peptide names

    Used for:
    - Autocomplete in search UI
    - Peptide selection in journey creation
    """
    db = get_database()

    # Search in peptide stats collection (has all known peptides)
    cursor = db.peptide_stats.find(
        {"peptide": {"$regex": f"^{q}", "$options": "i"}},
        {"peptide": 1, "total_journeys": 1, "avg_efficacy_rating": 1}
    ).limit(limit)

    results = []
    async for doc in cursor:
        results.append({
            "name": doc["peptide"],
            "journey_count": doc.get("total_journeys", 0),
            "avg_rating": doc.get("avg_efficacy_rating")
        })

    # Also check static peptide list for ones without journeys
    # TODO: Load from peptide reference data

    return {"results": results}


@router.get("/search/similar/{chunk_id}")
async def find_similar(
    chunk_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    user: dict = Depends(get_current_user)
):
    """
    Find documents similar to a given chunk

    Useful for "related research" features.
    """
    # TODO: Implement vector similarity search in Weaviate
    return {
        "chunk_id": chunk_id,
        "similar": []  # Placeholder
    }


@router.get("/search/trending")
async def get_trending(
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=10, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    """
    Get trending peptides and topics

    Based on:
    - Recent search queries
    - New journey starts
    - Popular questions
    """
    db = get_database()

    # Get peptides with most new journeys in time period
    # TODO: Implement trending calculation

    return {
        "trending_peptides": [
            {"name": "BPC-157", "mentions": 150, "trend": "up"},
            {"name": "TB-500", "mentions": 120, "trend": "up"},
            {"name": "Semaglutide", "mentions": 200, "trend": "stable"},
        ],
        "trending_topics": [
            "healing protocols",
            "peptide stacks",
            "reconstitution"
        ],
        "period_days": days
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _perform_search(
    query: str,
    search_type: SearchType,
    source_filter: SourceFilter,
    peptide_filter: Optional[List[str]],
    limit: int,
    offset: int
) -> List[SearchResult]:
    """
    Perform search in Weaviate
    """
    weaviate = get_weaviate()

    # Determine alpha based on search type
    alpha = 0.5  # hybrid default
    if search_type == SearchType.SEMANTIC:
        alpha = 1.0
    elif search_type == SearchType.KEYWORD:
        alpha = 0.0

    # Perform search
    results = await weaviate.hybrid_search(
        query=query,
        limit=limit,
        alpha=alpha,
        source_filter=source_filter.value if source_filter != SourceFilter.ALL else None,
        peptide_filter=peptide_filter,
        include_outcomes=True
    )

    # Convert to SearchResult objects
    search_results = []
    for result in results:
        props = result.get("properties", {})
        search_results.append(SearchResult(
            chunk_id=props.get("chunk_id", ""),
            content=props.get("content", "")[:500],  # Truncate content
            score=result.get("score", 0),
            source_type=props.get("source_type", "unknown"),
            title=props.get("title", "Untitled")[:100],
            url=props.get("url"),
            citation=props.get("citation"),
            publication_date=props.get("publication_date") if isinstance(props.get("publication_date"), datetime) else (datetime.fromisoformat(str(props["publication_date"]).replace("Z", "+00:00")) if props.get("publication_date") else None),
            peptides_mentioned=props.get("peptides_mentioned", []),
            fda_status=props.get("fda_status"),
            highlight=None  # TODO: Add highlighting
        ))

    return search_results
