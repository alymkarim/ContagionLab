import { useEffect, useRef } from "react";
import type { NetworkResponse } from "../api/client";

interface Props {
  data: NetworkResponse;
}

interface SimNode {
  id: string;
  x: number;
  y: number;
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
];

export default function MiniNetworkGraph({ data }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = 220;
    const height = 160;
    canvas.width = width;
    canvas.height = height;

    const { graph, metrics } = data;

    const colorMap = new Map<string, string>();
    Object.entries(metrics.communities.assignment).forEach(([node, comm]) => {
      colorMap.set(
        node,
        COMMUNITY_COLORS[(comm as number) % COMMUNITY_COLORS.length],
      );
    });

    const importanceValues = Object.values(metrics.systemic_importance);
    const maxImportance = Math.max(...importanceValues, 0.01);

    const nodes: SimNode[] = graph.nodes.map((n) => {
      const importance = metrics.systemic_importance[n.id] ?? 0;
      return {
        id: n.id,
        x: width / 2 + (Math.random() - 0.5) * 120,
        y: height / 2 + (Math.random() - 0.5) * 80,
        color: colorMap.get(n.id) ?? "#9ca3af",
        radius: 4 + (importance / maxImportance) * 6,
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

    const repulsion = 400;
    const attraction = 0.008;
    const damping = 0.9;
    const centerGravity = 0.02;
    let running = true;
    let ticks = 0;

    function tick() {
      if (!ctx) return;

      for (const n of nodes) {
        let vx = 0;
        let vy = 0;

        for (const other of nodes) {
          if (other === n) continue;
          let dx = other.x - n.x;
          let dy = other.y - n.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = repulsion / (dist * dist);
          vx -= (dx / dist) * force;
          vy -= (dy / dist) * force;
        }

        for (const e of edges) {
          if (e.source === n) {
            const dx = e.target.x - n.x;
            const dy = e.target.y - n.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = dist * attraction * Math.abs(e.weight);
            vx += (dx / dist) * force;
            vy += (dy / dist) * force;
          } else if (e.target === n) {
            const dx = e.source.x - n.x;
            const dy = e.source.y - n.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = dist * attraction * Math.abs(e.weight);
            vx += (dx / dist) * force;
            vy += (dy / dist) * force;
          }
        }

        vx += (width / 2 - n.x) * centerGravity;
        vy += (height / 2 - n.y) * centerGravity;
        n.x += vx * damping;
        n.y += vy * damping;
        n.x = Math.max(n.radius, Math.min(width - n.radius, n.x));
        n.y = Math.max(n.radius, Math.min(height - n.radius, n.y));
      }

      ctx.fillStyle = "#111827";
      ctx.fillRect(0, 0, width, height);

      for (const e of edges) {
        ctx.beginPath();
        ctx.moveTo(e.source.x, e.source.y);
        ctx.lineTo(e.target.x, e.target.y);
        ctx.strokeStyle = `rgba(156, 163, 175, ${Math.min(0.6, Math.abs(e.weight))})`;
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }

      for (const n of nodes) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();
        ctx.strokeStyle = "#1f2937";
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.fillStyle = "#f3f4f6";
        ctx.font = "8px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(n.id, n.x, n.y);
      }

      ticks++;
      if (running && ticks < 120) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    tick();

    return () => {
      running = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, [data]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full"
      style={{ width: "100%", height: 160 }}
    />
  );
}
