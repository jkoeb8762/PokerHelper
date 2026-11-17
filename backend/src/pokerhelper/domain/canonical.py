"""Semantic canonical JSON and typed SHA-256 content identities."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping

from .cards import Card, ExactCombo
from .decimal_utils import normalized_decimal
from .errors import fail
from .game import GameConfig, GameState, ResolvedAction


_PREFIX = re.compile(r"^[a-z][a-z0-9_-]*$")


def canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        fail(
            "SCHEMA_CANONICAL_FLOAT_FORBIDDEN",
            "value",
            "Binary floating-point values cannot enter canonical serialization.",
        )
    if isinstance(value, Decimal):
        return normalized_decimal(value)
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, (Card, ExactCombo)):
        return str(value)
    if is_dataclass(value):
        return {
            field.name: canonical_value(getattr(value, field.name))
            for field in fields(value)
            if not field.name.startswith("_")
        }
    if isinstance(value, Mapping):
        return {
            str(key): canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [canonical_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        canonical_items = [canonical_value(item) for item in value]
        return sorted(canonical_items, key=_json_sort_key)
    fail(
        "SCHEMA_CANONICAL_TYPE_UNSUPPORTED",
        "value",
        "Value type is not supported by canonical serialization.",
        details={"receivedType": type(value).__name__},
    )


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def content_id(prefix: str, value: Any) -> str:
    if not _PREFIX.fullmatch(prefix):
        fail(
            "SCHEMA_ID_PREFIX_INVALID",
            "prefix",
            "Content ID prefix must be lowercase ASCII with optional digits, hyphens, or underscores.",
        )
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}:sha256:{digest}"


def game_config_payload(config: GameConfig) -> dict[str, Any]:
    return {
        "schemaVersion": config.schema_version,
        "identityProfileVersion": config.identity_profile_version,
        "variant": config.variant,
        "bettingStructure": config.betting_structure,
        "gameType": config.game_type,
        "tableSize": config.table_size,
        "positions": [
            {"position": item.position, "startingStackBb": item.starting_stack_bb}
            for item in config.positions
        ],
        "smallBlindBb": config.small_blind_bb,
        "bigBlindBb": config.big_blind_bb,
        "anteBb": config.ante_bb,
        "rakePolicy": {
            "policyVersion": config.rake_policy.policy_version,
            "rate": config.rake_policy.rate,
            "capBb": config.rake_policy.cap_bb,
            "noFlopNoDrop": config.rake_policy.no_flop_no_drop,
            "collectionRule": config.rake_policy.collection_rule,
            "roundingIncrementBb": config.rake_policy.rounding_increment_bb,
        },
    }


def game_config_id(config: GameConfig) -> str:
    return content_id("game", game_config_payload(config))


def resolved_action_payload(action: ResolvedAction) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "actor": action.actor,
        "type": action.type,
        "isAllIn": action.is_all_in,
    }
    if action.target_bb is not None:
        payload["targetBb"] = action.target_bb
    if action.raise_classification is not None:
        payload["raiseClassification"] = action.raise_classification
    return payload


def game_state_payload(state: GameState) -> dict[str, Any]:
    return {
        "schemaVersion": state.config.schema_version,
        "identityProfileVersion": state.config.identity_profile_version,
        "gameConfigId": game_config_id(state.config),
        "actionHistory": [resolved_action_payload(action) for action in state.action_history],
    }


def game_state_id(state: GameState) -> str:
    return content_id("state", game_state_payload(state))


def _json_sort_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))

