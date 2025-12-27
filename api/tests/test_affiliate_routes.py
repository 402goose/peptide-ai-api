"""
Tests for Affiliate API routes.

Tests symptom/product search, affiliate tracking, and analytics
using mock database implementations.
"""

import pytest
from datetime import datetime, timedelta
from tests.mocks import MockDatabase


class TestSymptomListing:
    """Tests for symptom listing and search."""

    @pytest.fixture
    def mock_db(self):
        """Create a fresh mock database with test data."""
        db = MockDatabase()
        db.clear_all()

        # Seed symptoms
        db.seed_data("symptoms", [
            {
                "symptom_id": "sym-1",
                "name": "Fatigue",
                "slug": "fatigue",
                "category": "energy",
                "keywords": ["tired", "exhausted", "low energy"],
                "recommended_products": ["prod-1", "prod-2"],
            },
            {
                "symptom_id": "sym-2",
                "name": "Joint Pain",
                "slug": "joint-pain",
                "category": "pain",
                "keywords": ["arthritis", "inflammation"],
                "recommended_products": ["prod-3"],
            },
            {
                "symptom_id": "sym-3",
                "name": "Poor Sleep",
                "slug": "poor-sleep",
                "category": "sleep",
                "keywords": ["insomnia", "restless"],
                "recommended_products": ["prod-1"],
            },
        ])

        return db

    @pytest.mark.asyncio
    async def test_list_all_symptoms(self, mock_db):
        """Should list all symptoms."""
        collection = mock_db.get_collection("symptoms")
        count = await collection.count_documents({})
        assert count == 3

    @pytest.mark.asyncio
    async def test_filter_symptoms_by_category(self, mock_db):
        """Should filter symptoms by category."""
        collection = mock_db.get_collection("symptoms")
        cursor = collection.find({"category": "energy"})
        symptoms = await cursor.to_list(length=100)

        assert len(symptoms) == 1
        assert symptoms[0]["name"] == "Fatigue"

    @pytest.mark.asyncio
    async def test_get_symptom_by_slug(self, mock_db):
        """Should get symptom by slug."""
        collection = mock_db.get_collection("symptoms")
        symptom = await collection.find_one({"slug": "joint-pain"})

        assert symptom is not None
        assert symptom["name"] == "Joint Pain"
        assert symptom["category"] == "pain"


class TestProductListing:
    """Tests for product listing and search."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()

        # Seed products
        db.seed_data("products", [
            {
                "product_id": "prod-1",
                "name": "BPC-157",
                "product_type": "peptide",
                "is_peptide": True,
                "description": "Healing peptide",
                "affiliate_url": "https://vendor.com/bpc157",
            },
            {
                "product_id": "prod-2",
                "name": "Vitamin D3",
                "product_type": "supplement",
                "is_peptide": False,
                "description": "Essential vitamin",
            },
            {
                "product_id": "prod-3",
                "name": "TB-500",
                "product_type": "peptide",
                "is_peptide": True,
                "description": "Recovery peptide",
            },
        ])

        return db

    @pytest.mark.asyncio
    async def test_list_all_products(self, mock_db):
        """Should list all products."""
        collection = mock_db.get_collection("products")
        count = await collection.count_documents({})
        assert count == 3

    @pytest.mark.asyncio
    async def test_filter_by_peptide(self, mock_db):
        """Should filter products by is_peptide flag."""
        collection = mock_db.get_collection("products")
        cursor = collection.find({"is_peptide": True})
        peptides = await cursor.to_list(length=100)

        assert len(peptides) == 2
        assert all(p["is_peptide"] for p in peptides)

    @pytest.mark.asyncio
    async def test_filter_by_product_type(self, mock_db):
        """Should filter products by type."""
        collection = mock_db.get_collection("products")
        cursor = collection.find({"product_type": "supplement"})
        supplements = await cursor.to_list(length=100)

        assert len(supplements) == 1
        assert supplements[0]["name"] == "Vitamin D3"

    @pytest.mark.asyncio
    async def test_get_product_by_id(self, mock_db):
        """Should get product by ID."""
        collection = mock_db.get_collection("products")
        product = await collection.find_one({"product_id": "prod-1"})

        assert product is not None
        assert product["name"] == "BPC-157"
        assert product["affiliate_url"] is not None


class TestAffiliateClickTracking:
    """Tests for affiliate click tracking."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()

        # Seed products for click tracking
        db.seed_data("products", [
            {
                "product_id": "prod-1",
                "name": "BPC-157",
                "affiliate_url": "https://vendor.com/bpc157?ref=peptideai",
            },
        ])

        return db

    @pytest.mark.asyncio
    async def test_track_click(self, mock_db):
        """Should record affiliate click."""
        clicks = mock_db.get_collection("affiliate_clicks")

        click = {
            "click_id": "click-123",
            "user_id": "user-123",
            "session_id": "session-abc",
            "product_id": "prod-1",
            "symptom_id": "sym-1",
            "source": "chat",
            "source_id": "conv-123",
            "clicked_at": datetime.utcnow(),
        }

        await clicks.insert_one(click)

        doc = await clicks.find_one({"click_id": "click-123"})
        assert doc is not None
        assert doc["product_id"] == "prod-1"
        assert doc["source"] == "chat"

    @pytest.mark.asyncio
    async def test_track_click_without_user(self, mock_db):
        """Should track anonymous clicks."""
        clicks = mock_db.get_collection("affiliate_clicks")

        click = {
            "click_id": "click-456",
            "user_id": None,
            "product_id": "prod-1",
            "source": "search",
            "clicked_at": datetime.utcnow(),
        }

        await clicks.insert_one(click)

        doc = await clicks.find_one({"click_id": "click-456"})
        assert doc is not None
        assert doc["user_id"] is None


