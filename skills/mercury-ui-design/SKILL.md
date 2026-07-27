---
name: mercury-ui-design
description: Use when designing, adding, reviewing, or polishing any Mercury RSS Reader interface, PySide6 widget, dialog, panel, toolbar, Reader view, theme, interaction state, or UI test; enforces the approved warm-modern light theme, near-black graphite-blue dark theme, semantic tokens, accessibility, and UI architecture boundaries.
---

# Mercury UI Design

## Core contract

Keep every new screen visually continuous with Mercury. Reuse semantic tokens and existing component patterns; never invent a local palette, radius, control height, or theme system.

**REQUIRED SUB-SKILLS:** Use `superpowers:brainstorming` before changing appearance or behavior, `superpowers:test-driven-development` during implementation, and `superpowers:verification-before-completion` before claiming completion.

## Workflow

1. Inspect `app/styles.py`, `ui/theme.py`, `ui/theme_controller.py`, the target component, and its `tests/test_ui/` coverage.
2. Sketch the new UI using the existing three-column hierarchy and 4/8 px spacing grid. Preserve the current Feed, article, Reader mode, scroll position, and unsaved state during visual changes.
3. Add or extend semantic roles in `ui/theme.py`; consume them from centralized QSS or Reader CSS. Do not place hex colors in component files.
4. Write failing `pytest-qt` tests for state, accessibility, theme switching, and stale-result protection before production code.
5. Implement only UI intent collection and presentation. Emit typed signals to controllers/use cases; never call SQL, HTTP, extraction, LLM, or Store code from a View.
6. Render and inspect both themes, then run UI and full regression suites.

## Approved visual system

### Light theme: warm modern

- Window `#F6F4EE`; surface `#FFFDF8`; alternate surface `#EFEEE8`.
- Text `#26343F`; muted text `#68766F`.
- Accent `#4F827D`; hover `#43746F`; pressed `#38645F`.
- Sidebar `#162A3A`; selected item `#315B68`.
- Avoid pure white reading backgrounds and cold generic blue accents.

### Dark theme: near-black graphite blue

- Window `#0A0D12`; surface `#10151C`; alternate surface/control `#171D26`.
- Hover `#202832`; pressed `#2A3440`; border `#242C36`.
- Sidebar `#080B10`; selected item `#1B2A3D`.
- Text `#ECEEF1`; muted text `#9AA4B1`; disabled text `#66717E`.
- Accent `#557FC0`; hover `#6590D2`; pressed `#466DAC`; focus `#79A1DD`.
- Preserve subtle blue-gray separation between panes. Do not use green, pure black, or pure white as the dominant dark theme.

Keep preference values exactly `system`, `light`, and `dark`. Default to `system`, persist through `QSettings`, and update Qt QSS and Reader HTML together without refetching content.

## Components and interaction

- Use 8 px control radius, 12 px panel radius, and pill radius only for badges/tags.
- Use 36 px minimum height for normal controls and at least 36×36 px targets for icon buttons.
- Implement `normal`, `hover`, `pressed`, `checked`, `focus`, and `disabled` for every interactive control.
- Use solid accent for the primary action, low-contrast surfaces for secondary actions, and neutral destructive controls that reveal muted red on hover or confirmation.
- Use a visible 2 px focus treatment; add Tooltip and `accessibleName` to every icon button.
- Express unread, favorite, loading, error, disabled, and selected states with text/icon/shape in addition to color.
- Support `empty`, `loading`, `content`, `error`, `offline`, and `disabled` without blank panes or layout jumps.
- Let long Chinese/English text wrap or elide with Tooltip. Preserve keyboard focus order and high-DPI scaling.

## Reader rules

Use the global effective theme. Render prose with a comfortable serif stack, approximately 1.76 line height, responsive gutters, constrained media, scrollable tables/code, blue links, muted metadata, and palette-backed code/quote surfaces. Keep JavaScript disabled in Reader mode and never reload the network solely for a theme change.

## Acceptance gate

Before handoff, verify:

- Both themes cover the window, sidebar, lists, Reader, dialogs, menus, status bar, scrollbars, and all six control states.
- Text and essential controls meet WCAG AA; no state relies only on color.
- Keyboard navigation, Tooltip, accessible names, Chinese/English labels, and 100%/150%/200% scaling remain usable.
- Theme switching preserves selection, Reader settings, content, and pending edits.
- `ruff check app/styles.py ui tests/test_ui`, `ruff format --check app/styles.py ui tests/test_ui`, `pytest tests/test_ui -q`, and the full `pytest -q` pass.
- Changes stay inside authorized UI files unless the user explicitly expands scope.

## Example

For a new tag panel, reuse the current surfaces and spacing, style tag pills with semantic accent roles, provide visible add/remove states and 36 px targets, emit tag intentions through signals, test both themes and keyboard use, and reject any proposal that introduces pure-white cards, green dark surfaces, 6 px radii, or a second theme preference.
