"use client";

import { useEffect, useRef, useCallback } from "react";
import * as d3 from "d3";
import type { GraphNode, GraphEdge } from "@/types/api";

const TYPE_COLORS: Record<string, string> = {
  Person: "#3b82f6",
  Project: "#10b981",
  Topic: "#f59e0b",
  Decision: "#ef4444",
  Document: "#8b5cf6",
  Entity: "#6b7280",
};

interface ForceGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (nodeId: string) => void;
  width?: number;
  height?: number;
}

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  type: string;
  name: string;
  size: number;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  relation: string;
  weight: number;
}

export function ForceGraph({
  nodes,
  edges,
  onNodeClick,
  width = 800,
  height = 600,
}: ForceGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);

  const getColor = useCallback((type: string) => TYPE_COLORS[type] ?? "#6b7280", []);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const simNodes: SimNode[] = nodes.map((n) => ({ ...n }));
    const nodeIndex = new Map(simNodes.map((n) => [n.id, n]));

    const simLinks: SimLink[] = edges
      .filter((e) => nodeIndex.has(e.source) && nodeIndex.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        relation: e.relation,
        weight: e.weight,
      }));

    const simulation = d3
      .forceSimulation<SimNode>(simNodes)
      .force(
        "link",
        d3
          .forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance(80),
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30));

    simulationRef.current = simulation;

    const g = svg.append("g");

    // Zoom
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 4])
      .on("zoom", (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
        g.attr("transform", event.transform.toString());
      });
    svg.call(zoom);

    // Links
    const link = g
      .append("g")
      .attr("stroke", "#d1d5db")
      .attr("stroke-opacity", 0.8)
      .selectAll("line")
      .data(simLinks)
      .join("line")
      .attr("stroke-width", (d: SimLink) => Math.max(1, d.weight * 2));

    // Link labels
    const linkLabel = g
      .append("g")
      .selectAll("text")
      .data(simLinks)
      .join("text")
      .attr("font-size", 9)
      .attr("fill", "#9ca3af")
      .attr("text-anchor", "middle")
      .text((d: SimLink) => d.relation);

    // Nodes
    const node = g
      .append("g")
      .selectAll<SVGCircleElement, SimNode>("circle")
      .data(simNodes)
      .join("circle")
      .attr("r", (d: SimNode) => Math.max(8, Math.min(24, d.size * 3)))
      .attr("fill", (d: SimNode) => getColor(d.type))
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .attr("cursor", "pointer")
      .on("click", (_event: MouseEvent, d: SimNode) => {
        onNodeClick?.(d.id);
      });

    // Drag behavior
    const drag = d3.drag<SVGCircleElement, SimNode>()
      .on("start", (event: d3.D3DragEvent<SVGCircleElement, SimNode, SimNode>) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      })
      .on("drag", (event: d3.D3DragEvent<SVGCircleElement, SimNode, SimNode>) => {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      })
      .on("end", (event: d3.D3DragEvent<SVGCircleElement, SimNode, SimNode>) => {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      });
    node.call(drag);

    // Labels
    const label = g
      .append("g")
      .selectAll("text")
      .data(simNodes)
      .join("text")
      .attr("font-size", 11)
      .attr("font-weight", "500")
      .attr("fill", "#1f2937")
      .attr("text-anchor", "middle")
      .attr("dy", (d: SimNode) => -(Math.max(8, Math.min(24, d.size * 3)) + 6))
      .text((d: SimNode) => d.name);

    // Tooltip on hover
    node.append("title").text((d: SimNode) => `${d.name} (${d.type})`);

    simulation.on("tick", () => {
      link
        .attr("x1", (d: SimLink) => (d.source as SimNode).x!)
        .attr("y1", (d: SimLink) => (d.source as SimNode).y!)
        .attr("x2", (d: SimLink) => (d.target as SimNode).x!)
        .attr("y2", (d: SimLink) => (d.target as SimNode).y!);

      linkLabel
        .attr("x", (d: SimLink) => ((d.source as SimNode).x! + (d.target as SimNode).x!) / 2)
        .attr("y", (d: SimLink) => ((d.source as SimNode).y! + (d.target as SimNode).y!) / 2);

      node.attr("cx", (d: SimNode) => d.x!).attr("cy", (d: SimNode) => d.y!);

      label.attr("x", (d: SimNode) => d.x!).attr("y", (d: SimNode) => d.y!);
    });

    return () => {
      simulation.stop();
    };
  }, [nodes, edges, width, height, onNodeClick, getColor]);

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      className="border border-border rounded-lg bg-surface"
      role="img"
      aria-label="Knowledge-Graph-Visualisierung"
    />
  );
}

// Legend component
export function GraphLegend() {
  return (
    <div className="flex flex-wrap gap-3 text-sm">
      {Object.entries(TYPE_COLORS).map(([type, color]) => (
        <div key={type} className="flex items-center gap-1.5">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: color }}
          />
          <span className="text-text-secondary">{type}</span>
        </div>
      ))}
    </div>
  );
}
