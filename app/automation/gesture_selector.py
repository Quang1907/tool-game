"""Smart Gesture Selector with weighted random sampling, repeat avoidance, and natural Bézier generation."""

from __future__ import annotations
import math
import random
from typing import Dict, List, Optional, Tuple

from app.automation.gesture_models import GestureConfig, GesturePoint, GestureSample


class GestureSelector:
    """Selects or generates drag gestures for any of the 156 directed slot pairs."""

    def __init__(self, recent_history_size: int = 5) -> None:
        self.recent_history_size = recent_history_size
        self._recent_sample_ids: List[str] = []

    def record_used_sample(self, sample_id: str) -> None:
        """Records a sample ID to avoid consecutive identical repetitions."""
        self._recent_sample_ids.append(sample_id)
        if len(self._recent_sample_ids) > self.recent_history_size:
            self._recent_sample_ids.pop(0)

    def select_gesture(
        self,
        source_slot: int,
        target_slot: int,
        available_samples: List[GestureSample],
        config: GestureConfig,
        source_coords: Optional[Tuple[float, float]] = None,
        target_coords: Optional[Tuple[float, float]] = None,
    ) -> GestureSample:
        """Selects the best or randomized gesture for the directed pair (source_slot -> target_slot).
        If no samples exist, procedurally generates a natural human-like Bézier gesture.
        """
        # Filter samples for this exact pair
        pair_samples = [s for s in available_samples if s.source_slot == source_slot and s.target_slot == target_slot]

        # Filter verified if requested
        if config.verified_only:
            verified_samples = [s for s in pair_samples if s.is_verified]
            if verified_samples:
                pair_samples = verified_samples

        # If samples exist, apply selection logic
        if pair_samples:
            if not config.random_enabled:
                # Return the highest weight or first verified sample
                pair_samples.sort(key=lambda s: (s.is_verified, s.weight), reverse=True)
                chosen = pair_samples[0]
                self.record_used_sample(chosen.id)
                return chosen

            # If avoiding consecutive repeats and more than 1 candidate exists
            candidates = pair_samples
            if config.avoid_consecutive_repeats and len(pair_samples) > 1:
                non_recent = [s for s in pair_samples if s.id not in self._recent_sample_ids]
                if non_recent:
                    candidates = non_recent

            # Weighted random selection
            weights = [max(0.1, s.weight) for s in candidates]
            chosen = random.choices(candidates, weights=weights, k=1)[0]
            self.record_used_sample(chosen.id)
            return chosen

        # Fallback: Procedural natural Bézier trajectory
        start_x, start_y = source_coords if source_coords else (0.3, 0.3)
        end_x, end_y = target_coords if target_coords else (0.7, 0.7)
        return self.generate_natural_bezier_sample(
            source_slot=source_slot,
            target_slot=target_slot,
            start_coord=(start_x, start_y),
            end_coord=(end_x, end_y),
        )

    @classmethod
    def generate_natural_bezier_sample(
        cls,
        source_slot: int,
        target_slot: int,
        start_coord: Tuple[float, float],
        end_coord: Tuple[float, float],
        num_points: int = 24,
        base_duration_ms: int = 350,
        is_verified: bool = True,
    ) -> GestureSample:
        """Generates a smooth, human-like cubic Bézier drag trajectory between two relative coordinates."""
        x0, y0 = start_coord
        x3, y3 = end_coord

        dx = x3 - x0
        dy = y3 - y0
        dist = math.hypot(dx, dy)

        # Scale duration with distance (closer = faster, farther = slightly longer)
        duration_ms = max(240, min(550, int(base_duration_ms * (0.8 + 0.4 * (dist / 0.5)))))

        # Compute perpendicular vector for natural human curved arc
        perp_x = -dy
        perp_y = dx
        norm = math.hypot(perp_x, perp_y)
        if norm > 1e-6:
            perp_x /= norm
            perp_y /= norm
        else:
            perp_x, perp_y = 0.0, 0.0

        # Randomize curvature direction and amplitude (subtle arc of 2% to 6% of distance)
        curve_factor = random.uniform(-0.08, 0.08) * dist

        # Two intermediate cubic Bézier control points
        x1 = x0 + dx * 0.33 + perp_x * curve_factor + random.uniform(-0.008, 0.008)
        y1 = y0 + dy * 0.33 + perp_y * curve_factor + random.uniform(-0.008, 0.008)

        x2 = x0 + dx * 0.67 + perp_x * (curve_factor * 0.8) + random.uniform(-0.008, 0.008)
        y2 = y0 + dy * 0.67 + perp_y * (curve_factor * 0.8) + random.uniform(-0.008, 0.008)

        points: List[GesturePoint] = []
        for i in range(num_points):
            t = i / float(num_points - 1)

            # Ease-in-out timing profile (smoother acceleration and deceleration)
            # Cubic ease-in-out formula
            if t < 0.5:
                ease_t = 4.0 * t * t * t
            else:
                f = (2.0 * t) - 2.0
                ease_t = 0.5 * f * f * f + 1.0
            ease_t = max(0.0, min(1.0, ease_t))

            # Cubic Bézier formula: B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
            omt = 1.0 - ease_t
            px = (omt ** 3) * x0 + 3 * (omt ** 2) * ease_t * x1 + 3 * omt * (ease_t ** 2) * x2 + (ease_t ** 3) * x3
            py = (omt ** 3) * y0 + 3 * (omt ** 2) * ease_t * y1 + 3 * omt * (ease_t ** 2) * y2 + (ease_t ** 3) * y3

            # Add tiny microscopic human micro-tremor (except start and end)
            if 0 < i < num_points - 1:
                px += random.uniform(-0.0015, 0.0015)
                py += random.uniform(-0.0015, 0.0015)

            time_ms = int(ease_t * duration_ms)
            points.append(GesturePoint(rel_x=round(px, 5), rel_y=round(py, 5), time_ms=time_ms))

        name = f"Bézier Tự nhiên #{random.randint(100, 999)}"
        return GestureSample.create_new(
            source_slot=source_slot,
            target_slot=target_slot,
            name=name,
            points=points,
            mouse_down_delay_ms=random.randint(65, 95),
            mouse_up_delay_ms=random.randint(65, 95),
            total_duration_ms=duration_ms,
            is_verified=is_verified,
            weight=1.0,
            metadata={"generator": "procedural_bezier", "curve_factor": round(curve_factor, 4)},
        )
