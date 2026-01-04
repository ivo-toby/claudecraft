"""BRD/PRD document ingestion."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from claudecraft.core.database import Spec, SpecStatus
from claudecraft.core.project import Project


class Ingestor:
    """BRD/PRD document ingestor."""

    def __init__(self, project: Project):
        """Initialize ingestor."""
        self.project = project

    def ingest(self, document_path: Path, source_type: str = "brd") -> str:
        """
        Ingest a BRD or PRD document.

        Args:
            document_path: Path to BRD/PRD markdown file
            source_type: "brd" or "prd"

        Returns:
            spec_id: ID of created specification
        """
        if not document_path.exists():
            raise FileNotFoundError(f"Document not found: {document_path}")

        if source_type not in ("brd", "prd"):
            raise ValueError(f"source_type must be 'brd' or 'prd', got: {source_type}")

        # Read document
        content = document_path.read_text()

        # Generate spec ID from document title
        spec_id = self._generate_spec_id(content, document_path.stem)

        # Create spec directory
        spec_dir = self.project.ensure_spec_dir(spec_id)

        # Copy source document
        source_file = spec_dir / f"{source_type}.md"
        source_file.write_text(content)

        # Extract metadata
        metadata = self._extract_metadata(content)
        title = metadata.get("title", document_path.stem)

        # Create spec in database
        now = datetime.now()
        spec = Spec(
            id=spec_id,
            title=title,
            status=SpecStatus.DRAFT,
            source_type=source_type,
            created_at=now,
            updated_at=now,
            metadata=metadata,
        )

        self.project.db.create_spec(spec)

        return spec_id

    def _generate_spec_id(self, content: str, fallback: str) -> str:
        """Generate a spec ID from document content or filename."""
        # Try to extract title
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            # Convert to slug
            spec_id = re.sub(r"[^a-z0-9]+", "-", title.lower())
            spec_id = spec_id.strip("-")
            if spec_id:
                return spec_id

        # Fallback to filename
        return re.sub(r"[^a-z0-9]+", "-", fallback.lower()).strip("-")

    def _extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract metadata from document content."""
        metadata: dict[str, Any] = {}

        # Extract title
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        # Extract version
        version_match = re.search(r"Version:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if version_match:
            metadata["version"] = version_match.group(1).strip()

        # Extract author
        author_match = re.search(r"Author:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if author_match:
            metadata["author"] = author_match.group(1).strip()

        # Extract date
        date_match = re.search(r"Date:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if date_match:
            metadata["date"] = date_match.group(1).strip()

        # Count requirements (bullet points)
        requirements = re.findall(r"^\s*[-*•]\s+.+$", content, re.MULTILINE)
        metadata["requirement_count"] = len(requirements)

        # Count headers (sections)
        headers = re.findall(r"^#{2,}\s+.+$", content, re.MULTILINE)
        metadata["section_count"] = len(headers)

        return metadata

    def extract_requirements(self, spec_id: str) -> list[str]:
        """
        Extract requirements from ingested document.

        Args:
            spec_id: Specification ID

        Returns:
            List of extracted requirements
        """
        spec = self.project.db.get_spec(spec_id)
        if not spec or not spec.source_type:
            raise ValueError(f"No source document for spec: {spec_id}")

        spec_dir = self.project.spec_dir(spec_id)
        source_file = spec_dir / f"{spec.source_type}.md"

        if not source_file.exists():
            raise FileNotFoundError(f"Source document not found: {source_file}")

        content = source_file.read_text()

        # Extract bullet points as requirements
        requirements = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*", "•")):
                req = line.lstrip("-*• ").strip()
                if req:
                    requirements.append(req)

        return requirements

    def extract_user_stories(self, spec_id: str) -> list[dict[str, str]]:
        """
        Extract user stories from document.

        Args:
            spec_id: Specification ID

        Returns:
            List of user stories with role, goal, benefit
        """
        spec = self.project.db.get_spec(spec_id)
        if not spec or not spec.source_type:
            raise ValueError(f"No source document for spec: {spec_id}")

        spec_dir = self.project.spec_dir(spec_id)
        source_file = spec_dir / f"{spec.source_type}.md"

        if not source_file.exists():
            raise FileNotFoundError(f"Source document not found: {source_file}")

        content = source_file.read_text()

        # Extract "As a ... I want ... so that ..." patterns
        user_stories = []
        pattern = r"As an? (.+?),\s+I want (.+?)\s+so that (.+?)(?:\.|$)"

        for match in re.finditer(pattern, content, re.IGNORECASE):
            user_stories.append(
                {"role": match.group(1).strip(), "goal": match.group(2).strip(), "benefit": match.group(3).strip()}
            )

        return user_stories
