import { useState } from "react";
import { buildNetwork, type NetworkResponse } from "./api/client";
import NetworkGraph from "./components/NetworkGraph";

const METHODS = [
  { value: "pearson", label: "Pearson" },
  { value: "spearman", label: "Spearman" },
  { value: "partial_correlation", label: "Partial Correlation" },
  { value: "graphical_lasso", label: "Graphical Lasso" },
  { value: "granger_causality", label: "Granger Causality" },
];

function App() {
  const [method, setMethod] = useState("pearson");
  const [assets, setAssets] = useState("SPY,QQQ,TLT,GLD");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<NetworkResponse | null>(null);

  const handleBuild = async () => {
    const assetList = assets
      .split(",")
      .map((a) => a.trim().toUpperCase())
      .filter(Boolean);
    if (assetList.length < 2) {
      setError("Enter at least 2 tickers separated by commas");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await buildNetwork(assetList, method);
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const density = data
    ? (2 * data.num_edges) / (data.num_nodes * (data.num_nodes - 1))
    : 0;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-8">
      <h1 className="text-3xl font-bold mb-6">ContagionLab</h1>

      <div className="max-w-xl space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">
            Tickers (comma-separated)
          </label>
          <input
            type="text"
            value={assets}
            onChange={(e) => setAssets(e.target.value)}
            className="w-full rounded bg-gray-800 border border-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring focus:ring-blue-500"
            placeholder="SPY, QQQ, TLT, GLD"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Method</label>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="w-full rounded bg-gray-800 border border-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring focus:ring-blue-500"
          >
            {METHODS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleBuild}
          disabled={loading}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
        >
          {loading ? "Building…" : "Build Network"}
        </button>

        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}
      </div>

      {data && (
        <div className="mt-8 flex flex-col lg:flex-row gap-6">
          <NetworkGraph data={data} />
          <div className="grid grid-cols-1 gap-4 min-w-[200px]">
            <Card label="Nodes" value={data.num_nodes} />
            <Card label="Edges" value={data.num_edges} />
            <Card label="Density" value={density.toFixed(3)} />
          </div>
        </div>
      )}
    </div>
  );
}

function Card({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded bg-gray-800 border border-gray-700 p-4 text-center">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-gray-400 mt-1">{label}</div>
    </div>
  );
}

export default App;
