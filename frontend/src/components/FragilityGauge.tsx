import { useEffect, useRef } from "react";
import type { FragilityResponse } from "../api/client";

interface Props {
  data: FragilityResponse;
}

function scoreColor(score: number): string {
  if (score > 0.7) return "#ef4444";
  if (score > 0.4) return "#f59e0b";
  return "#10b981";
}

function regimeLabel(regime: string): string {
  switch (regime.toLowerCase()) {
    case "resilient":
      return "Resilient";
    case "stressed":
      return "Stressed";
    default:
      return "Normal";
  }
}

function trendIcon(trend: string): string {
  switch (trend.toLowerCase()) {
    case "increasing":
      return "\u2191";
    case "decreasing":
      return "\u2193";
    default:
      return "\u2192";
  }
}

function trendColor(trend: string): string {
  switch (trend.toLowerCase()) {
    case "increasing":
      return "text-red-400";
    case "decreasing":
      return "text-green-400";
    default:
      return "text-gray-400";
  }
}

export default function FragilityGauge({ data }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { summary, history } = data;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || history.length < 2) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = 300;
    const height = 60;
    canvas.width = width;
    canvas.height = height;

    ctx.fillStyle = "#111827";
    ctx.fillRect(0, 0, width, height);

    const values = history.map((h) => h.fragility);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = Math.max(max - min, 0.01);
    const pad = 4;

    const points = values.map((v, i) => ({
      x: pad + (i / (values.length - 1)) * (width - 2 * pad),
      y: pad + (1 - (v - min) / range) * (height - 2 * pad),
    }));

    const color = scoreColor(summary.current_fragility);

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      const prev = points[i - 1];
      const curr = points[i];
      const cpx = (prev.x + curr.x) / 2;
      ctx.bezierCurveTo(cpx, prev.y, cpx, curr.y, curr.x, curr.y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();

    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, color + "30");
    gradient.addColorStop(1, color + "00");
    ctx.lineTo(points[points.length - 1].x, height);
    ctx.lineTo(points[0].x, height);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
  }, [data]);

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-5">
      <h3 className="text-sm font-medium text-gray-300 mb-4">
        Fragility Index
      </h3>

      <div className="flex items-center gap-6 mb-4">
        <div>
          <div
            className="text-4xl font-bold font-mono"
            style={{ color: scoreColor(summary.current_fragility) }}
          >
            {(summary.current_fragility * 100).toFixed(0)}
          </div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wider mt-1">
            Current Score
          </div>
        </div>

        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-600 uppercase tracking-wider w-16">
              Regime
            </span>
            <span className="text-sm text-gray-300 font-medium">
              {regimeLabel(summary.regime)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-600 uppercase tracking-wider w-16">
              Trend
            </span>
            <span className={`text-sm font-medium ${trendColor(summary.trend)}`}>
              {trendIcon(summary.trend)} {summary.trend}
            </span>
          </div>
        </div>
      </div>

      {history.length > 1 && (
        <div>
          <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5">
            History
          </div>
          <canvas
            ref={canvasRef}
            className="w-full rounded"
            style={{ width: "100%", height: 60 }}
          />
          <div className="flex justify-between text-[9px] text-gray-700 mt-1">
            <span>{history[0].date}</span>
            <span>{history[history.length - 1].date}</span>
          </div>
        </div>
      )}
    </div>
  );
}
