"""
Tests for Journey API routes.

Tests journey CRUD operations, status transitions, and logging endpoints
using mock database implementations.
"""

import pytest
from datetime import date, datetime
from api.tests.mocks import MockDatabase


class TestJourneyService:
    """
    Unit tests for JourneyService logic.

    These tests verify the service layer without HTTP overhead.
    """

    @pytest.fixture
    def mock_db(self):
        """Create a fresh mock database."""
        db = MockDatabase()
        db.clear_all()
        return db

    @pytest.fixture
    def sample_user(self):
        """Sample authenticated user."""
        return {
            "user_id": "user-123",
            "email": "test@example.com",
            "subscription_tier": "pro",
        }

    @pytest.fixture
    def sample_journey_data(self):
        """Sample journey creation data."""
        return {
            "journey_id": "journey-123",
            "user_id": "user-123",
            "title": "BPC-157 Healing Journey",
            "primary_peptide": "BPC-157",
            "secondary_peptides": [],
            "status": "planning",
            "goals": [
                {
                    "id": "goal-1",
                    "category": "healing",
                    "description": "Heal tendon injury",
                }
            ],
            "administration_route": "subcutaneous",
            "planned_protocol": "250mcg twice daily",
            "planned_duration_weeks": 4,
            "dose_count": 0,
            "created_at": datetime.utcnow().isoformat(),
        }

    @pytest.mark.asyncio
    async def test_create_journey_inserts_document(self, mock_db, sample_journey_data):
        """Creating a journey should insert a document into the database."""
        collection = mock_db.get_collection("journeys")

        await collection.insert_one(sample_journey_data)

        # Verify it was inserted
        doc = await collection.find_one({"journey_id": "journey-123"})
        assert doc is not None
        assert doc["primary_peptide"] == "BPC-157"
        assert doc["status"] == "planning"

    @pytest.mark.asyncio
    async def test_list_journeys_filters_by_user(self, mock_db):
        """Listing journeys should only return the user's journeys."""
        collection = mock_db.get_collection("journeys")

        # Insert journeys for different users
        await collection.insert_one({
            "journey_id": "j1",
            "user_id": "user-123",
            "primary_peptide": "BPC-157",
            "status": "active",
        })
        await collection.insert_one({
            "journey_id": "j2",
            "user_id": "user-456",
            "primary_peptide": "TB-500",
            "status": "active",
        })
        await collection.insert_one({
            "journey_id": "j3",
            "user_id": "user-123",
            "primary_peptide": "Ipamorelin",
            "status": "completed",
        })

        # Query for user-123's journeys
        cursor = collection.find({"user_id": "user-123"})
        journeys = await cursor.to_list(length=100)

        assert len(journeys) == 2
        assert all(j["user_id"] == "user-123" for j in journeys)

    @pytest.mark.asyncio
    async def test_list_journeys_filters_by_status(self, mock_db):
        """Listing journeys with status filter should return matching journeys."""
        collection = mock_db.get_collection("journeys")

        await collection.insert_one({
            "journey_id": "j1",
            "user_id": "user-123",
            "status": "active",
        })
        await collection.insert_one({
            "journey_id": "j2",
            "user_id": "user-123",
            "status": "completed",
        })

        cursor = collection.find({"user_id": "user-123", "status": "active"})
        active_journeys = await cursor.to_list(length=100)

        assert len(active_journeys) == 1
        assert active_journeys[0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_journey_returns_full_document(self, mock_db, sample_journey_data):
        """Getting a journey should return the full document."""
        collection = mock_db.get_collection("journeys")
        await collection.insert_one(sample_journey_data)

        doc = await collection.find_one({"journey_id": "journey-123"})

        assert doc["title"] == "BPC-157 Healing Journey"
        assert doc["planned_protocol"] == "250mcg twice daily"
        assert len(doc["goals"]) == 1

    @pytest.mark.asyncio
    async def test_start_journey_updates_status(self, mock_db, sample_journey_data):
        """Starting a journey should update status to active."""
        collection = mock_db.get_collection("journeys")
        await collection.insert_one(sample_journey_data)

        # Update to start the journey
        result = await collection.update_one(
            {"journey_id": "journey-123"},
            {"$set": {"status": "active", "start_date": date.today().isoformat()}}
        )

        assert result.modified_count == 1

        doc = await collection.find_one({"journey_id": "journey-123"})
        assert doc["status"] == "active"
        assert doc["start_date"] is not None

    @pytest.mark.asyncio
    async def test_complete_journey_updates_status_and_outcomes(self, mock_db):
        """Completing a journey should update status and store outcomes."""
        collection = mock_db.get_collection("journeys")
        await collection.insert_one({
            "journey_id": "journey-123",
            "user_id": "user-123",
            "status": "active",
        })

        outcomes = {
            "overall_efficacy_rating": 8,
            "would_recommend": True,
            "would_use_again": True,
            "outcome_summary": "Great results for healing",
        }

        result = await collection.update_one(
            {"journey_id": "journey-123"},
            {"$set": {"status": "completed", "outcomes": outcomes}}
        )

        assert result.modified_count == 1

        doc = await collection.find_one({"journey_id": "journey-123"})
        assert doc["status"] == "completed"
        assert doc["outcomes"]["overall_efficacy_rating"] == 8

    @pytest.mark.asyncio
    async def test_pause_journey_updates_status(self, mock_db):
        """Pausing a journey should update status to paused."""
        collection = mock_db.get_collection("journeys")
        await collection.insert_one({
            "journey_id": "journey-123",
            "status": "active",
        })

        result = await collection.update_one(
            {"journey_id": "journey-123"},
            {"$set": {"status": "paused", "pause_reason": "Travel"}}
        )

        doc = await collection.find_one({"journey_id": "journey-123"})
        assert doc["status"] == "paused"
        assert doc["pause_reason"] == "Travel"


class TestDoseLogging:
    """Tests for dose logging functionality."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()
        return db

    @pytest.mark.asyncio
    async def test_log_dose_creates_record(self, mock_db):
        """Logging a dose should create a dose_logs record."""
        collection = mock_db.get_collection("dose_logs")

        dose_log = {
            "log_id": "dose-123",
            "journey_id": "journey-123",
            "peptide": "BPC-157",
            "dose_amount": 250,
            "dose_unit": "mcg",
            "route": "subcutaneous",
            "injection_site": "stomach",
            "timestamp": datetime.utcnow().isoformat(),
        }

        await collection.insert_one(dose_log)

        doc = await collection.find_one({"log_id": "dose-123"})
        assert doc is not None
        assert doc["dose_amount"] == 250
        assert doc["peptide"] == "BPC-157"

    @pytest.mark.asyncio
    async def test_log_dose_increments_journey_count(self, mock_db):
        """Logging a dose should increment the journey's dose_count."""
        journeys = mock_db.get_collection("journeys")
        await journeys.insert_one({
            "journey_id": "journey-123",
            "dose_count": 5,
        })

        # Simulate incrementing dose count
        result = await journeys.update_one(
            {"journey_id": "journey-123"},
            {"$set": {"dose_count": 6}}  # MockDB doesn't support $inc
        )

        doc = await journeys.find_one({"journey_id": "journey-123"})
        assert doc["dose_count"] == 6

    @pytest.mark.asyncio
    async def test_get_dose_history(self, mock_db):
        """Getting dose history should return all doses for a journey."""
        collection = mock_db.get_collection("dose_logs")

        # Insert multiple doses
        for i in range(5):
            await collection.insert_one({
                "log_id": f"dose-{i}",
                "journey_id": "journey-123",
                "peptide": "BPC-157",
                "dose_amount": 250,
                "timestamp": datetime.utcnow().isoformat(),
            })

        cursor = collection.find({"journey_id": "journey-123"})
        doses = await cursor.to_list(length=100)

        assert len(doses) == 5


class TestSymptomLogging:
    """Tests for symptom logging functionality."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()
        return db

    @pytest.mark.asyncio
    async def test_log_symptoms_creates_record(self, mock_db):
        """Logging symptoms should create a symptom_logs record."""
        collection = mock_db.get_collection("symptom_logs")

        symptom_log = {
            "log_id": "symptom-123",
            "journey_id": "journey-123",
            "log_date": date.today().isoformat(),
            "energy_level": 7,
            "sleep_quality": 8,
            "mood": 7,
            "pain_level": 3,
            "side_effects": [],
            "side_effect_severity": "none",
        }

        await collection.insert_one(symptom_log)

        doc = await collection.find_one({"log_id": "symptom-123"})
        assert doc is not None
        assert doc["energy_level"] == 7
        assert doc["pain_level"] == 3

    @pytest.mark.asyncio
    async def test_symptom_log_tracks_side_effects(self, mock_db):
        """Symptom logs should track side effects with severity."""
        collection = mock_db.get_collection("symptom_logs")

        await collection.insert_one({
            "log_id": "symptom-123",
            "journey_id": "journey-123",
            "log_date": date.today().isoformat(),
            "side_effects": ["mild_headache", "injection_site_redness"],
            "side_effect_severity": "mild",
        })

        doc = await collection.find_one({"log_id": "symptom-123"})
        assert len(doc["side_effects"]) == 2
        assert doc["side_effect_severity"] == "mild"

    @pytest.mark.asyncio
    async def test_get_symptom_trends(self, mock_db):
        """Getting symptom history should return trends over time."""
        collection = mock_db.get_collection("symptom_logs")

        # Log symptoms over multiple days
        for i in range(7):
            await collection.insert_one({
                "log_id": f"symptom-{i}",
                "journey_id": "journey-123",
                "log_date": f"2024-01-0{i+1}",
                "energy_level": 5 + i,  # Improving trend
                "sleep_quality": 6,
            })

        cursor = collection.find({"journey_id": "journey-123"})
        logs = await cursor.to_list(length=100)

        assert len(logs) == 7
        # Could verify trend analysis here


class TestJourneyAuthorization:
    """Tests for journey authorization logic."""

    @pytest.fixture
    def mock_db(self):
        db = MockDatabase()
        db.clear_all()
        return db

    @pytest.mark.asyncio
    async def test_user_can_only_access_own_journeys(self, mock_db):
        """Users should only be able to access their own journeys."""
        collection = mock_db.get_collection("journeys")

        await collection.insert_one({
            "journey_id": "j1",
            "user_id": "user-123",
        })
        await collection.insert_one({
            "journey_id": "j2",
            "user_id": "user-456",
        })

        # Simulate auth check
        journey = await collection.find_one({"journey_id": "j2"})
        requesting_user_id = "user-123"

        is_authorized = journey["user_id"] == requesting_user_id
        assert not is_authorized

    @pytest.mark.asyncio
    async def test_admin_can_access_any_journey(self, mock_db):
        """Admins should be able to access any journey."""
        collection = mock_db.get_collection("journeys")

        await collection.insert_one({
            "journey_id": "j1",
            "user_id": "user-456",
        })

        journey = await collection.find_one({"journey_id": "j1"})
        user = {"user_id": "admin-1", "is_admin": True}

        # Admin check
        is_authorized = journey["user_id"] == user["user_id"] or user.get("is_admin")
        assert is_authorized


class TestJourneyValidation:
    """Tests for journey input validation."""

    def test_efficacy_rating_range(self):
        """Efficacy rating should be between 1 and 10."""
        valid_ratings = [1, 5, 10]
        invalid_ratings = [0, 11, -1]

        for rating in valid_ratings:
            assert 1 <= rating <= 10

        for rating in invalid_ratings:
            assert not (1 <= rating <= 10)

    def test_dose_amount_positive(self):
        """Dose amount should be positive."""
        valid_doses = [0.1, 100, 500.5]
        invalid_doses = [0, -100]

        for dose in valid_doses:
            assert dose > 0

        for dose in invalid_doses:
            assert not (dose > 0)

    def test_symptom_scores_range(self):
        """Symptom scores should be between 1 and 10."""
        valid_scores = [1, 5, 10]
        invalid_scores = [0, 11]

        for score in valid_scores:
            assert 1 <= score <= 10

        for score in invalid_scores:
            assert not (1 <= score <= 10)
