from dataclasses import dataclass

import networkx as nx
import pydot
from dowhy import CausalModel


@dataclass
class CausalModelBuildResult:
    graph: nx.DiGraph
    model: CausalModel


def dot_to_networkx(dot_code: str) -> nx.DiGraph:
    graphs = pydot.graph_from_dot_data(dot_code)
    if not graphs:
        raise ValueError("No se pudo interpretar el codigo DOT.")

    pydot_graph = graphs[0]
    nx_graph = nx.DiGraph()

    for node in pydot_graph.get_nodes():
        name = node.get_name().strip('"')
        if name in ("node",):
            continue
        nx_graph.add_node(name, **node.get_attributes())

    for edge in pydot_graph.get_edges():
        src = edge.get_source().strip('"')
        tgt = edge.get_destination().strip('"')
        nx_graph.add_edge(src, tgt)

    return nx_graph


def build_causal_model_from_dot(
    df,
    treatment_col: str,
    outcome_col: str,
    dot_code: str,
) -> CausalModelBuildResult:
    graph = dot_to_networkx(dot_code)
    model = CausalModel(
        data=df,
        treatment=treatment_col,
        outcome=outcome_col,
        graph=graph,
    )
    return CausalModelBuildResult(graph=graph, model=model)
