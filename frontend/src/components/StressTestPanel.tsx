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

  return (
    <div className="rounded bg-gray-800 border border-gray-700 p-4 space-y-3">
      <h3 className="text-sm font-medium">Stress Test</h3>

      <div>
        <label className="block text-xs text-gray-400 mb-1">Shock Asset</label>
        <select
          value={shockAsset}
          onChange={(e) => setShockAsset(e.target.value)}
          className="w-full rounded bg-gray-900 border border-gray-700 px-2 py-1.5 text-sm focus:outline-none focus:ring focus:ring-blue-500"
        >
          {assets.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Shock Magnitude: {magnitude.toFixed(2)}
        </label>
        <input
          type="range"
          min={-1}
          max={-0.01}
          step={0.01}
          value={magnitude}
          onChange={(e) => setMagnitude(parseFloat(e.target.value))}
          className="w-full accent-blue-500"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>-1.0</span>
          <span>-0.01</span>
        </div>
      </div>

      <button
        onClick={handleRun}
        disabled={loading || !shockAsset}
        className="w-full rounded bg-amber-600 px-3 py-1.5 text-sm font-medium hover:bg-amber-500 disabled:opacity-50"
      >
        {loading ? "Running…" : "Run Stress Test"}
      </button>

      {error && <p className="text-red-400 text-xs">{error}</p>}
    </div>
  );
}
