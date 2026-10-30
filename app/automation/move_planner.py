"""Move Planner: Calculates minimal card swap sequence to transform current table cards into optimal solved hands."""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple

from app.automation.gesture_models import MoveAction, MovePlan
from app.core.card import Card
from app.core.solver import HandArrangement


class MovePlanner:
    """Plans the minimal sequence of drag-and-drop swaps between slots 1..13."""

    FRONT_SLOTS = [1, 2, 3]
    MIDDLE_SLOTS = [4, 5, 6, 7, 8]
    BACK_SLOTS = [9, 10, 11, 12, 13]

    @classmethod
    def plan_moves(
        cls,
        current_slots: Dict[int, Card],
        solution: HandArrangement,
        avg_swap_duration_sec: float = 0.75,
    ) -> MovePlan:
        """Computes the minimal swap sequence to move current cards into target Front, Middle, and Back hands."""
        if not current_slots or len(current_slots) < 13:
            return MovePlan(actions=[], total_swaps=0, estimated_duration_seconds=0.0, is_already_optimal=False)

        # 1. Target card sets for each group
        target_front = list(solution.front)
        target_middle = list(solution.middle)
        target_back = list(solution.back)

        # 2. Assign target slot for each card preserving cards already in the correct group
        # Target assignment: target_slot -> Card
        target_slots: Dict[int, Card] = {}
        unassigned_current_slots = set(range(1, 14))

        # First pass: check cards already in their correct group
        # Front
        for slot in cls.FRONT_SLOTS:
            c = current_slots.get(slot)
            if c in target_front:
                target_slots[slot] = c
                target_front.remove(c)
                unassigned_current_slots.discard(slot)

        # Middle
        for slot in cls.MIDDLE_SLOTS:
            c = current_slots.get(slot)
            if c in target_middle:
                target_slots[slot] = c
                target_middle.remove(c)
                unassigned_current_slots.discard(slot)

        # Back
        for slot in cls.BACK_SLOTS:
            c = current_slots.get(slot)
            if c in target_back:
                target_slots[slot] = c
                target_back.remove(c)
                unassigned_current_slots.discard(slot)

        # Second pass: fill remaining empty slots with remaining desired cards
        for slot in cls.FRONT_SLOTS:
            if slot not in target_slots and target_front:
                target_slots[slot] = target_front.pop(0)

        for slot in cls.MIDDLE_SLOTS:
            if slot not in target_slots and target_middle:
                target_slots[slot] = target_middle.pop(0)

        for slot in cls.BACK_SLOTS:
            if slot not in target_slots and target_back:
                target_slots[slot] = target_back.pop(0)

        # 3. Build permutation: current card at slot S needs to go to slot D
        # where target_slots[D] == current_slots[S]
        current_to_target_slot: Dict[int, int] = {}
        matched_target_slots: Set[int] = set()

        for curr_slot, curr_card in current_slots.items():
            for tgt_slot, tgt_card in target_slots.items():
                if tgt_slot not in matched_target_slots and curr_card == tgt_card:
                    current_to_target_slot[curr_slot] = tgt_slot
                    matched_target_slots.add(tgt_slot)
                    break

        # 4. Decompose permutation into minimal swap cycles
        # We simulate the state of cards at slots
        virtual_slots = dict(current_slots)
        actions: List[MoveAction] = []

        # Continue swapping until all slots hold their target card
        visited_in_round: Set[int] = set()
        for start_slot in range(1, 14):
            if start_slot in visited_in_round:
                continue

            # Trace cycle
            cycle: List[int] = []
            curr = start_slot
            while curr not in cycle:
                dest = current_to_target_slot.get(curr, curr)
                if dest == curr:
                    break
                cycle.append(curr)
                curr = dest

            for s in cycle:
                visited_in_round.add(s)

            # A cycle of length K (e.g. [s1, s2, s3]) can be resolved by K-1 swaps:
            # swap(s1, s2), then swap(s1, s3), ...
            if len(cycle) > 1:
                base_slot = cycle[0]
                for next_slot in cycle[1:]:
                    card_a = virtual_slots.get(base_slot)
                    card_b = virtual_slots.get(next_slot)

                    actions.append(
                        MoveAction(
                            source_slot=base_slot,
                            target_slot=next_slot,
                            card_source=card_a,
                            card_target=card_b,
                            description=f"Hoán đổi ô {base_slot} ({card_a}) ⟷ ô {next_slot} ({card_b})",
                        )
                    )
                    # Perform virtual swap
                    virtual_slots[base_slot], virtual_slots[next_slot] = virtual_slots[next_slot], virtual_slots[base_slot]

        is_optimal = len(actions) == 0
        total_swaps = len(actions)
        est_duration = total_swaps * avg_swap_duration_sec

        return MovePlan(
            actions=actions,
            total_swaps=total_swaps,
            estimated_duration_seconds=round(est_duration, 1),
            is_already_optimal=is_optimal,
        )
