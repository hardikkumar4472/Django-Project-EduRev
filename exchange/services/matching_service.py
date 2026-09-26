import time
from typing import List, Dict, Any, Tuple
import networkx as nx
from django.utils import timezone
from exchange.models import ExchangeRequest, PolicyRule
from accounts.models import User

class MatchingService:
    """
    High-Performance Graph-Based Exchange Matching Engine.
    Builds directed dependency graphs and executes bounded cycle searches (lengths 2 to 5)
    using NetworkX algorithms.
    """

    @classmethod
    def get_max_chain_length(cls) -> int:
        try:
            rule = PolicyRule.objects.filter(rule_type=PolicyRule.RuleType.MAX_CHAIN_LENGTH, is_active=True).first()
            return rule.int_value if rule else 5
        except Exception:
            return 5

    @classmethod
    def find_cycles(cls, target_student_id: int = None) -> List[Dict[str, Any]]:
        """
        Discovers all valid elementary cycles of lengths 2 through max_chain_length.
        If target_student_id is specified, filters cycles to those containing target student.
        """
        start_time = time.time()
        max_chain = cls.get_max_chain_length()

        # 1. Fetch active eligible requests
        now = timezone.now()
        active_requests = list(ExchangeRequest.objects.filter(
            status=ExchangeRequest.RequestStatus.ACTIVE
        ).select_related(
            'requester',
            'current_bed__room__block__hostel',
            'preferred_hostel',
            'specific_target_room__block__hostel'
        ))

        # Filter out expired or ineligible
        valid_requests = []
        for req in active_requests:
            if req.expires_at and req.expires_at < now:
                continue
            if req.requester.has_disciplinary_hold:
                continue
            valid_requests.append(req)

        # 2. Build directed graph
        # Node key: student_id
        # Edge A -> B means A desires B's current room/bed
        G = nx.DiGraph()
        req_map: Dict[int, ExchangeRequest] = {}

        for req in valid_requests:
            s_id = req.requester_id
            req_map[s_id] = req
            G.add_node(s_id, request_id=req.id)

        # Evaluate compatibility edges
        for r_a in valid_requests:
            s_a = r_a.requester_id
            for r_b in valid_requests:
                s_b = r_b.requester_id
                if s_a == s_b:
                    continue  # No self-loops

                b_bed = r_b.current_bed
                b_room = b_bed.room
                b_hostel = b_room.block.hostel

                # Check gender policy alignment
                if r_a.requester.gender == User.Gender.MALE and b_hostel.gender_type == 'FEMALE':
                    continue
                if r_a.requester.gender == User.Gender.FEMALE and b_hostel.gender_type == 'MALE':
                    continue

                # Match criteria
                is_match = False
                reasons = []
                score = 50.0

                # Check specific room match
                if r_a.specific_target_room_id:
                    if r_a.specific_target_room_id == b_room.id:
                        is_match = True
                        score += 50.0
                        reasons.append(f"Target Room {b_room.room_number} exact match")
                else:
                    # Check preferred hostel
                    if r_a.preferred_hostel_id:
                        if r_a.preferred_hostel_id == b_hostel.id:
                            is_match = True
                            score += 25.0
                            reasons.append(f"Preferred Hostel: {b_hostel.name}")
                        else:
                            is_match = False
                    else:
                        is_match = True  # open to any hostel

                    # Check room type
                    if is_match and r_a.preferred_room_type:
                        if r_a.preferred_room_type == b_room.room_type:
                            score += 15.0
                            reasons.append(f"Preferred Room Type: {b_room.get_room_type_display()}")
                        else:
                            is_match = False

                    # Check floor
                    if is_match and r_a.preferred_floor:
                        if r_a.preferred_floor == b_room.floor:
                            score += 10.0
                            reasons.append(f"Floor {b_room.floor} match")

                if is_match:
                    G.add_edge(s_a, s_b, score=min(100.0, score), reasons=reasons)

        # 3. Find elementary cycles (bounded 2 <= length <= max_chain)
        all_cycles = list(nx.simple_cycles(G))
        discovered_cycles = []
        seen_cycle_fingerprints = set()

        for cycle_nodes in all_cycles:
            cycle_len = len(cycle_nodes)
            if cycle_len < 2 or cycle_len > max_chain:
                continue

            # Check if target student filter applied
            if target_student_id and target_student_id not in cycle_nodes:
                continue

            # Deduplicate rotational permutations (e.g. [1, 2, 3] is same cycle as [2, 3, 1])
            # Normalize cycle representation: start with minimum node ID
            min_idx = cycle_nodes.index(min(cycle_nodes))
            normalized = tuple(cycle_nodes[min_idx:] + cycle_nodes[:min_idx])
            if normalized in seen_cycle_fingerprints:
                continue
            seen_cycle_fingerprints.add(normalized)

            # Build cycle details
            participants = []
            cycle_scores = []
            total_reasons = []

            for i in range(cycle_len):
                curr_s = cycle_nodes[i]
                next_s = cycle_nodes[(i + 1) % cycle_len]
                edge_data = G.get_edge_data(curr_s, next_s) or {'score': 80.0, 'reasons': ['Mutual hostel preference']}
                cycle_scores.append(edge_data['score'])
                total_reasons.extend(edge_data['reasons'])

                r_curr = req_map[curr_s]
                r_next = req_map[next_s]
                participants.append({
                    'order': i + 1,
                    'student_id': curr_s,
                    'student_name': r_curr.requester.get_full_name(),
                    'university_id': r_curr.requester.university_id,
                    'current_bed_id': r_curr.current_bed.id,
                    'current_room': r_curr.current_bed.room.room_number,
                    'current_hostel': r_curr.current_bed.room.block.hostel.name,
                    'target_bed_id': r_next.current_bed.id,
                    'target_room': r_next.current_bed.room.room_number,
                    'target_hostel': r_next.current_bed.room.block.hostel.name,
                    'request_id': r_curr.id,
                })

            avg_score = round(sum(cycle_scores) / len(cycle_scores), 1)
            discovered_cycles.append({
                'cycle_length': cycle_len,
                'proposal_type': f"CYCLE_{cycle_len}" if cycle_len > 2 else "DIRECT",
                'type_display': f"Direct 2-Party Swap" if cycle_len == 2 else f"{cycle_len}-Party Multi-Hop Cycle",
                'compatibility_score': avg_score,
                'reasons': list(set(total_reasons))[:4],
                'participants': participants,
                'node_ids': cycle_nodes,
            })

        # Sort candidate matches by highest compatibility score, then shortest cycle length
        discovered_cycles.sort(key=lambda x: (-x['compatibility_score'], x['cycle_length']))
        elapsed_time = round(time.time() - start_time, 4)

        return discovered_cycles
