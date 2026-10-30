"""Domain models and data structures for Card Slots, Mouse Gestures, and Auto-Binh Moves."""

from __future__ import annotations
from dataclasses import dataclass, field
import datetime
import json
from typing import Any, Dict, List, Optional
import uuid

from app.core.card import Card


@dataclass
class CardSlot:
    """Represents one of the 13 designated card slots on the game table.
    Coordinates are normalized [0.0, 1.0] relative to the game window bounds.
    """
    slot_number: int            # 1 to 13
    name: str                   # e.g. "Chi Đầu 1", "Chi Giữa 3"
    rel_x: float                # 0.0 to 1.0
    rel_y: float                # 0.0 to 1.0
    group_name: str             # "front", "middle", "back"
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_number": self.slot_number,
            "name": self.name,
            "rel_x": self.rel_x,
            "rel_y": self.rel_y,
            "group_name": self.group_name,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CardSlot:
        return cls(
            slot_number=int(data["slot_number"]),
            name=str(data["name"]),
            rel_x=float(data["rel_x"]),
            rel_y=float(data["rel_y"]),
            group_name=str(data.get("group_name", "front")),
            updated_at=str(data.get("updated_at", datetime.datetime.now().isoformat())),
        )


@dataclass
class GesturePoint:
    """A single waypoint along a mouse trajectory."""
    rel_x: float                # Relative to game window [0.0, 1.0]
    rel_y: float                # Relative to game window [0.0, 1.0]
    time_ms: int                # Offset in milliseconds from trajectory start

    def to_dict(self) -> Dict[str, Any]:
        return {"rel_x": round(self.rel_x, 5), "rel_y": round(self.rel_y, 5), "time_ms": self.time_ms}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GesturePoint:
        return cls(
            rel_x=float(data["rel_x"]),
            rel_y=float(data["rel_y"]),
            time_ms=int(data["time_ms"]),
        )


@dataclass
class GestureSample:
    """A recorded or procedurally generated mouse trajectory between source and target slots."""
    id: str
    source_slot: int            # 1 to 13
    target_slot: int            # 1 to 13 (source != target)
    name: str                   # Human-readable sample name
    points: List[GesturePoint]
    mouse_down_delay_ms: int = 80
    mouse_up_delay_ms: int = 80
    total_duration_ms: int = 350
    is_verified: bool = False
    weight: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_new(
        cls,
        source_slot: int,
        target_slot: int,
        name: str,
        points: List[GesturePoint],
        mouse_down_delay_ms: int = 80,
        mouse_up_delay_ms: int = 80,
        total_duration_ms: int = 350,
        is_verified: bool = False,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GestureSample:
        return cls(
            id=str(uuid.uuid4()),
            source_slot=source_slot,
            target_slot=target_slot,
            name=name,
            points=points,
            mouse_down_delay_ms=mouse_down_delay_ms,
            mouse_up_delay_ms=mouse_up_delay_ms,
            total_duration_ms=total_duration_ms,
            is_verified=is_verified,
            weight=weight,
            created_at=datetime.datetime.now().isoformat(),
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_slot": self.source_slot,
            "target_slot": self.target_slot,
            "name": self.name,
            "points": [p.to_dict() for p in self.points],
            "mouse_down_delay_ms": self.mouse_down_delay_ms,
            "mouse_up_delay_ms": self.mouse_up_delay_ms,
            "total_duration_ms": self.total_duration_ms,
            "is_verified": self.is_verified,
            "weight": self.weight,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GestureSample:
        points = [GesturePoint.from_dict(p) for p in data.get("points", [])]
        return cls(
            id=str(data["id"]),
            source_slot=int(data["source_slot"]),
            target_slot=int(data["target_slot"]),
            name=str(data["name"]),
            points=points,
            mouse_down_delay_ms=int(data.get("mouse_down_delay_ms", 80)),
            mouse_up_delay_ms=int(data.get("mouse_up_delay_ms", 80)),
            total_duration_ms=int(data.get("total_duration_ms", 350)),
            is_verified=bool(data.get("is_verified", False)),
            weight=float(data.get("weight", 1.0)),
            created_at=str(data.get("created_at", datetime.datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MoveAction:
    """A single card swap/move action between two slots."""
    source_slot: int
    target_slot: int
    card_source: Optional[Card] = None
    card_target: Optional[Card] = None
    description: str = ""


@dataclass
class MovePlan:
    """A complete sequence of card swap actions to arrange 13 cards into the optimal layout."""
    actions: List[MoveAction]
    total_swaps: int
    estimated_duration_seconds: float
    is_already_optimal: bool = False


@dataclass
class GestureConfig:
    """Global configuration for gesture selection and auto-binh execution."""
    random_enabled: bool = True
    verified_only: bool = False
    avoid_consecutive_repeats: bool = True
    inter_move_delay_ms: int = 350  # Delay between consecutive drag actions
    speed_factor: float = 1.0       # Speed multiplier (0.5 = 2x faster, 1.5 = slower)
