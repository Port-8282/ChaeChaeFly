"""실행 가능한 후보를 비용·대기 시간·ID 순으로 결정적으로 정렬한다."""

from schemas import EvaluatedCandidate, RankedCandidate


def rank_candidates(
    candidates: tuple[EvaluatedCandidate, ...],
) -> tuple[RankedCandidate, ...]:
    feasible = [item for item in candidates if item.constraints.feasible]
    if any(item.cost is None for item in feasible):
        raise ValueError("실행 가능한 후보의 비용이 없습니다.")
    ordered = sorted(
        feasible,
        key=lambda item: (
            item.cost.total_amount,
            sum(t.waiting_seconds for t in item.simulation.timelines),
            item.candidate.candidate_id,
        ),
    )
    return tuple(
        RankedCandidate(rank=index, evaluation=item) for index, item in enumerate(ordered, start=1)
    )
