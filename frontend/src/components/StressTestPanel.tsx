import { useState } from "react";
import { runStressTest, type StressTestResponse } from "../api/client";

interface Props {
  assets: string[];
  method: string;
  onResults: (results: StressTestResponse) => void;
}

export default function StressTestPanel({ assets, method, onResults }: Props) {
  const [shockAsset, setShockAsset] = useState(assets[0] ?? "");
  const [magnitude, setMagnitude] = useState(-0.2);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    if (!shockAsset) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runStressTest(assets, shockAsset, magnitude, method);
      onResults(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const magnitudeLabel =
    magnitude <= -0.8
      ? "Severe crash"
      : magnitude <= -0.5
        ? "Major drop"
        : magnitude <= -0.2
          ? "Moderate decline"
          : "Minor dip";

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-5">
      <h3 className="text-sm font-medium text-gray-300 mb-4">
        Stress Test
      </h3>

      <div className="space-y-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1.5">
            Which asset crashes?
          </label>
          <select
            value={shockAsset}
            onChange={(e) => setShockAsset(e.target.value)}
            className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {assets.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs text-gray-500">How bad?</label>
            <span className="text-xs text-gray-400">
              {magnitude.toFixed(0)}% ({magnitudeLabel})
            </span>
          </div>
          <input
            type="range"
            min={-1}
            max={-0.01}
            step={0.01}
            value={magnitude}
            onChange={(e) => setMagnitude(parseFloat(e.target.value))}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-[10px] text-gray-600 mt-1">
            <span>-100% (total loss)</span>
            <span>-1% (blip)</span>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={loading || !shockAsset}
          className="w-full rounded-lg bg-amber-600/20 border border-amber-600/50 text-amber-400 px-4 py-2.5 text-sm font-medium hover:bg-amber-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg
                className="animate-spin h-3.5 w-3.5"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Simulating...
            </span>
          ) : (
            "Run Stress Test"
          )}
        </button>

        {error && (
          <p className="text-red-400 text-xs bg-red-400/10 rounded px-3 py-2">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
