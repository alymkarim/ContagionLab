import { useState, useEffect } from "react";
import {
  listCrises,
  analyzeCrisis,
  type CrisisInfo,
  type CrisisAnalysisResponse,
} from "../api/client";
import MiniNetworkGraph from "./MiniNetworkGraph";

interface Props {
  assets: string[];
  method: string;
}

export default function CrisisReplay({ assets, method }: Props) {
  const [crises, setCrises] = useState<CrisisInfo[]>([]);
  const [selectedCrisis, setSelectedCrisis] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CrisisAnalysisResponse | null>(null);

  useEffect(() => {
    listCrises()
      .then((c) => {
        setCrises(c);
        if (c.length > 0) setSelectedCrisis(c[0].id);
      })
      .catch(() => {});
  }, []);

  const handleAnalyze = async () => {
    if (!selectedCrisis || assets.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const res = await analyzeCrisis(assets, selectedCrisis, method);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const phases: { key: "pre" | "during" | "post"; label: string }[] = [
    { key: "pre", label: "Before" },
    { key: "during", label: "During" },
    { key: "post", label: "After" },
  ];

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-5">
      <h3 className="text-sm font-medium text-gray-300 mb-4">
        Crisis Replay
      </h3>

      <div className="space-y-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1.5">
            Select crisis event
          </label>
          <select
            value={selectedCrisis}
            onChange={(e) => setSelectedCrisis(e.target.value)}
            className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {crises.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.start})
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading || !selectedCrisis}
          className="w-full rounded-lg bg-blue-600/20 border border-blue-600/50 text-blue-400 px-4 py-2.5 text-sm font-medium hover:bg-blue-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
              Analyzing...
            </span>
          ) : (
            "Analyze Crisis"
          )}
        </button>

        {error && (
          <p className="text-red-400 text-xs bg-red-400/10 rounded px-3 py-2">
            {error}
          </p>
        )}
      </div>

      {result && (
        <div className="mt-6 space-y-5">
          <div className="grid grid-cols-3 gap-3">
            {phases.map(({ key, label }) => (
              <div key={key}>
                <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5 text-center">
                  {label}
                </div>
                <div className="rounded border border-gray-700 bg-gray-800 overflow-hidden">
                  <MiniNetworkGraph data={result.phases[key]} />
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <PhaseStat
              label="Density change"
              value={result.comparison.density_change}
            />
            <PhaseStat
              label="Clustering change"
              value={result.comparison.clustering_change}
            />
          </div>

          <div className="rounded bg-gray-800 border border-gray-700/50 p-3">
            <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">
              Interpretation
            </div>
            <p className="text-xs text-gray-400 leading-relaxed">
              {result.comparison.interpretation}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function PhaseStat({ label, value }: { label: string; value: number }) {
  const color =
    value > 0.1 ? "text-red-400" : value < -0.1 ? "text-green-400" : "text-gray-400";
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-gray-500">{label}</span>
      <span className={`font-mono ${color}`}>
        {value > 0 ? "+" : ""}
        {(value * 100).toFixed(1)}%
      </span>
    </div>
  );
}
