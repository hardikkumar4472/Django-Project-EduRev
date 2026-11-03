import time
from typing import List, Dict, Any, Tuple
from django.utils import timezone
from exchange.models import ExchangeRequest, PolicyRule
from accounts.models import User

try:
    import networkx as nx
except ImportError:
    nx = None

def _simple_cycles_dfs(adj: Dict[int, List[int]], max_len: int) -> List[List[int]]:
    """Pure-Python elementary cycle discovery bounded up to max_len (2 to 5)."""
    cycles = []
    nodes = sorted(adj.keys())

    for start_node in nodes:
        stack = [(start_node, [start_node], {start_node})]
        while stack:
            curr, path, visited = stack.pop()
            for neighbor in adj.get(curr, []):
                if neighbor == start_node:
                    if len(path) >= 2:
                        cycles.append(list(path))
                elif neighbor not in visited and len(path) < max_len and neighbor > start_node:
                    stack.append((neighbor, path + [neighbor], visited | {neighbor}))
    return cycles

class MatchingService:
    """
    High-Performance Graph-Based Exchange Matching Engine.
    Builds directed dependency graphs and executes bounded cycle searches (lengths 2 to 5).
    Uses NetworkX when available, falling back smoothly to pure-Python DFS algorithm.
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
        adj: Dict[int, List[int]] = {r.requester_id: [] for r in valid_requests}
        edge_data: Dict[Tuple[int, int], Dict[str, Any]] = {}
        req_map: Dict[int, ExchangeRequest] = {r.requester_id: r for r in valid_requests}

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

                # Check gender policy alignment - strict gender residency separation
                if r_a.requester.gender != r_b.requester.gender:
                    continue
                if r_a.requester.gender == User.Gender.MALE and b_hostel.gender_type != 'MALE':
                    continue
                if r_a.requester.gender == User.Gender.FEMALE and b_hostel.gender_type != 'FEMALE':
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
                    adj[s_a].append(s_b)
                    edge_data[(s_a, s_b)] = {
                        'score': min(100.0, score),
                        'reasons': reasons
                    }

        # 3. Find elementary cycles (bounded 2 <= length <= max_chain)
        if nx is not None:
            G = nx.DiGraph()
            for n in adj:
                G.add_node(n)
            for (u, v), d in edge_data.items():
                G.add_edge(u, v, **d)
            all_cycles = list(nx.simple_cycles(G, length_bound=max_chain))
        else:
            all_cycles = _simple_cycles_dfs(adj, max_chain)

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
            min_idx = cycle_nodes.index(min(cycle_nodes))
            norm_cycle = tuple(cycle_nodes[min_idx:] + cycle_nodes[:min_idx])
            if norm_cycle in seen_cycle_fingerprints:
                continue
            seen_cycle_fingerprints.add(norm_cycle)

            # Build transition hops
            hops = []
            cycle_scores = []
            is_valid_cycle = True

            for i in range(cycle_len):
                from_id = cycle_nodes[i]
                to_id = cycle_nodes[(i + 1) % cycle_len]

                e_info = edge_data.get((from_id, to_id), {})
                if not e_info and nx is not None:
                    # fallback to nx graph lookup
                    pass

                r_from = req_map.get(from_id)
                r_to = req_map.get(to_id)
                if not r_from or not r_to:
                    is_valid_cycle = False
                    break

                edge_score = e_info.get('score', 75.0)
                edge_reasons = e_info.get('reasons', [])
                cycle_scores.append(edge_score)

                hops.append({
                    'step': i + 1,
                    'giver': {
                        'student_id': r_from.requester.id,
                        'name': r_from.requester.get_full_name() or r_from.requester.username,
                        'university_id': r_from.requester.university_id,
                        'current_room': r_from.current_bed.room.room_number,
                        'current_block': r_from.current_bed.room.block.name,
                        'current_hostel': r_from.current_bed.room.block.hostel.name,
                        'current_hostel_code': r_from.current_bed.room.block.hostel.code,
                        'bed_number': r_from.current_bed.bed_number,
                    },
                    'receiver': {
                        'student_id': r_to.requester.id,
                        'name': r_to.requester.get_full_name() or r_to.requester.username,
                        'university_id': r_to.requester.university_id,
                    },
                    'assigned_bed_id': r_to.current_bed_id,
                    'score': edge_score,
                    'reasons': edge_reasons,
                })

            if not is_valid_cycle:
                continue

            avg_score = round(sum(cycle_scores) / len(cycle_scores), 1) if cycle_scores else 0.0

            # Determine cycle typology
            if cycle_len == 2:
                cycle_type_label = "Direct 2-Party Swap"
            elif cycle_len == 3:
                cycle_type_label = "3-Party Cyclic Rotation"
            elif cycle_len == 4:
                cycle_type_label = "4-Party Quad Loop"
            else:
                cycle_type_label = f"{cycle_len}-Party Multi-Hop Chain"

            discovered_cycles.append({
                'cycle_length': cycle_len,
                'cycle_type': cycle_type_label,
                'student_ids': list(norm_cycle),
                'score': avg_score,
                'hops': hops,
                'involved_hostels': list(set(
                    h['giver']['current_hostel_code'] for h in hops
                )),
                'is_cross_hostel': len(set(h['giver']['current_hostel_code'] for h in hops)) > 1,
            })

        # Sort: highest score first, then shorter cycle length
        discovered_cycles.sort(key=lambda c: (-c['score'], c['cycle_length']))

        return discovered_cycles
