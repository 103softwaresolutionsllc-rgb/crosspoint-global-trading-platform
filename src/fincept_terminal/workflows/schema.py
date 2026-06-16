"""JSON-serializable workflow schema for the visual pipeline editor."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WorkflowNode:
    id: str
    type: str
    title: str
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def category(self) -> str:
        return self.type.split("/")[0] if "/" in self.type else self.type


@dataclass
class WorkflowConnection:
    from_node: str
    to_node: str


@dataclass
class WorkflowDefinition:
    name: str
    nodes: list[WorkflowNode]
    connections: list[WorkflowConnection] = field(default_factory=list)
    version: str = "1.0"

    @classmethod
    def from_json(cls, path: Path | str) -> WorkflowDefinition:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        nodes = [WorkflowNode(**n) for n in raw["nodes"]]
        connections = [WorkflowConnection(**c) for c in raw.get("connections", [])]
        return cls(name=raw["name"], nodes=nodes, connections=connections, version=raw.get("version", "1.0"))

    def to_json(self, path: Path | str) -> None:
        data = {
            "name": self.name,
            "version": self.version,
            "nodes": [
                {"id": n.id, "type": n.type, "title": n.title, "config": n.config} for n in self.nodes
            ],
            "connections": [
                {"from_node": c.from_node, "to_node": c.to_node} for c in self.connections
            ],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def topological_order(self) -> list[WorkflowNode]:
        """Return nodes in dependency order (sources first)."""
        node_map = {n.id: n for n in self.nodes}
        in_degree: dict[str, int] = {n.id: 0 for n in self.nodes}
        adj: dict[str, list[str]] = {n.id: [] for n in self.nodes}

        for conn in self.connections:
            if conn.from_node in adj and conn.to_node in in_degree:
                adj[conn.from_node].append(conn.to_node)
                in_degree[conn.to_node] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        ordered: list[WorkflowNode] = []
        while queue:
            nid = queue.pop(0)
            ordered.append(node_map[nid])
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return ordered if len(ordered) == len(self.nodes) else self.nodes
