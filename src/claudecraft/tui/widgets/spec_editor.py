"""Spec editor widget for TUI."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Label, TabbedContent, TabPane, TextArea


class SpecEditor(Container):
    """Spec editor with tabbed view."""

    CSS = """
    SpecEditor {
        height: 1fr;
    }

    SpecEditor TabbedContent {
        height: 100%;
    }

    SpecEditor TabPane {
        padding: 0;
    }

    SpecEditor TextArea {
        height: 100%;
    }
    """

    def __init__(self, **kwargs) -> None:
        """Initialize spec editor."""
        super().__init__(**kwargs)
        self.current_spec_id: str | None = None
        self.spec_dir: Path | None = None
        self.current_spec = None
        self.loaded_tabs: set[str] = set()
        self._loading_tab: str | None = None
        self.unsaved_tabs: set[str] = set()  # Track which tabs have unsaved changes
        self._original_content: dict[str, str] = {}  # Track original content for comparison

    def compose(self) -> ComposeResult:
        """Compose the spec editor."""
        with TabbedContent(initial="tab-overview"):
            with TabPane("Overview", id="tab-overview"):
                yield TextArea(
                    "# No specification selected\n\nSelect a spec from the left panel.",
                    language="markdown",
                    theme="monokai",
                    id="editor-overview"
                )

            with TabPane("BRD", id="tab-brd"):
                yield TextArea(
                    "No brd.md available",
                    language="markdown",
                    theme="monokai",
                    id="editor-brd"
                )

            with TabPane("PRD", id="tab-prd"):
                yield TextArea(
                    "No prd.md available",
                    language="markdown",
                    theme="monokai",
                    id="editor-prd"
                )

            with TabPane("Spec", id="tab-spec"):
                yield TextArea(
                    "No spec.md available",
                    language="markdown",
                    theme="monokai",
                    id="editor-spec"
                )

            with TabPane("Plan", id="tab-plan"):
                yield TextArea(
                    "No plan.md available",
                    language="markdown",
                    theme="monokai",
                    id="editor-plan"
                )

            with TabPane("Tasks", id="tab-tasks"):
                yield TextArea(
                    "# Tasks\n\nNo specification selected.",
                    language="markdown",
                    theme="monokai",
                    read_only=True,
                    id="editor-tasks"
                )

            with TabPane("Research", id="tab-research"):
                yield TextArea(
                    "No research.md available",
                    language="markdown",
                    theme="monokai",
                    id="editor-research"
                )

            # This tab will be dynamically labeled as Questions or Answers
            with TabPane("Q/A", id="tab-answers"):
                yield TextArea(
                    "No questions or answers available",
                    language="markdown",
                    theme="monokai",
                    id="editor-answers"
                )

    def load_spec(self, spec_id: str) -> None:
        """Load a specification into the editor."""
        self.current_spec_id = spec_id
        self.loaded_tabs.clear()

        # Get project from app
        app = self.app
        if not hasattr(app, "project") or app.project is None:
            return

        # Get spec from database
        spec = app.project.db.get_spec(spec_id)
        if not spec:
            return

        # Cache for lazy loading
        self.current_spec = spec
        self.spec_dir = app.project.spec_dir(spec_id)

        # Only load overview immediately - fast and responsive
        overview_md = self._generate_overview(spec, self.spec_dir)
        self._update_tab("tab-overview", overview_md)
        self.loaded_tabs.add("tab-overview")

        # Watch for tab changes to lazy load
        try:
            tabbed = self.query_one(TabbedContent)
            if not hasattr(self, "_watcher_installed"):
                self.watch(tabbed, "active", self._on_active_tab_changed, init=False)
                self._watcher_installed = True
        except Exception:
            pass

    def _on_active_tab_changed(self, tab_id: str) -> None:
        """Load tab content when user switches to it."""
        if not tab_id or tab_id in self.loaded_tabs or not self.spec_dir:
            return

        # Prevent double-loading
        if self._loading_tab == tab_id:
            return
        self._loading_tab = tab_id

        # Show loading indicator immediately
        self._show_loading_indicator(tab_id)

        # Load asynchronously to avoid blocking UI
        self.call_later(self._load_tab_async, tab_id)

    def _show_loading_indicator(self, tab_id: str) -> None:
        """Show loading indicator in tab."""
        loading_messages = {
            "tab-brd": "# Loading business requirements...\n\nPlease wait while the content loads.",
            "tab-prd": "# Loading product requirements...\n\nPlease wait while the content loads.",
            "tab-spec": "# Loading specification...\n\nPlease wait while the content loads.",
            "tab-plan": "# Loading implementation plan...\n\nPlease wait while the content loads.",
            "tab-tasks": "# Loading tasks...\n\nPlease wait while the content loads.",
            "tab-research": "# Loading research notes...\n\nPlease wait while the content loads.",
        }
        message = loading_messages.get(tab_id, "# Loading...\n\nPlease wait.")
        self._update_tab(tab_id, message)

    def _load_tab_async(self, tab_id: str) -> None:
        """Load tab content asynchronously."""
        # Update app status
        tab_names = {
            "tab-brd": "business requirements",
            "tab-prd": "product requirements",
            "tab-spec": "specification",
            "tab-plan": "plan",
            "tab-tasks": "tasks",
            "tab-research": "research",
            "tab-answers": "Q/A"
        }
        tab_name = tab_names.get(tab_id, "content")

        try:
            if hasattr(self.app, 'sub_title'):
                original_subtitle = self.app.sub_title
        except Exception:
            original_subtitle = None

        try:
            if hasattr(self.app, 'sub_title'):
                self.app.sub_title = f"Loading {tab_name}..."
        except Exception:
            pass

        # Load the content
        if tab_id == "tab-brd":
            self._load_file_to_tab(self.spec_dir / "brd.md", tab_id)
        elif tab_id == "tab-prd":
            self._load_file_to_tab(self.spec_dir / "prd.md", tab_id)
        elif tab_id == "tab-spec":
            self._load_file_to_tab(self.spec_dir / "spec.md", tab_id)
        elif tab_id == "tab-plan":
            self._load_file_to_tab(self.spec_dir / "plan.md", tab_id)
        elif tab_id == "tab-tasks":
            self._load_tasks_from_database(tab_id)
        elif tab_id == "tab-research":
            self._load_file_to_tab(self.spec_dir / "research.md", tab_id)
        elif tab_id == "tab-answers":
            # Check for answers.md first, then questions.md
            answers_file = self.spec_dir / "answers.md"
            questions_file = self.spec_dir / "questions.md"

            if answers_file.exists():
                # Update tab label
                try:
                    tabbed = self.query_one(TabbedContent)
                    for tab in tabbed.query(TabPane):
                        if tab.id == "tab-answers":
                            tab.label = "Answers"
                            break
                except Exception:
                    pass
                self._load_file_to_tab(answers_file, tab_id)
            elif questions_file.exists():
                # Update tab label
                try:
                    tabbed = self.query_one(TabbedContent)
                    for tab in tabbed.query(TabPane):
                        if tab.id == "tab-answers":
                            tab.label = "Questions"
                            break
                except Exception:
                    pass
                self._load_file_to_tab(questions_file, tab_id)
            else:
                self._update_tab(tab_id, "No questions or answers available")

        self.loaded_tabs.add(tab_id)
        self._loading_tab = None

        # Restore subtitle
        try:
            if hasattr(self.app, 'sub_title') and original_subtitle:
                self.app.sub_title = original_subtitle
        except Exception:
            pass

    def _generate_overview(self, spec, spec_dir: Path) -> str:
        """Generate overview markdown."""
        app = self.app
        tasks = app.project.db.list_tasks(spec_id=spec.id)
        completed = len([t for t in tasks if t.status.value == "completed"])
        total = len(tasks)

        overview = f"""# {spec.title}

