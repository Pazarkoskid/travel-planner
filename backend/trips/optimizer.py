import logging

logger = logging.getLogger(__name__)


def route_cost(order, minutes, start=0):
    total, prev = 0.0, start
    for i in order:
        total += minutes[prev][i]
        prev = i
    return total


def _nearest_neighbour(minutes, nodes, start=0):
    remaining, order, cur = set(nodes), [], start
    while remaining:
        nxt = min(remaining, key=lambda j: minutes[cur][j])
        order.append(nxt)
        remaining.remove(nxt)
        cur = nxt
    improved = True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for k in range(i + 1, len(order)):
                cand = order[:i] + order[i:k + 1][::-1] + order[k + 1:]
                if route_cost(cand, minutes, start) + 1e-9 < route_cost(order, minutes, start):
                    order, improved = cand, True
    return order


def optimize_order(minutes, time_limit_s=0.3):
    n = len(minutes) - 1
    nodes = list(range(1, n + 1))
    if n <= 2:
        return _nearest_neighbour(minutes, nodes)
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        logger.warning("OR-Tools not installed; using heuristic")
        return _nearest_neighbour(minutes, nodes)

    size = n + 2
    scaled = [[0] * size for _ in range(size)]
    for i in range(n + 1):
        for j in range(n + 1):
            scaled[i][j] = int(round(minutes[i][j] * 100))
    manager = pywrapcp.RoutingIndexManager(size, 1, [0], [n + 1])
    routing = pywrapcp.RoutingModel(manager)

    def cb(a, b):
        return scaled[manager.IndexToNode(a)][manager.IndexToNode(b)]

    transit = routing.RegisterTransitCallback(cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromMilliseconds(int(time_limit_s * 1000))
    solution = routing.SolveWithParameters(params)
    if not solution:
        return _nearest_neighbour(minutes, nodes)
    order, idx = [], routing.Start(0)
    while not routing.IsEnd(idx):
        node = manager.IndexToNode(idx)
        if 1 <= node <= n:
            order.append(node)
        idx = solution.Value(routing.NextVar(idx))
    heuristic = _nearest_neighbour(minutes, nodes)
    return order if route_cost(order, minutes) <= route_cost(heuristic, minutes) else heuristic
