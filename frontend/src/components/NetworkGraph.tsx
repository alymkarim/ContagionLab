import { useEffect, useRef, useCallback } from "react";
import type { NetworkResponse } from "../api/client";

interface Props {
  data: NetworkResponse;
}

interface SimNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  importance: number;
  community: string;
  color: string;
  radius: number;
}

const COMMUNITY_COLORS = [
  "#3b82f6",
  "#ef4444",
  "#10b981",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#f97316",
  "#84cc16",
  "#6366f1",
];

function assignColors(
  assignment: Record<string, number>,
): Map<string, string> {
  const map = new Map<string, string>();
  Object.entries(assignment).forEach(([node, comm]) => {
    const color = COMMUNITY_COLORS[(comm as number) % COMMUNITY_COLORS.length];
    map.set(node, color);
  });
  return map;
}

function percentileRank(values: number[], target: number): number {
  const sorted = [...values].sort((a, b) => a - b);
  let count = 0;
  for (const v of sorted) {
    if (v <= target) count++;
  }
  return count / sorted.length;
}

export default function NetworkGraph({ data }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const rafRef = useRef<number>(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = container.clientWidth;
    const height = Math.max(400, Math.min(500, width * 0.65));
    canvas.width = width;
    canvas.height = height;

    const { graph, metrics } = data;
    const colorMap = assignColors(metrics.communities.assignment);
    const importanceValues = Object.values(metrics.systemic_importance);

    const nodes: SimNode[] = graph.nodes.map((n) => {
      const importance = metrics.systemic_importance[n.id] ?? 0;
      const pct = percentileRank(importanceValues, importance);
      return {
        id: n.id,
        x: width / 2 + (Math.random() - 0.5) * width * 0.5,
        y: height / 2 + (Math.random() - 0.5) * height * 0.4,
        vx: 0,
        vy: 0,
        importance,
        community: "",
        color: colorMap.get(n.id) ?? "#9ca3af",
        radius: 8 + pct * 16,
      };
    });

    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    const edges = graph.edges
      .map((e) => {
        const s = nodeMap.get(e.source);
        const t = nodeMap.get(e.target);
        if (!s || !t) return null;
        return { source: s, target: t, weight: e.weight };
      })
      .filter(Boolean) as { source: SimNode; target: SimNode; weight: number }[];

    nodesRef.current = nodes;

    const repulsion = 800;
    const attraction = 0.005;
    const damping = 0.92;
    const centerGravity = 0.01;
    let running = true;

    function tick() {
      if (!ctx) return;

      for (const n of nodes) {
        n.vx = 0;
        n.vy = 0;
      }

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = repulsion / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          a.vx -= fx;
          a.vy -= fy;
          b.vx += fx;
          b.vy += fy;
        }
      }

      for (const e of edges) {
        const dx = e.target.x - e.source.x;
        const dy = e.target.y - e.source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist * attraction * Math.abs(e.weight);
        e.source.vx += (dx / dist) * force;
        e.source.vy += (dy / dist) * force;
        e.target.vx -= (dx / dist) * force;
        e.target.vy -= (dy / dist) * force;
      }

      for (const n of nodes) {
        n.vx += (width / 2 - n.x) * centerGravity;
        n.vy += (height / 2 - n.y) * centerGravity;
        n.vx *= damping;
        n.vy *= damping;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(n.radius, Math.min(width - n.radius, n.x));
        n.y = Math.max(n.radius, Math.min(height - n.radius, n.y));
      }

      ctx.fillStyle = "#111827";
      ctx.fillRect(0, 0, width, height);

      for (const e of edges) {
        ctx.beginPath();
        ctx.moveTo(e.source.x, e.source.y);
        ctx.lineTo(e.target.x, e.target.y);
        ctx.strokeStyle = `rgba(156, 163, 175, ${Math.min(0.8, Math.abs(e.weight))})`;
        ctx.lineWidth = 1 + Math.abs(e.weight) * 2;
        ctx.stroke();
      }

      for (const n of nodes) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();
        ctx.strokeStyle = "#1f2937";
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = "#f3f4f6";
        ctx.font = "11px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(n.id, n.x, n.y);
      }

      if (running) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    tick();

    return () => {
      running = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, [data]);

  useEffect(() => {
    const cleanup = draw();
    return cleanup;
  }, [draw]);

  return (
    <div ref={containerRef} className="w-full">
      <canvas
        ref={canvasRef}
        className="rounded border border-gray-700 w-full"
        style={{ height: 450 }}
      />
    </div>
  );
}
