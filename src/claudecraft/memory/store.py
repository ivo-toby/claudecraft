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

    def extract_from_text(self, text: str, source: str, spec_id: str | None = None) -> list[Entity]:
        """
        Extract entities from text.

        Extracts:
        - File references
        - Decisions and choices
        - Patterns and approaches
        - Technical notes
        - Dependencies
        """
        entities = []
        import re

        base_context = {"source": source}
        if spec_id:
            base_context["spec_id"] = spec_id

        # Extract file references
        file_pattern = r"(?:^|\s)([\w\/\-\.]+\.(py|js|ts|tsx|md|json|yaml|yml|toml|sh))(?:\s|$|:|\))"
        for match in re.finditer(file_pattern, text, re.IGNORECASE):
            file_path = match.group(1)
            entity_id = f"file:{file_path}"

            if entity_id not in self.entities:
                entity = Entity(
                    id=entity_id,
                    type="file",
                    name=file_path,
                    description=f"File referenced in {source}",
                    context=base_context.copy(),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                entities.append(entity)
                self.add_entity(entity)

        # Extract decisions (lines starting with "Decision:", "We decided", etc.)
        decision_pattern = r"(?:Decision|We decided|Chosen approach|Using|Implementing with):\s*(.+?)(?:\n|$)"
        for match in re.finditer(decision_pattern, text, re.IGNORECASE):
            decision = match.group(1).strip()
            if len(decision) > 10:  # Skip very short matches
                entity_id = f"decision:{abs(hash(decision)) % 100000}"

                if entity_id not in self.entities:
                    entity = Entity(
                        id=entity_id,
                        type="decision",
                        name=decision[:50],
                        description=decision,
                        context=base_context.copy(),
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        relevance_score=0.9,
                    )
                    entities.append(entity)
                    self.add_entity(entity)

        # Extract patterns (architectural patterns, design patterns)
        pattern_indicators = [
            r"(?:pattern|approach|architecture):\s*(.+?)(?:\n|$)",
            r"(?:using|implemented)\s+(singleton|factory|observer|decorator|adapter|facade|repository)\s+pattern",
            r"(?:following|using)\s+(mvc|mvvm|clean architecture|hexagonal|layered)\s+(?:pattern|architecture)",
        ]
        for pattern in pattern_indicators:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                pattern_desc = match.group(1).strip() if match.lastindex else match.group(0).strip()
                entity_id = f"pattern:{abs(hash(pattern_desc)) % 100000}"

                if entity_id not in self.entities and len(pattern_desc) > 5:
                    entity = Entity(
                        id=entity_id,
                        type="pattern",
                        name=pattern_desc[:50],
                        description=pattern_desc,
                        context=base_context.copy(),
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        relevance_score=0.8,
                    )
                    entities.append(entity)
                    self.add_entity(entity)

        # Extract dependencies (package names, libraries)
        dependency_patterns = [
            r"(?:install|pip install|npm install|using)\s+([\w\-]+)",
            r"(?:import|from)\s+([\w\.]+)",
            r"(?:depends on|requires)\s+([\w\-\.]+)",
        ]
        for pattern in dependency_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                dep = match.group(1).strip()
                # Skip common Python builtins and short names
                if len(dep) > 2 and dep not in ["os", "re", "sys", "json", "from", "import"]:
                    entity_id = f"dependency:{dep}"

                    if entity_id not in self.entities:
                        entity = Entity(
                            id=entity_id,
                            type="dependency",
                            name=dep,
                            description=f"Dependency: {dep}",
                            context=base_context.copy(),
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            relevance_score=0.6,
                        )
                        entities.append(entity)
                        self.add_entity(entity)

        # Extract technical notes (TODO, FIXME, NOTE, IMPORTANT)
        note_pattern = r"(?:TODO|FIXME|NOTE|IMPORTANT|WARNING):\s*(.+?)(?:\n|$)"
        for match in re.finditer(note_pattern, text, re.IGNORECASE):
            note = match.group(1).strip()
            if len(note) > 10:
                entity_id = f"note:{abs(hash(note)) % 100000}"

                if entity_id not in self.entities:
                    entity = Entity(
                        id=entity_id,
                        type="note",
                        name=note[:50],
                        description=note,
                        context=base_context.copy(),
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        relevance_score=0.7,
                    )
                    entities.append(entity)
                    self.add_entity(entity)

        return entities

    def get_context_for_spec(self, spec_id: str) -> str:
        """Get relevant context for a specification."""
        # Find entities related to this spec (prioritize spec-specific, then general)
        spec_entities = [
            e for e in self.entities.values()
            if e.context.get("spec_id") == spec_id
        ]
        general_entities = [
            e for e in self.entities.values()
            if e.context.get("spec_id") is None
        ]

        # Combine: spec-specific first, then general (sorted by relevance)
        entities = sorted(spec_entities, key=lambda e: e.relevance_score, reverse=True)
        entities += sorted(general_entities, key=lambda e: e.relevance_score, reverse=True)

        if not entities:
            return ""  # Return empty string if no context

        context = "## Relevant Context from Memory\n\n"

        # Group by type
        by_type: dict[str, list[Entity]] = {}
        for entity in entities[:30]:  # Limit total entities
            if entity.type not in by_type:
                by_type[entity.type] = []
            by_type[entity.type].append(entity)

        # Order types by importance
        type_order = ["decision", "pattern", "note", "file", "dependency"]
        for entity_type in type_order:
            if entity_type in by_type:
                type_entities = by_type[entity_type]
                context += f"### {entity_type.capitalize()}s\n"
                for entity in type_entities[:5]:  # Top 5 per type
                    context += f"- **{entity.name}**: {entity.description}\n"
                context += "\n"

        # Add any remaining types
        for entity_type, type_entities in by_type.items():
            if entity_type not in type_order:
                context += f"### {entity_type.capitalize()}s\n"
                for entity in type_entities[:5]:
                    context += f"- **{entity.name}**: {entity.description}\n"
                context += "\n"

        return context

    def get_entities_for_spec(self, spec_id: str) -> list[Entity]:
        """Get all entities associated with a specific spec."""
        return [
            e for e in self.entities.values()
            if e.context.get("spec_id") == spec_id
        ]

    def add_memory(
        self,
        entity_type: str,
        name: str,
        description: str,
        spec_id: str | None = None,
        relevance: float = 1.0,
    ) -> Entity:
        """Convenience method to add a memory entry."""
        entity_id = f"{entity_type}:{abs(hash(name + description)) % 100000}"

        context = {}
        if spec_id:
            context["spec_id"] = spec_id

        entity = Entity(
            id=entity_id,
            type=entity_type,
            name=name[:50],
            description=description,
            context=context,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            relevance_score=relevance,
        )
        self.add_entity(entity)
        return entity

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