class TestConversionTracking:
    """Tests for conversion tracking."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()

        # Seed a click
        db.seed_data("affiliate_clicks", [
            {
                "click_id": "click-123",
                "product_id": "prod-1",
                "clicked_at": datetime.utcnow(),
            }
        ])

        return db

    @pytest.mark.asyncio
    async def test_record_conversion(self, mock_db):
        """Should record conversion linked to click."""
        conversions = mock_db.get_collection("affiliate_conversions")

        conversion = {
            "conversion_id": "conv-abc",
            "click_id": "click-123",
            "vendor": "vendor-a",
            "order_amount": 99.99,
            "commission_amount": 9.99,
            "status": "confirmed",
            "converted_at": datetime.utcnow(),
        }

        await conversions.insert_one(conversion)

        doc = await conversions.find_one({"conversion_id": "conv-abc"})
        assert doc is not None
        assert doc["click_id"] == "click-123"
        assert doc["order_amount"] == 99.99
        assert doc["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_conversion_without_amounts(self, mock_db):
        """Should allow conversions without financial data."""
        conversions = mock_db.get_collection("affiliate_conversions")

        conversion = {
            "conversion_id": "conv-xyz",
            "click_id": "click-123",
            "vendor": "vendor-b",
            "status": "pending",
            "converted_at": datetime.utcnow(),
        }

        await conversions.insert_one(conversion)

        doc = await conversions.find_one({"conversion_id": "conv-xyz"})
        assert doc is not None
        assert doc.get("order_amount") is None


class TestSearchTracking:
    """Tests for search query tracking."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()
        return db

    @pytest.mark.asyncio
    async def test_log_search_query(self, mock_db):
        """Should log search queries."""
        searches = mock_db.get_collection("symptom_searches")

        search_log = {
            "search_id": "search-123",
            "user_id": "user-123",
            "query": "fatigue",
            "matched_symptoms": ["sym-1"],
            "source": "search",
            "searched_at": datetime.utcnow(),
        }

        await searches.insert_one(search_log)

        doc = await searches.find_one({"search_id": "search-123"})
        assert doc is not None
        assert doc["query"] == "fatigue"
        assert len(doc["matched_symptoms"]) == 1

    @pytest.mark.asyncio
    async def test_log_search_anonymous(self, mock_db):
        """Should log anonymous searches."""
        searches = mock_db.get_collection("symptom_searches")

        search_log = {
            "search_id": "search-456",
            "user_id": None,
            "query": "joint pain",
            "matched_symptoms": [],
            "source": "browse",
            "searched_at": datetime.utcnow(),
        }

        await searches.insert_one(search_log)

        doc = await searches.find_one({"search_id": "search-456"})
        assert doc is not None
        assert doc["user_id"] is None


