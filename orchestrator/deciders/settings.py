"""Orchestrator decision settings from `.pipeline/config.json`."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DECIDER = "jev"
DEFAULT_FALLBACK = "grok-4.6"
DEFAULT_JEV_MODEL = "jev-latest"
DEFAULT_MIN_CONFIDENCE = 0.5
KNOWN_DECIDERS = ("fixed", "jev")
DEFAULT_CANDIDATES = (
    "grok-4.5",
    "grok-4.6",
    "grok-4.7",
    "claude-opus-5",
    "gpt-5.5",
    "gpt-5.6-sol",
)
KNOWN_KINDS = ("coding", "reasoning", "general", "writing")
CARD_FIELDS = ("fit", "kind", "display_name", "description")


@dataclass
class OrchestratorSettings:
    decider: str = DEFAULT_DECIDER
    fallback_model: str = DEFAULT_FALLBACK
    jev_model: str = DEFAULT_JEV_MODEL
    min_confidence: float = DEFAULT_MIN_CONFIDENCE
    steps: dict[str, str] = field(default_factory=dict)
    candidates: tuple[str, ...] = field(default_factory=tuple)
    cards: dict[str, dict] = field(default_factory=dict)


def load_settings(project: Path) -> OrchestratorSettings:
    path = project / ".pipeline" / "config.json"
    block: dict = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict) and isinstance(data.get("orchestrator"), dict):
            block = data["orchestrator"]
    name = str(block.get("decider") or DEFAULT_DECIDER).strip().lower() or DEFAULT_DECIDER
    fallback = str(block.get("fallback_model") or DEFAULT_FALLBACK).strip() or DEFAULT_FALLBACK
    jev = block.get("jev") if isinstance(block.get("jev"), dict) else {}
    jev_model = str(jev.get("model") or DEFAULT_JEV_MODEL).strip() or DEFAULT_JEV_MODEL
    try:
        minimum = float(jev.get("min_confidence", DEFAULT_MIN_CONFIDENCE))
    except (TypeError, ValueError):
        minimum = DEFAULT_MIN_CONFIDENCE
    if minimum < 0 or minimum > 1:
        minimum = DEFAULT_MIN_CONFIDENCE
    steps: dict[str, str] = {}
    models = block.get("models") if isinstance(block.get("models"), dict) else {}
    raw_steps = models.get("steps") if isinstance(models.get("steps"), dict) else {}
    for key, value in raw_steps.items():
        if isinstance(value, str) and value.strip():
            steps[str(key)] = value.strip()
        elif isinstance(value, list) and value and isinstance(value[0], str) and value[0].strip():
            steps[str(key)] = value[0].strip()
    candidates, cards = _read_candidates_and_cards(models)
    return OrchestratorSettings(
        decider=name,
        fallback_model=fallback,
        jev_model=jev_model,
        min_confidence=minimum,
        steps=steps,
        candidates=candidates,
        cards=cards,
    )


def _read_card(raw: dict) -> dict[str, str]:
    card: dict[str, str] = {}
    for key in CARD_FIELDS:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        text = value.strip()
        if key == "kind":
            text = text.lower()
            if text not in KNOWN_KINDS:
                continue
        card[key] = text
    return card


def _read_candidates_and_cards(models: dict) -> tuple[tuple[str, ...], dict[str, dict]]:
    extra: dict[str, dict] = {}
    if "candidates" not in models:
        ids: list[str] = list(DEFAULT_CANDIDATES)
    else:
        raw = models.get("candidates")
        if raw is None or raw == []:
            ids = []
        elif isinstance(raw, str) and raw.strip():
            ids = [raw.strip()]
        elif isinstance(raw, list):
            ids = []
            for item in raw:
                if isinstance(item, str) and item.strip():
                    ids.append(item.strip())
                elif isinstance(item, dict):
                    model_id = str(item.get("id") or item.get("name") or "").strip()
                    if not model_id:
                        continue
                    ids.append(model_id)
                    card = _read_card(item)
                    if card:
                        extra[model_id] = card
        else:
            ids = list(DEFAULT_CANDIDATES)
    cards = dict(extra)
    raw_cards = models.get("cards")
    if isinstance(raw_cards, dict):
        for key, value in raw_cards.items():
            model_id = str(key).strip()
            if not model_id or not isinstance(value, dict):
                continue
            card = _read_card(value)
            if not card:
                continue
            merged = dict(cards.get(model_id) or {})
            merged.update(card)
            cards[model_id] = merged
    return tuple(ids), cards


def require_known(settings: OrchestratorSettings) -> str:
    if settings.decider not in KNOWN_DECIDERS:
        known = ", ".join(KNOWN_DECIDERS)
        raise ValueError("unknown decider %r; known: %s" % (settings.decider, known))
    return settings.decider
