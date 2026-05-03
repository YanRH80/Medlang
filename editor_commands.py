"""Pluggable command registry for the editor.

Scope
-----
Holds the catalog of commands available through the `:` palette. Each
command is a `(name, description, handler)` triple registered at app
startup. The registry knows how to fuzzy-find names by query and how to
execute a registered handler by name.

Design
------
- Open/Closed: the registry never has to be edited to add a new command.
  Callers register new commands at startup. Adding a new feature is one
  `registry.register(...)` call in `app.py`.
- Dependency Inversion: handlers are opaque callables supplied by the
  caller. The registry imports nothing from feature modules, so commands
  can depend on app-level state without polluting the registry.
- Single Responsibility: ranking + dispatch only. UI, key handling, and
  feature side effects live elsewhere.

Boundaries
----------
- Does NOT render UI. The command palette modal queries this registry but
  owns its own widgets.
- Does NOT handle keyboard input.
- Does NOT have hardcoded knowledge of any specific command.

Freeze criteria
---------------
This module can be considered frozen once:
- `register`, `unregister`, `is_enabled`, `description`, and
  `command_names` round-trip correctly.
- `fuzzy_find` returns the expected ranking for prefix, substring, and
  fuzzy-only matches.
- `execute` runs the registered handler and returns its `CommandResult`,
  or a graceful failure for unknown / disabled commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable


@dataclass(frozen=True)
class CommandResult:
    """Result of executing a colon command."""

    ok: bool
    message: str = ""


@dataclass(frozen=True)
class Command:
    """A single command registered in the palette."""

    name: str
    description: str
    handler: Callable[[Any], CommandResult]
    enabled: bool = True


@dataclass
class CommandRegistry:
    """In-memory registry of commands, keyed by name."""

    _commands: dict[str, Command] = field(default_factory=dict)

    # ----- registration ----------------------------------------------------

    def register(self, command: Command) -> None:
        """Register or replace a command by name."""

        self._commands[command.name] = command

    def unregister(self, name: str) -> None:
        """Remove a command. No-op if it was never registered."""

        self._commands.pop(name, None)

    # ----- introspection ---------------------------------------------------

    def is_enabled(self, name: str) -> bool:
        cmd = self._commands.get(name)
        return bool(cmd and cmd.enabled)

    def description(self, name: str) -> str:
        cmd = self._commands.get(name)
        return cmd.description if cmd else name

    def command_names(self) -> list[str]:
        """Return the enabled command names in registration order."""

        return [name for name, cmd in self._commands.items() if cmd.enabled]

    # ----- fuzzy matching --------------------------------------------------

    def fuzzy_find(self, query: str, limit: int = 20) -> list[str]:
        """Return command names ranked by fuzzy similarity to the query.

        A candidate is kept only if every character of the query appears
        in the command name in order (fzf-style subsequence filter), or
        if the description matches very strongly. Ranking then promotes
        prefix and substring matches to the top.
        """

        normalized_query = query.strip().lower()
        if not normalized_query:
            return self.command_names()[:limit]

        scored: list[tuple[float, str]] = []
        for name in self.command_names():
            description = self.description(name).lower()
            normalized_name = name.lower()

            keeps = (
                _is_subsequence(normalized_query, normalized_name)
                or normalized_query in description
            )
            if not keeps:
                continue

            score = self._score(normalized_query, normalized_name, description)
            scored.append((score, name))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [name for _, name in scored[:limit]]

    def _score(self, query: str, normalized_name: str, description: str) -> float:
        """Score a (query, name, description) triple. Higher is better."""

        ratio = SequenceMatcher(None, query, normalized_name).ratio()
        if normalized_name.startswith(query):
            ratio += 0.4
        if query in normalized_name:
            ratio += 0.2
        ratio += SequenceMatcher(None, query, description).ratio() * 0.15
        return ratio

    # ----- execution -------------------------------------------------------

    def _resolve_strict(self, query: str) -> tuple[str | None, list[str]]:
        """Resolve a partial query to a unique command via prefix match.

        Returns `(name, prefix_matches)`. `name` is set only when exactly
        one command name starts with `query`; otherwise `prefix_matches`
        carries every prefix candidate so the caller can report the
        ambiguity.
        """

        normalized = query.strip().lower()
        if not normalized:
            return None, []
        prefix_matches = [
            name for name in self.command_names()
            if name.lower().startswith(normalized)
        ]
        if len(prefix_matches) == 1:
            return prefix_matches[0], prefix_matches
        return None, prefix_matches

    def execute(self, app: Any, command_text: str) -> CommandResult:
        """Run a registered command.

        Resolution order:
        1. Exact name match (used by the modal, where the full name is picked).
        2. Unique prefix match (lets `:tog` execute `theme-toggle`).
        3. Otherwise, report ambiguity or unknown.
        """

        normalized = command_text.strip()
        if not normalized:
            return CommandResult(False, "empty command")

        cmd = self._commands.get(normalized)
        if cmd is None:
            resolved, prefix_matches = self._resolve_strict(normalized)
            if resolved is not None:
                cmd = self._commands.get(resolved)
            elif prefix_matches:
                return CommandResult(
                    False, "ambiguous: " + ", ".join(prefix_matches)
                )

        if cmd is None:
            return CommandResult(False, f"unknown command: {normalized}")
        if not cmd.enabled:
            return CommandResult(False, f"{cmd.name} is disabled")

        try:
            return cmd.handler(app)
        except Exception as exc:  # pragma: no cover - defensive
            return CommandResult(False, f"{cmd.name} failed: {exc}")


# ---------------------------------------------------------------------------
# Helper for config-driven enabling.
# ---------------------------------------------------------------------------

def is_enabled_in_config(config: dict[str, Any], name: str) -> bool:
    """Return whether `name` is enabled in the YAML config block.

    Missing entries default to `True` so registering a brand-new command
    without touching the config still works.
    """

    entry = config.get(name)
    if isinstance(entry, dict):
        return bool(entry.get("enabled", True))
    return True


def description_from_config(config: dict[str, Any], name: str, fallback: str) -> str:
    """Look up a command description in config, with a sane fallback."""

    entry = config.get(name)
    if isinstance(entry, dict):
        value = entry.get("description")
        if isinstance(value, str) and value.strip():
            return value
    return fallback


def _is_subsequence(query: str, candidate: str) -> bool:
    """Return True iff every char of `query` appears in `candidate` in order."""

    it = iter(candidate)
    return all(ch in it for ch in query)
