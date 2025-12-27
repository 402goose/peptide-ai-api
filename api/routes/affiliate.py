"""
Peptide AI - Affiliate & Holistic Products API

Endpoints for:
- Searching symptoms and getting product recommendations
- Tracking affiliate clicks and conversions
- Analytics on what symptoms/products users are interested in
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import hashlib
import re

from api.deps import get_database
from models.documents import (
    HolisticProduct, Symptom, LabTest, SymptomProductMapping,
    AffiliateClick, AffiliateConversion, SymptomSearch,
    ProductType, SymptomCategory
)

router = APIRouter(prefix="/affiliate", tags=["affiliate"])


# =============================================================================
# SYMPTOM & PRODUCT SEARCH
# =============================================================================

@router.get("/symptoms")
async def list_symptoms(
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    List all symptoms, optionally filtered by category or search query
    """
    query = {}

    if category:
        query["category"] = category

    if search:
        # Text search on name and keywords
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"keywords": {"$regex": search, "$options": "i"}}
        ]

    total = await db.symptoms.count_documents(query)
    cursor = db.symptoms.find(query).skip(offset).limit(limit).sort("name", 1)

    symptoms = []
    async for doc in cursor:
        doc.pop("_id", None)
        symptoms.append(doc)

    return {
        "symptoms": symptoms,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/symptoms/{symptom_slug}")
async def get_symptom(
    symptom_slug: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get a symptom by slug with its recommended products and labs
    """
    symptom = await db.symptoms.find_one({"slug": symptom_slug})
    if not symptom:
        raise HTTPException(status_code=404, detail="Symptom not found")

    symptom.pop("_id", None)

    # Get recommended products
    products = []
    if symptom.get("recommended_products"):
        cursor = db.products.find({"product_id": {"$in": symptom["recommended_products"]}})
        async for doc in cursor:
            doc.pop("_id", None)
            products.append(doc)

    # Get recommended lab tests
    labs = []
    if symptom.get("recommended_labs"):
        cursor = db.lab_tests.find({"test_id": {"$in": symptom["recommended_labs"]}})
        async for doc in cursor:
            doc.pop("_id", None)
            labs.append(doc)

    return {
        "symptom": symptom,
        "products": products,
        "labs": labs
    }


@router.get("/symptoms/category/{category}")
async def get_symptoms_by_category(
    category: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get all symptoms in a category
    """
    cursor = db.symptoms.find({"category": category}).sort("name", 1)

    symptoms = []
    async for doc in cursor:
        doc.pop("_id", None)
        symptoms.append(doc)

    return {
        "category": category,
        "symptoms": symptoms,
        "count": len(symptoms)
    }


@router.get("/categories")
async def list_categories(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    List all symptom categories with counts
    """
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]

    categories = []
    async for doc in db.symptoms.aggregate(pipeline):
        categories.append({
            "category": doc["_id"],
            "count": doc["count"]
        })

    return {"categories": categories}


@router.get("/products")
async def list_products(
    product_type: Optional[str] = None,
    is_peptide: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    List all products, optionally filtered
    """
    query = {}

    if product_type:
        query["product_type"] = product_type

    if is_peptide is not None:
        query["is_peptide"] = is_peptide

    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    total = await db.products.count_documents(query)
    cursor = db.products.find(query).skip(offset).limit(limit).sort("name", 1)

    products = []
    async for doc in cursor:
        doc.pop("_id", None)
        products.append(doc)

    return {
        "products": products,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get a product by ID with related symptoms
    """
    product = await db.products.find_one({"product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.pop("_id", None)

    # Get symptoms that recommend this product
    cursor = db.symptoms.find({"recommended_products": product_id})
    related_symptoms = []
    async for doc in cursor:
        doc.pop("_id", None)
        related_symptoms.append(doc)

    return {
        "product": product,
        "related_symptoms": related_symptoms
    }


@router.get("/search")
async def search_symptoms_and_products(
    q: str = Query(..., min_length=2),
    user_id: Optional[str] = None,
    source: str = "search",
    db: AsyncIOMotorDatabase = Depends(get_database),
    request: Request = None
) -> Dict[str, Any]:
    """
    Search for symptoms and products matching the query
    Also tracks the search for analytics
    """
    # Search symptoms
    symptom_cursor = db.symptoms.find({
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"keywords": {"$regex": q, "$options": "i"}}
        ]
    }).limit(10)

    symptoms = []
    symptom_ids = []
    async for doc in symptom_cursor:
        doc.pop("_id", None)
        symptoms.append(doc)
        symptom_ids.append(doc["symptom_id"])

    # Search products
    product_cursor = db.products.find({
        "name": {"$regex": q, "$options": "i"}
    }).limit(10)

    products = []
    async for doc in product_cursor:
        doc.pop("_id", None)
        products.append(doc)

    # Track the search
    search_log = SymptomSearch(
        user_id=user_id,
        query=q,
        matched_symptoms=symptom_ids,
        source=source
    )
    await db.symptom_searches.insert_one(search_log.model_dump())

    return {
        "query": q,
        "symptoms": symptoms,
        "products": products
    }


# =============================================================================
# AFFILIATE TRACKING
# =============================================================================

@router.post("/click")
async def track_click(
    product_id: str,
    symptom_id: Optional[str] = None,
    source: str = "search",
    source_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    request: Request = None
) -> Dict[str, Any]:
    """
    Track an affiliate link click
    Returns the affiliate URL to redirect to
    """
    # Verify product exists
    product = await db.products.find_one({"product_id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Create click record
    ip_hash = None
    user_agent = None
    if request:
        client_ip = request.client.host if request.client else None
        if client_ip:
            ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]
        user_agent = request.headers.get("user-agent")

    click = AffiliateClick(
        user_id=user_id,
        session_id=session_id,
        product_id=product_id,
        symptom_id=symptom_id,
        source=source,
        source_id=source_id,
        ip_hash=ip_hash,
        user_agent=user_agent
    )

    await db.affiliate_clicks.insert_one(click.model_dump())

    return {
        "click_id": click.click_id,
        "affiliate_url": product.get("affiliate_url"),
        "product_name": product.get("name")
    }


@router.post("/conversion")
async def record_conversion(
    click_id: str,
    vendor: str,
    order_amount: Optional[float] = None,
    commission_amount: Optional[float] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Record a conversion from an affiliate click
    (Called by webhook from affiliate network)
    """
    # Verify click exists
    click = await db.affiliate_clicks.find_one({"click_id": click_id})
    if not click:
        raise HTTPException(status_code=404, detail="Click not found")

    conversion = AffiliateConversion(
        click_id=click_id,
        vendor=vendor,
        order_amount=order_amount,
        commission_amount=commission_amount,
        status="confirmed"
    )

    await db.affiliate_conversions.insert_one(conversion.model_dump())

    return {
        "conversion_id": conversion.conversion_id,
        "status": "recorded"
    }


# =============================================================================
# ANALYTICS
# =============================================================================

@router.get("/analytics/popular-symptoms")
async def get_popular_symptoms(
    days: int = Query(30, le=365),
    limit: int = Query(20, le=50),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get most searched symptoms in the last N days
    """
    since = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {"searched_at": {"$gte": since}}},
        {"$unwind": "$matched_symptoms"},
        {"$group": {"_id": "$matched_symptoms", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]

    results = []
    async for doc in db.symptom_searches.aggregate(pipeline):
        # Get symptom details
        symptom = await db.symptoms.find_one({"symptom_id": doc["_id"]})
        if symptom:
            results.append({
                "symptom_id": doc["_id"],
                "name": symptom.get("name"),
                "category": symptom.get("category"),
                "search_count": doc["count"]
            })

    return {
        "period_days": days,
        "popular_symptoms": results
    }


@router.get("/analytics/popular-products")
async def get_popular_products(
    days: int = Query(30, le=365),
    limit: int = Query(20, le=50),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get most clicked products in the last N days
    """
    since = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {"clicked_at": {"$gte": since}}},
        {"$group": {"_id": "$product_id", "clicks": {"$sum": 1}}},
        {"$sort": {"clicks": -1}},
        {"$limit": limit}
    ]

    results = []
    async for doc in db.affiliate_clicks.aggregate(pipeline):
        # Get product details
        product = await db.products.find_one({"product_id": doc["_id"]})
        if product:
            results.append({
                "product_id": doc["_id"],
                "name": product.get("name"),
                "product_type": product.get("product_type"),
                "is_peptide": product.get("is_peptide"),
                "click_count": doc["clicks"]
            })

    return {
        "period_days": days,
        "popular_products": results
    }


@router.get("/analytics/search-queries")
async def get_search_queries(
    days: int = Query(30, le=365),
    limit: int = Query(50, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get most common search queries
    """
    since = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {"searched_at": {"$gte": since}}},
        {"$group": {"_id": {"$toLower": "$query"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]

    results = []
    async for doc in db.symptom_searches.aggregate(pipeline):
        results.append({
            "query": doc["_id"],
            "count": doc["count"]
        })

    return {
        "period_days": days,
        "search_queries": results
    }


@router.get("/analytics/source-breakdown")
async def get_source_breakdown(
    days: int = Query(30, le=365),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get breakdown of clicks by source (journey, chat, stacks, search)
    """
    since = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {"clicked_at": {"$gte": since}}},
        {"$group": {"_id": "$source", "clicks": {"$sum": 1}}},
        {"$sort": {"clicks": -1}}
    ]

    results = []
    async for doc in db.affiliate_clicks.aggregate(pipeline):
        results.append({
            "source": doc["_id"],
            "clicks": doc["clicks"]
        })

    return {
        "period_days": days,
        "source_breakdown": results
    }


@router.get("/analytics/conversions")
async def get_conversion_stats(
    days: int = Query(30, le=365),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Get conversion statistics
    """
    since = datetime.utcnow() - timedelta(days=days)

    # Total clicks
    total_clicks = await db.affiliate_clicks.count_documents({
        "clicked_at": {"$gte": since}
    })

    # Total conversions
    conversions_cursor = db.affiliate_conversions.find({
        "converted_at": {"$gte": since},
        "status": "confirmed"
    })

    total_conversions = 0
    total_revenue = 0
    total_commission = 0

    async for doc in conversions_cursor:
        total_conversions += 1
        if doc.get("order_amount"):
            total_revenue += doc["order_amount"]
        if doc.get("commission_amount"):
            total_commission += doc["commission_amount"]

    conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

    return {
        "period_days": days,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "conversion_rate": round(conversion_rate, 2),
        "total_revenue": round(total_revenue, 2),
        "total_commission": round(total_commission, 2)
    }


# =============================================================================
# ADMIN ENDPOINTS (for seeding data)
# =============================================================================

@router.post("/admin/seed-product")
async def seed_product(
    name: str,
    product_type: str,
    is_peptide: bool = False,
    description: Optional[str] = None,
    affiliate_url: Optional[str] = None,
    vendor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Add a product to the database
    """
    # Check if product already exists
    existing = await db.products.find_one({"name": name})
    if existing:
        return {"status": "exists", "product_id": existing["product_id"]}

    product = HolisticProduct(
        name=name,
        product_type=ProductType(product_type),
        is_peptide=is_peptide,
        description=description,
        affiliate_url=affiliate_url,
        vendor=vendor
    )

    await db.products.insert_one(product.model_dump())

    return {"status": "created", "product_id": product.product_id}


@router.post("/admin/seed-symptom")
async def seed_symptom(
    name: str,
    category: str,
    product_names: List[str] = [],
    lab_names: List[str] = [],
    keywords: List[str] = [],
    description: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Add a symptom with its product and lab recommendations
    """
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    # Check if symptom already exists
    existing = await db.symptoms.find_one({"slug": slug})
    if existing:
        return {"status": "exists", "symptom_id": existing["symptom_id"]}

    # Get product IDs
    product_ids = []
    for product_name in product_names:
        product = await db.products.find_one({"name": product_name})
        if product:
            product_ids.append(product["product_id"])

    # Get lab IDs
    lab_ids = []
    for lab_name in lab_names:
        lab = await db.lab_tests.find_one({"name": lab_name})
        if lab:
            lab_ids.append(lab["test_id"])

    symptom = Symptom(
        name=name,
        slug=slug,
        category=SymptomCategory(category),
        description=description,
        recommended_products=product_ids,
        recommended_labs=lab_ids,
        keywords=keywords
    )

    await db.symptoms.insert_one(symptom.model_dump())

    return {"status": "created", "symptom_id": symptom.symptom_id, "slug": slug}


@router.post("/admin/seed-lab")
async def seed_lab(
    name: str,
    description: Optional[str] = None,
    affiliate_url: Optional[str] = None,
    vendor: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """
    Add a lab test to the database
    """
    # Check if lab already exists
    existing = await db.lab_tests.find_one({"name": name})
    if existing:
        return {"status": "exists", "test_id": existing["test_id"]}

    lab = LabTest(
        name=name,
        description=description,
        affiliate_url=affiliate_url,
        vendor=vendor
    )

    await db.lab_tests.insert_one(lab.model_dump())

    return {"status": "created", "test_id": lab.test_id}
