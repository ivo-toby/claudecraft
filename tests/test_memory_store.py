"""Tests for memory store."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from claudecraft.memory.store import MemoryStore, Entity


@pytest.fixture
def memory_dir(tmp_path):
    """Create a temporary memory directory."""
    return tmp_path / "memory"


@pytest.fixture
def store(memory_dir):
    """Create a memory store."""
    return MemoryStore(memory_dir)


def test_memory_store_creation(store, memory_dir):
    """Test memory store initialization."""
    assert store.memory_dir == memory_dir
    assert memory_dir.exists()
    assert store.entities_file == memory_dir / "entities.json"


def test_entity_creation():
    """Test entity creation."""
    entity = Entity(
        id="test-1",
        type="file",
        name="test.py",
        description="Test file",
        context={"source": "test"},
        created_at=datetime.now(),
        updated_at=datetime.now(),
        relevance_score=1.0,
    )

    assert entity.id == "test-1"
    assert entity.type == "file"
    assert entity.name == "test.py"
    assert entity.relevance_score == 1.0


def test_entity_to_dict():
    """Test entity serialization to dict."""
    now = datetime.now()
    entity = Entity(
        id="test-1",
        type="file",
        name="test.py",
        description="Test file",
        context={"source": "test"},
        created_at=now,
        updated_at=now,
        relevance_score=0.8,
    )

    d = entity.to_dict()

    assert d["id"] == "test-1"
    assert d["type"] == "file"
    assert d["name"] == "test.py"
    assert d["relevance_score"] == 0.8
    assert isinstance(d["created_at"], str)
    assert isinstance(d["updated_at"], str)


def test_entity_from_dict():
    """Test entity deserialization from dict."""
    data = {
        "id": "test-1",
        "type": "concept",
        "name": "Test Concept",
        "description": "A test concept",
        "context": {"key": "value"},
        "created_at": "2024-01-01T12:00:00",
        "updated_at": "2024-01-01T13:00:00",
        "relevance_score": 0.9,
    }

    entity = Entity.from_dict(data)

    assert entity.id == "test-1"
    assert entity.type == "concept"
    assert isinstance(entity.created_at, datetime)
    assert isinstance(entity.updated_at, datetime)


def test_add_entity(store):
    """Test adding entity to store."""
    entity = Entity(
        id="test-1",
        type="file",
        name="test.py",
        description="Test file",
        context={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    store.add_entity(entity)

    assert "test-1" in store.entities
    assert store.entities["test-1"].name == "test.py"


def test_get_entity(store):
    """Test getting entity from store."""
    entity = Entity(
        id="test-1",
        type="file",
        name="test.py",
        description="Test file",
        context={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    store.add_entity(entity)

    retrieved = store.get_entity("test-1")
    assert retrieved is not None
    assert retrieved.id == "test-1"


def test_get_nonexistent_entity(store):
    """Test getting nonexistent entity."""
    entity = store.get_entity("nonexistent")
    assert entity is None


def test_search_entities_by_type(store):
    """Test searching entities by type."""
    # Add different types
    store.add_entity(
        Entity(
            id="file-1",
            type="file",
            name="test.py",
            description="Test",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )
    store.add_entity(
        Entity(
            id="decision-1",
            type="decision",
            name="Use Python",
            description="Decision",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )

    # Search for files
    files = store.search_entities(entity_type="file")
    assert len(files) == 1
    assert files[0].type == "file"

    # Search for decisions
    decisions = store.search_entities(entity_type="decision")
    assert len(decisions) == 1
    assert decisions[0].type == "decision"


def test_search_entities_by_keyword(store):
    """Test searching entities by keyword."""
    store.add_entity(
        Entity(
            id="1",
            type="file",
            name="python_module.py",
            description="Python module",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )
    store.add_entity(
        Entity(
            id="2",
            type="file",
            name="javascript.js",
            description="JavaScript file",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )

    # Search for python
    results = store.search_entities(keyword="python")
    assert len(results) == 1
    assert "python" in results[0].name.lower()


def test_search_entities_limit(store):
    """Test search result limit."""
    # Add many entities
    for i in range(20):
        store.add_entity(
            Entity(
                id=f"entity-{i}",
                type="file",
                name=f"file-{i}.py",
                description="Test",
                context={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )

    # Search with limit
    results = store.search_entities(limit=5)
    assert len(results) == 5


def test_search_entities_relevance_score(store):
    """Test search results sorted by relevance."""
    store.add_entity(
        Entity(
            id="1",
            type="file",
            name="low.py",
            description="Low",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            relevance_score=0.3,
        )
    )
    store.add_entity(
        Entity(
            id="2",
            type="file",
            name="high.py",
            description="High",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            relevance_score=0.9,
        )
    )

    results = store.search_entities()

    # Should be sorted by relevance (high first)
    assert results[0].relevance_score == 0.9
    assert results[1].relevance_score == 0.3


def test_extract_file_references(store):
    """Test extracting file references from text."""
    text = "Please update src/main.py and tests/test_main.py for this feature."

    entities = store.extract_from_text(text, source="test")

    assert len(entities) >= 1
    file_names = [e.name for e in entities]
    assert any("main.py" in name for name in file_names)


def test_extract_decisions(store):
    """Test extracting decisions from text."""
    text = "Decision: We will use Python 3.12 for this project."

    entities = store.extract_from_text(text, source="meeting")

    decisions = [e for e in entities if e.type == "decision"]
    assert len(decisions) >= 1
    assert "Python 3.12" in decisions[0].description


def test_extract_multiple_patterns(store):
    """Test extracting multiple entity types."""
    text = """
    Decision: Use PostgreSQL for database.
    Update config.yaml and main.py accordingly.
    We decided to implement caching.
    """

    entities = store.extract_from_text(text, source="notes")

    # Should extract both files and decisions
    types = {e.type for e in entities}
    assert "file" in types or "decision" in types


def test_get_context_for_spec(store):
    """Test getting context for a spec."""
    # Add some entities
    store.add_entity(
        Entity(
            id="1",
            type="file",
            name="main.py",
            description="Main module",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )

    context = store.get_context_for_spec("spec-1")

    assert isinstance(context, str)
    assert len(context) > 0


def test_get_context_empty_store(store):
    """Test getting context from empty store."""
    context = store.get_context_for_spec("spec-1")

    # Empty store returns empty string (no noise in prompts)
    assert context == ""


def test_cleanup_old_entities(store):
    """Test cleaning up old entities."""
    # Add old entity (manually to avoid updated_at being reset to now)
    old_date = datetime.now() - timedelta(days=100)
    old_entity = Entity(
        id="old",
        type="file",
        name="old.py",
        description="Old",
        context={},
        created_at=old_date,
        updated_at=old_date,
    )
    store.entities["old"] = old_entity
    store._save()

    # Add recent entity
    store.add_entity(
        Entity(
            id="new",
            type="file",
            name="new.py",
            description="New",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )

    # Cleanup entities older than 90 days
    removed = store.cleanup_old_entities(days=90)

    assert removed == 1
    assert "new" in store.entities
    assert "old" not in store.entities


def test_get_stats(store):
    """Test getting memory store statistics."""
    # Add entities
    store.add_entity(
        Entity(
            id="1",
            type="file",
            name="test.py",
            description="Test",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )
    store.add_entity(
        Entity(
            id="2",
            type="decision",
            name="Use React",
            description="Decision",
            context={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )

    stats = store.get_stats()

    assert stats["total_entities"] == 2
    assert stats["by_type"]["file"] == 1
    assert stats["by_type"]["decision"] == 1
    assert "oldest_entity" in stats
    assert "newest_entity" in stats


def test_get_stats_empty_store(store):
    """Test getting stats from empty store."""
    stats = store.get_stats()

    assert stats["total_entities"] == 0
    assert stats["oldest_entity"] is None
    assert stats["newest_entity"] is None


def test_persistence(memory_dir):
    """Test entity persistence across store instances."""
    # Create store and add entity
    store1 = MemoryStore(memory_dir)
    entity = Entity(
        id="persistent",
        type="file",
        name="test.py",
        description="Test",
        context={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    store1.add_entity(entity)

    # Create new store instance
    store2 = MemoryStore(memory_dir)

    # Entity should be loaded
    assert "persistent" in store2.entities
    assert store2.entities["persistent"].name == "test.py"


def test_entity_update(store):
    """Test updating existing entity."""
    entity = Entity(
        id="test",
        type="file",
        name="test.py",
        description="Original",
        context={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    store.add_entity(entity)
    original_updated = store.entities["test"].updated_at

    # Update entity
    entity.description = "Updated"
    store.add_entity(entity)

    # Should be updated
    assert store.entities["test"].description == "Updated"
    assert store.entities["test"].updated_at > original_updated