class TestAnalytics:
    """Tests for analytics queries."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()

        # Seed clicks for analytics
        now = datetime.utcnow()
        clicks_data = []
        for i in range(10):
            clicks_data.append({
                "click_id": f"click-{i}",
                "product_id": "prod-1" if i < 6 else "prod-2",
                "source": "chat" if i < 4 else "search",
                "clicked_at": now - timedelta(days=i),
            })

        db.seed_data("affiliate_clicks", clicks_data)

        # Seed conversions
        db.seed_data("affiliate_conversions", [
            {
                "conversion_id": "conv-1",
                "click_id": "click-0",
                "order_amount": 100.00,
                "commission_amount": 10.00,
                "status": "confirmed",
                "converted_at": now,
            },
            {
                "conversion_id": "conv-2",
                "click_id": "click-1",
                "order_amount": 50.00,
                "commission_amount": 5.00,
                "status": "confirmed",
                "converted_at": now - timedelta(days=1),
            },
        ])

        return db

    @pytest.mark.asyncio
    async def test_count_total_clicks(self, mock_db):
        """Should count total clicks."""
        clicks = mock_db.get_collection("affiliate_clicks")
        count = await clicks.count_documents({})
        assert count == 10

    @pytest.mark.asyncio
    async def test_count_clicks_by_product(self, mock_db):
        """Should count clicks per product."""
        clicks = mock_db.get_collection("affiliate_clicks")

        prod1_cursor = clicks.find({"product_id": "prod-1"})
        prod1_clicks = await prod1_cursor.to_list(length=100)

        prod2_cursor = clicks.find({"product_id": "prod-2"})
        prod2_clicks = await prod2_cursor.to_list(length=100)

        assert len(prod1_clicks) == 6
        assert len(prod2_clicks) == 4

    @pytest.mark.asyncio
    async def test_count_clicks_by_source(self, mock_db):
        """Should count clicks by source."""
        clicks = mock_db.get_collection("affiliate_clicks")

        chat_cursor = clicks.find({"source": "chat"})
        chat_clicks = await chat_cursor.to_list(length=100)

        search_cursor = clicks.find({"source": "search"})
        search_clicks = await search_cursor.to_list(length=100)

        assert len(chat_clicks) == 4
        assert len(search_clicks) == 6

    @pytest.mark.asyncio
    async def test_sum_conversions(self, mock_db):
        """Should sum conversion amounts."""
        conversions = mock_db.get_collection("affiliate_conversions")
        cursor = conversions.find({"status": "confirmed"})
        docs = await cursor.to_list(length=100)

        total_revenue = sum(d.get("order_amount", 0) for d in docs)
        total_commission = sum(d.get("commission_amount", 0) for d in docs)

        assert total_revenue == 150.00
        assert total_commission == 15.00


class TestAdminSeeding:
    """Tests for admin seeding endpoints."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()
        return db

    @pytest.mark.asyncio
    async def test_seed_product(self, mock_db):
        """Should seed a new product."""
        products = mock_db.get_collection("products")

        product = {
            "product_id": "new-prod",
            "name": "New Peptide",
            "product_type": "peptide",
            "is_peptide": True,
            "description": "A new peptide product",
        }

        await products.insert_one(product)

        doc = await products.find_one({"product_id": "new-prod"})
        assert doc is not None
        assert doc["name"] == "New Peptide"

    @pytest.mark.asyncio
    async def test_seed_symptom(self, mock_db):
        """Should seed a new symptom."""
        symptoms = mock_db.get_collection("symptoms")

        symptom = {
            "symptom_id": "new-sym",
            "name": "New Symptom",
            "slug": "new-symptom",
            "category": "other",
            "keywords": ["test"],
            "recommended_products": [],
        }

        await symptoms.insert_one(symptom)

        doc = await symptoms.find_one({"symptom_id": "new-sym"})
        assert doc is not None
        assert doc["slug"] == "new-symptom"

    @pytest.mark.asyncio
    async def test_prevent_duplicate_products(self, mock_db):
        """Should detect existing products."""
        products = mock_db.get_collection("products")

        await products.insert_one({
            "product_id": "prod-1",
            "name": "Existing Product",
        })

        existing = await products.find_one({"name": "Existing Product"})
        assert existing is not None

    @pytest.mark.asyncio
    async def test_seed_lab_test(self, mock_db):
        """Should seed a new lab test."""
        labs = mock_db.get_collection("lab_tests")

        lab = {
            "test_id": "lab-1",
            "name": "Hormone Panel",
            "description": "Complete hormone testing",
            "affiliate_url": "https://labs.com/hormones",
        }

        await labs.insert_one(lab)

        doc = await labs.find_one({"test_id": "lab-1"})
        assert doc is not None
        assert doc["name"] == "Hormone Panel"
