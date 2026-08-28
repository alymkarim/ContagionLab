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

export default function StressTestResults({ data }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const entries = Object.entries(data.results);
    const width = 700;
    const height = 300;
    const padTop = 30;
    const padBottom = 40;
    const padLeft = 50;
    const padRight = 20;
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

    ctx.strokeStyle = "#374151";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const val = minVal + (range * i) / 4;
      const y = yScale(val);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(width - padRight, y);
      ctx.stroke();

      ctx.fillStyle = "#9ca3af";
      ctx.font = "10px sans-serif";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(val.toFixed(3), padLeft - 6, y);
    }

    const zeroY = yScale(0);
    ctx.strokeStyle = "#6b7280";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padLeft, zeroY);
    ctx.lineTo(width - padRight, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);

    const barW = Math.min(40, (chartW / entries.length) * 0.6);
    const gap = (chartW - barW * entries.length) / (entries.length + 1);

    entries.forEach(([asset, result], i) => {
      const x = padLeft + gap * (i + 1) + barW * i;
      const medianY = yScale(result.median);
      const y0 = yScale(0);

      const color = barColor(result.prob_negative);
      ctx.fillStyle = color;
      ctx.fillRect(x, Math.min(medianY, y0), barW, Math.abs(medianY - y0));

      const [ciLow, ciHigh] = result.ci_95;
      const ciLowY = yScale(ciLow);
      const ciHighY = yScale(ciHigh);
      const whiskerX = x + barW / 2;

      ctx.strokeStyle = "#d1d5db";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(whiskerX, ciLowY);
      ctx.lineTo(whiskerX, ciHighY);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(whiskerX - 4, ciLowY);
      ctx.lineTo(whiskerX + 4, ciLowY);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(whiskerX - 4, ciHighY);
      ctx.lineTo(whiskerX + 4, ciHighY);
      ctx.stroke();

      ctx.fillStyle = "#d1d5db";
      ctx.font = "10px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(asset, x + barW / 2, height - padBottom + 6);

      ctx.textBaseline = "bottom";
      ctx.fillText(result.median.toFixed(4), x + barW / 2, medianY - 4);
    });

    ctx.fillStyle = "#9ca3af";
    ctx.font = "11px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText("Median response to shock", width / 2, padTop - 10);
  }, [data]);

  return (
    <div className="rounded bg-gray-800 border border-gray-700 p-4">
      <h3 className="text-sm font-medium mb-2">
        Results — shock {data.shock_asset} by {(data.shock_magnitude * 100).toFixed(0)}%
      </h3>
      <canvas
        ref={canvasRef}
        className="rounded"
        style={{ width: 700, height: 300 }}
      />
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        {Object.entries(data.results).map(([asset, r]) => (
          <div key={asset} className="flex items-center gap-2">
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ backgroundColor: barColor(r.prob_negative) }}
            />
            <span className="text-gray-300 font-medium">{asset}</span>
            <span className="text-gray-500">
              P(neg)={(r.prob_negative * 100).toFixed(1)}%
            </span>
            <span className="text-gray-500">
              95% CI [{r.ci_95[0].toFixed(4)}, {r.ci_95[1].toFixed(4)}]
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