**ID**: {spec.id}
**Status**: {spec.status.value}
**Created**: {spec.created_at.strftime("%Y-%m-%d %H:%M")}
**Updated**: {spec.updated_at.strftime("%Y-%m-%d %H:%M")}

## Progress

- Tasks: {completed}/{total} completed
- Coverage: {(completed/total*100) if total > 0 else 0:.1f}%

## Files

"""
        # List available files
        files = []
        for file_name in ["brd.md", "prd.md", "spec.md", "plan.md", "tasks.md", "research.md"]:
            file_path = spec_dir / file_name
            if file_path.exists():
                size = file_path.stat().st_size
                files.append(f"- ✓ {file_name} ({size} bytes)")
            else:
                files.append(f"- ✗ {file_name}")

        overview += "\n".join(files)

        if spec.metadata:
            overview += "\n\n## Metadata\n\n"
            for key, value in spec.metadata.items():
                overview += f"- **{key}**: {value}\n"

        return overview

    def _load_file_to_tab(self, file_path: Path, tab_id: str) -> None:
        """Load a file into a tab."""
        if file_path.exists():
            content = file_path.read_text()
            self._update_tab(tab_id, content)
        else:
            self._update_tab(tab_id, f"File not found: {file_path.name}")

    def _load_tasks_from_database(self, tab_id: str) -> None:
        """Load tasks from the database and format as markdown."""
        app = self.app
        if not hasattr(app, "project") or app.project is None or not self.current_spec_id:
            self._update_tab(tab_id, "# Tasks\n\nNo project loaded.")
            return

        tasks = app.project.db.list_tasks(spec_id=self.current_spec_id)

        if not tasks:
            self._update_tab(tab_id, f"# Tasks\n\nNo tasks defined for spec: {self.current_spec_id}")
            return

        # Group tasks by status
        status_groups = {
            "todo": [],
            "implementing": [],
            "testing": [],
            "reviewing": [],
            "done": [],
        }

        for task in tasks:
            status_key = task.status.value if hasattr(task.status, 'value') else str(task.status)
            if status_key in status_groups:
                status_groups[status_key].append(task)
            else:
                status_groups["todo"].append(task)

        # Build markdown content
        lines = [f"# Tasks for {self.current_spec_id}", ""]

        # Summary
        total = len(tasks)
        done_count = len(status_groups["done"])
        lines.append(f"**Total:** {total} tasks | **Completed:** {done_count} ({done_count/total*100:.0f}% done)" if total > 0 else "**Total:** 0 tasks")
        lines.append("")

        # Status emoji mapping
        status_emoji = {
            "todo": "📋",
            "implementing": "🔨",
            "testing": "🧪",
            "reviewing": "🔍",
            "done": "✅",
        }

        # Display tasks by status (active first, then done)
        status_order = ["implementing", "testing", "reviewing", "todo", "done"]

        for status in status_order:
            task_list = status_groups[status]
            if not task_list:
                continue

            emoji = status_emoji.get(status, "📌")
            status_title = status.replace("_", " ").title()
            lines.append(f"## {emoji} {status_title} ({len(task_list)})")
            lines.append("")

            for task in sorted(task_list, key=lambda t: t.priority):
                # Priority indicator
                priority_marker = "🔴" if task.priority == 1 else "🟡" if task.priority == 2 else "🟢"

                lines.append(f"### {priority_marker} {task.id}: {task.title}")
                lines.append("")

                if task.description:
                    lines.append(task.description)
                    lines.append("")

                # Show metadata for follow-up tasks
                if task.metadata:
                    if task.metadata.get("is_followup"):
                        category = task.metadata.get("category", "unknown")
                        parent = task.metadata.get("parent_task", "N/A")
                        lines.append(f"*Follow-up task ({category}) from {parent}*")
                        lines.append("")

                lines.append("---")
                lines.append("")

        content = "\n".join(lines)
        self._update_tab(tab_id, content)

    def _update_tab(self, tab_id: str, content: str) -> None:
        """Update tab content."""
        try:
            # Map tab IDs to editor IDs
            editor_ids = {
                "tab-overview": "editor-overview",
                "tab-brd": "editor-brd",
                "tab-prd": "editor-prd",
                "tab-spec": "editor-spec",
                "tab-plan": "editor-plan",
                "tab-tasks": "editor-tasks",
                "tab-research": "editor-research",
                "tab-answers": "editor-answers",
            }
            editor_id = editor_ids.get(tab_id)
            if not editor_id:
                return

            # Update TextArea content - instant, no rendering needed
            editor = self.query_one(f"#{editor_id}", TextArea)
            editor.load_text(content)

            # Store original content for change detection
            self._original_content[tab_id] = content

            # Mark as saved
            if tab_id in self.unsaved_tabs:
                self.unsaved_tabs.remove(tab_id)
        except Exception:
            pass  # Tab not found or other error

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Track changes in text areas."""
        # Map editor IDs back to tab IDs (excluding readonly tabs like tasks)
        tab_map = {
            "editor-brd": "tab-brd",
            "editor-prd": "tab-prd",
            "editor-spec": "tab-spec",
            "editor-plan": "tab-plan",
            "editor-research": "tab-research",
            "editor-answers": "tab-answers",
        }

        # Get the TextArea that triggered the event
        editor_id = event.text_area.id if hasattr(event.text_area, 'id') else None
        tab_id = tab_map.get(editor_id) if editor_id else None

        if not tab_id:
            return  # Overview/constitution or unknown

        # Check if content differs from original
        current_content = event.text_area.text
        original_content = self._original_content.get(tab_id, "")

        if current_content != original_content:
            self.unsaved_tabs.add(tab_id)
            # Update app subtitle to show unsaved indicator
            self.call_later(self._update_unsaved_indicator)
        else:
            if tab_id in self.unsaved_tabs:
                self.unsaved_tabs.remove(tab_id)
                # Clear unsaved indicator if no tabs have changes
                if not self.unsaved_tabs:
                    self.call_later(self._clear_unsaved_indicator)

    def _update_unsaved_indicator(self) -> None:
        """Update subtitle with unsaved indicator."""
        try:
            if hasattr(self.app, 'sub_title'):
                if not self.app.sub_title.endswith(" *"):
                    self.app.sub_title = f"{self.app.sub_title} *"
        except Exception:
            pass

    def _clear_unsaved_indicator(self) -> None:
        """Clear unsaved indicator from subtitle."""
        try:
            if hasattr(self.app, 'sub_title'):
                if self.app.sub_title.endswith(" *"):
                    self.app.sub_title = self.app.sub_title[:-2]
        except Exception:
            pass

    def save_current_tab(self) -> bool:
        """Save the currently active tab content to disk."""
        try:
            tabbed = self.query_one(TabbedContent)
            active_tab = tabbed.active

            # Skip overview and tasks - they're generated/readonly, not editable
            if active_tab in ("tab-overview", "tab-tasks"):
                return False

            # Handle constitution separately (project-level)
            if active_tab == "tab-constitution":
                return self._save_constitution()

            # Map tab to file
            file_map = {
                "tab-brd": "brd.md",
                "tab-prd": "prd.md",
                "tab-spec": "spec.md",
                "tab-plan": "plan.md",
                "tab-research": "research.md",
            }

            # Handle Q/A tab specially - determine which file to save to
            if active_tab == "tab-answers":
                # Check which file exists to determine where to save
                answers_file = self.spec_dir / "answers.md"
                questions_file = self.spec_dir / "questions.md"

                if answers_file.exists():
                    filename = "answers.md"
                elif questions_file.exists():
                    filename = "questions.md"
                else:
                    # Default to questions.md if neither exists
                    filename = "questions.md"
            else:
                filename = file_map.get(active_tab)

            if not filename or not self.spec_dir:
                return False

            # Get editor content
            editor_ids = {
                "tab-brd": "editor-brd",
                "tab-prd": "editor-prd",
                "tab-spec": "editor-spec",
                "tab-plan": "editor-plan",
                "tab-research": "editor-research",
                "tab-answers": "editor-answers",
            }
            editor_id = editor_ids.get(active_tab)
            if not editor_id:
                return False

            editor = self.query_one(f"#{editor_id}", TextArea)
            content = editor.text

            # Save to file
            file_path = self.spec_dir / filename
            file_path.write_text(content)

            # Update original content and clear unsaved flag
            self._original_content[active_tab] = content
            if active_tab in self.unsaved_tabs:
                self.unsaved_tabs.remove(active_tab)

            # Update app subtitle to show saved
            if hasattr(self.app, 'sub_title'):
                # Remove asterisk if no unsaved tabs
                subtitle = self.app.sub_title
                if subtitle.endswith(" *") and not self.unsaved_tabs:
                    subtitle = subtitle[:-2]

                self.app.sub_title = f"Saved {filename}"
                # Restore after 2 seconds
                final_subtitle = subtitle if not self.unsaved_tabs else f"{subtitle}"
                self.set_timer(2.0, lambda: setattr(self.app, 'sub_title', final_subtitle))

            return True
        except Exception:
            return False

    def _save_constitution(self) -> bool:
        """Save the constitution file."""
        try:
            app = self.app
            if not hasattr(app, "project") or app.project is None:
                return False

            editor = self.query_one("#editor-constitution", TextArea)
            content = editor.text

            # Save to file
            constitution_file = app.project.root / ".claudecraft" / "constitution.md"
            constitution_file.write_text(content)

            # Update original content and clear unsaved flag
            self._original_content["tab-constitution"] = content
            if "tab-constitution" in self.unsaved_tabs:
                self.unsaved_tabs.remove("tab-constitution")

            # Update app subtitle to show saved
            if hasattr(app, 'sub_title'):
                # Remove asterisk if no unsaved tabs
                subtitle = app.sub_title
                if subtitle.endswith(" *") and not self.unsaved_tabs:
                    subtitle = subtitle[:-2]

                app.sub_title = "Saved constitution.md"
                # Restore after 2 seconds
                final_subtitle = subtitle if not self.unsaved_tabs else f"{subtitle}"
                self.set_timer(2.0, lambda: setattr(app, 'sub_title', final_subtitle))

            return True
        except Exception:
            return False
