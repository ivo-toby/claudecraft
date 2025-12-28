# Issues to be fixed

- [x] I have two specs in the project, but only the first is shown in the TUI
  - Fixed by adding `scan_and_register_specs()` method to scan filesystem and register untracked specs
- [x] changes in the textareas should be saved, and warn a user that changes are unsaved when the textarea loses focus
  - Implemented unsaved changes tracking with asterisk (*) indicator in subtitle
  - Fixed tab mapping to properly track Q/A tab changes
- [x] the constition is not part of the workflow, nor the TUI. It should editable from the TUI
  - Removed from spec-specific tabs (it's project-level, not spec-level)
  - Added to project configuration screen (accessible via 'c' key)
- [x] I want the agents to be editable from the TUI
  - Implemented project configuration screen accessible via 'c' key
  - Constitution editor in first tab
  - Agents list and editor in second tab
  - Can save with Ctrl+S or Save button
- [x] During ingestion Claude tends to create file with a lot of question. IF there's a questions.md file in the spec, add a tab that loads the file and allow the user to answer the questions. The ingest hook should be smart about this (eg. have claude code mention the possibility of answering in the file)
  - Implemented dynamic Q/A tab that shows "Answers" if answers.md exists, otherwise "Questions" if questions.md exists
  - Save logic properly handles both file types
