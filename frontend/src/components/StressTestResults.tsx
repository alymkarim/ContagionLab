import { useEffect, useRef } from "react";
import type { StressTestResponse } from "../api/client";

interface Props {
  data: StressTestResponse;
}

function barColor(probNegative: number): string {
  if (probNegative > 0.5) return "#ef4444";
  if (probNegative > 0.25) return "#f59e0b";
  return "#10b981";
}

function riskLabel(probNegative: number): string {
  if (probNegative > 0.75) return "Critical";
  if (probNegative > 0.5) return "High";
  if (probNegative > 0.25) return "Moderate";
  return "Low";
}

export default function StressTestResults({ data }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const entries = Object.entries(data.results);
    const width = 340;
    const height = 220;
    const padTop = 20;
    const padBottom = 30;
    const padLeft = 45;
    const padRight = 15;
    const chartW = width - padLeft - padRight;
    const chartH = height - padTop - padBottom;

    canvas.width = width;
    canvas.height = height;

    ctx.fillStyle = "#111827";
    ctx.fillRect(0, 0, width, height);

    if (entries.length === 0) return;

    const allMedians = entries.map(([, r]) => r.median);
    const minVal = Math.min(...allMedians, 0);
    const maxVal = Math.max(...allMedians, 0);
    const range = Math.max(maxVal - minVal, 0.01);

    function yScale(v: number): number {
      return padTop + chartH - ((v - minVal) / range) * chartH;
    }

    // grid lines
    ctx.strokeStyle = "#1f2937";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const val = minVal + (range * i) / 4;
      const y = yScale(val);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(width - padRight, y);
      ctx.stroke();

      ctx.fillStyle = "#6b7280";
      ctx.font = "9px sans-serif";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(val.toFixed(2), padLeft - 5, y);
    }

    // zero line
    const zeroY = yScale(0);
    ctx.strokeStyle = "#4b5563";
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(padLeft, zeroY);
    ctx.lineTo(width - padRight, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);

    // bars
    const barW = Math.min(28, (chartW / entries.length) * 0.55);
    const gap = (chartW - barW * entries.length) / (entries.length + 1);

    entries.forEach(([asset, result], i) => {
      const x = padLeft + gap * (i + 1) + barW * i;
      const medianY = yScale(result.median);
      const y0 = yScale(0);

      ctx.fillStyle = barColor(result.prob_negative);
      ctx.globalAlpha = 0.8;
      ctx.fillRect(x, Math.min(medianY, y0), barW, Math.abs(medianY - y0));
      ctx.globalAlpha = 1;

      // CI whiskers
      const [ciLow, ciHigh] = result.ci_95;
      const whiskerX = x + barW / 2;

      ctx.strokeStyle = "#9ca3af";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(whiskerX, yScale(ciLow));
      ctx.lineTo(whiskerX, yScale(ciHigh));
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(whiskerX - 3, yScale(ciLow));
      ctx.lineTo(whiskerX + 3, yScale(ciLow));
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(whiskerX - 3, yScale(ciHigh));
      ctx.lineTo(whiskerX + 3, yScale(ciHigh));
      ctx.stroke();

      // labels
      ctx.fillStyle = "#9ca3af";
      ctx.font = "9px monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(asset, whiskerX, height - padBottom + 5);
    });
  }, [data]);

  const sorted = Object.entries(data.results).sort(
    (a, b) => a[1].median - b[1].median,
  );

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-300">Results</h3>
        <span className="text-xs text-gray-500">
          Shock {data.shock_asset} by {(data.shock_magnitude * 100).toFixed(0)}%
        </span>
      </div>

      <canvas
        ref={canvasRef}
        className="w-full rounded"
        style={{ width: "100%", height: 220 }}
      />

      <div className="mt-4 space-y-2">
        {sorted.map(([asset, r]) => (
          <div
            key={asset}
            className="flex items-center gap-3 text-xs"
          >
            <span
              className="w-1.5 h-1.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: barColor(r.prob_negative) }}
            />
            <span className="font-mono text-gray-300 w-14">{asset}</span>
            <div className="flex-1 h-1.5 bg-gray-800 rounded overflow-hidden">
              <div
                className="h-full rounded transition-all"
                style={{
                  width: `${Math.abs(r.median) * 100}%`,
                  backgroundColor: barColor(r.prob_negative),
                }}
              />
            </div>
            <span className="text-gray-500 w-20 text-right">
              {riskLabel(r.prob_negative)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
