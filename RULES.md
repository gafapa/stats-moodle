# Repository Rules

## Language

- Use English for code identifiers.
- Use English for Markdown documentation.
- Use English for code comments and commit messages.

## Documentation Sync

- Update documentation whenever application behavior changes.
- Keep authentication docs aligned with the actual Moodle connection flow.
- Keep website copy aligned with the current app behavior when user-visible workflows or analysis criteria change.
- Keep deployment instructions aligned with the current standalone build and `prepare_web_release.bat` output layout.

## Security

- Do not persist Moodle passwords.
- Persist generated tokens only when the user saves or updates a profile.
- Restrict Moodle interactions to read-only APIs for analysis flows.

## Testing

- Add or update automated tests for behavior changes.
- Run the unit test suite before closing a task when feasible.
- Add regression coverage when changing risk thresholds, adaptive metrics, or other analysis heuristics that may affect interpretation.
