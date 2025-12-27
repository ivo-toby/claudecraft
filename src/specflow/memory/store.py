"""Memory store for cross-session context."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Entity:
    """An extracted entity from a session."""

    id: str
    type: str  # file, concept, decision, pattern, dependency
    name: str
    description: str
    context: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    relevance_score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        d["updated_at"] = self.updated_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        """Create from dictionary."""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class MemoryStore:
    """Store for persistent memory across sessions."""

    def __init__(self, memory_dir: Path):
        """Initialize memory store."""
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.entities_file = memory_dir / "entities.json"
        self.entities: dict[str, Entity] = {}
        self._load()

    def _load(self) -> None:
        """Load entities from disk."""
        if not self.entities_file.exists():
            return

        try:
            with open(self.entities_file) as f:
                data = json.load(f)
                for entity_data in data:
                    entity = Entity.from_dict(entity_data)
                    self.entities[entity.id] = entity
        except Exception:
            # If loading fails, start fresh
            self.entities = {}

    def _save(self) -> None:
        """Save entities to disk."""
        data = [entity.to_dict() for entity in self.entities.values()]
        with open(self.entities_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_entity(self, entity: Entity) -> None:
        """Add or update an entity."""
        entity.updated_at = datetime.now()
        self.entities[entity.id] = entity
        self._save()

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get an entity by ID."""
        return self.entities.get(entity_id)

    def search_entities(
        self, entity_type: str | None = None, keyword: str | None = None, limit: int = 10
    ) -> list[Entity]:
        """Search entities by type and/or keyword."""
        results = list(self.entities.values())

        # Filter by type
        if entity_type:
            results = [e for e in results if e.type == entity_type]

        # Filter by keyword
        if keyword:
            keyword_lower = keyword.lower()
            results = [
                e
                for e in results
                if keyword_lower in e.name.lower() or keyword_lower in e.description.lower()
            ]

        # Sort by relevance score
        results.sort(key=lambda e: e.relevance_score, reverse=True)

        return results[:limit]

    def extract_from_text(self, text: str, source: str) -> list[Entity]:
        """
        Extract entities from text.

        This is a simple implementation. In a production system,
        you might use NLP or LLM for better extraction.
        """
        entities = []

        # Extract file references
        import re

        file_pattern = r"(?:^|\s)([\w\/\-\.]+\.(py|js|ts|md|json|yaml|yml))(?:\s|$)"
        for match in re.finditer(file_pattern, text, re.IGNORECASE):
            file_path = match.group(1)
            entity_id = f"file:{file_path}"

            if entity_id not in self.entities:
                entity = Entity(
                    id=entity_id,
                    type="file",
                    name=file_path,
                    description=f"File referenced in {source}",
                    context={"source": source},
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                entities.append(entity)
                self.add_entity(entity)

        # Extract decisions (lines starting with "Decision:", "We decided", etc.)
        decision_pattern = r"(?:Decision|We decided|Chosen approach):\s*(.+)"
        for match in re.finditer(decision_pattern, text, re.IGNORECASE):
            decision = match.group(1).strip()
            entity_id = f"decision:{abs(hash(decision))}"

            if entity_id not in self.entities:
                entity = Entity(
                    id=entity_id,
                    type="decision",
                    name=decision[:50],
                    description=decision,
                    context={"source": source},
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    relevance_score=0.9,
                )
                entities.append(entity)
                self.add_entity(entity)

        return entities

    def get_context_for_spec(self, spec_id: str) -> str:
        """Get relevant context for a specification."""
        # Find entities related to this spec
        entities = self.search_entities(limit=20)

        if not entities:
            return "No relevant context found in memory."

        context = "# Relevant Context from Memory\n\n"

        # Group by type
        by_type: dict[str, list[Entity]] = {}
        for entity in entities:
            if entity.type not in by_type:
                by_type[entity.type] = []
            by_type[entity.type].append(entity)

        for entity_type, type_entities in by_type.items():
            context += f"## {entity_type.capitalize()}s\n\n"
            for entity in type_entities[:5]:  # Top 5 per type
                context += f"- **{entity.name}**: {entity.description}\n"
            context += "\n"

        return context

    def cleanup_old_entities(self, days: int = 90) -> int:
        """Remove entities older than specified days."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        before_count = len(self.entities)

        self.entities = {
            eid: entity for eid, entity in self.entities.items() if entity.updated_at >= cutoff
        }

        self._save()
        return before_count - len(self.entities)

    def get_stats(self) -> dict[str, Any]:
        """Get memory store statistics."""
        by_type: dict[str, int] = {}
        for entity in self.entities.values():
            by_type[entity.type] = by_type.get(entity.type, 0) + 1

        return {
            "total_entities": len(self.entities),
            "by_type": by_type,
            "oldest_entity": (
                min(self.entities.values(), key=lambda e: e.created_at).created_at.isoformat()
                if self.entities
                else None
            ),
            "newest_entity": (
                max(self.entities.values(), key=lambda e: e.created_at).created_at.isoformat()
                if self.entities
                else None
            ),
        }
