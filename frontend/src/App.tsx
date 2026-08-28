import { useState } from "react";
import {
  buildNetwork,
  buildMacroNetwork,
  computeFragility,
  type NetworkResponse,
  type StressTestResponse,
  type FragilityResponse,
} from "./api/client";
import NetworkGraph from "./components/NetworkGraph";
import MetricsPanel from "./components/MetricsPanel";
import StressTestPanel from "./components/StressTestPanel";
import StressTestResults from "./components/StressTestResults";
import CrisisReplay from "./components/CrisisReplay";
import FragilityGauge from "./components/FragilityGauge";
import ExportPanel from "./components/ExportPanel";
import ThemeToggle from "./components/ThemeToggle";

const METHODS = [
  {
    value: "pearson",
    label: "Pearson",
    desc: "Linear correlation. The baseline. Measures how two assets move together.",
  },
  {
    value: "spearman",
    label: "Spearman",
    desc: "Rank-based correlation. More robust to outliers and non-normal data.",
  },
  {
    value: "partial_correlation",
    label: "Partial",
    desc: "Direct relationships only. Removes indirect connections through other assets.",
  },
  {
    value: "graphical_lasso",
    label: "Graphical Lasso",
    desc: "Sparse precision matrix. Produces cleaner, more interpretable networks.",
  },
  {
    value: "granger_causality",
    label: "Granger Causality",
    desc: "Predictive relationships. \"A helps predict B\". Directed edges.",
  },
  {
    value: "tail_dependence",
    label: "Tail Dependence",
    desc: "Extreme co-movement. How likely are assets to crash together in the tails?",
  },
];

const EXAMPLE_PORTFOLIOS = [
  { label: "Tech", tickers: "AAPL, MSFT, NVDA, GOOGL, META, AMZN, TSLA" },
  { label: "S&P 500 Core", tickers: "SPY, QQQ, IWM, DIA, VTI, VOO" },
  { label: "Risk Parity", tickers: "SPY, TLT, GLD, UUP, DBC, IEF" },
  { label: "Banks", tickers: "JPM, BAC, GS, MS, C, WFC, BLK" },
  { label: "Energy", tickers: "XOM, CVX, COP, SLB, EOG, MPC" },
  { label: "Healthcare", tickers: "JNJ, UNH, PFE, ABBV, MRK, TMO" },
  { label: "Crypto-adjacent", tickers: "COIN, MSTR, MARA, RIOT, GLD, SPY" },
  { label: "Defensive", tickers: "XLU, XLP, TLT, GLD, VPU, PG, KO" },
];

const TICKER_CATEGORIES = [
  {
    name: "US Equities",
    tickers: [
      "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK.B",
      "JPM", "V", "UNH", "JNJ", "XOM", "PG", "MA", "HD", "CVX", "MRK",
      "ABBV", "LLY", "PEP", "COST", "KO", "AVGO", "WMT", "MCD", "CSCO",
      "ACN", "TMO", "ABT", "DHR", "NEE", "LIN", "TXN", "PM", "UPS",
      "RTX", "LOW", "HON", "INTC", "AMGN", "IBM", "QCOM", "SPGI",
      "GE", "CAT", "BA", "GS", "BLK", "AXP", "MS", "C",
    ],
  },
  {
    name: "ETFs",
    tickers: [
      "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VEA", "VWO",
      "TLT", "IEF", "SHY", "LQD", "HYG", "AGG", "BND", "GLD", "SLV",
      "USO", "XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "XLU", "XLRE",
      "DBC", "UUP", "FXE", "FXY", "EEM", "EFA", "VTV", "VUG",
    ],
  },
  {
    name: "Macro Indicators",
    tickers: [
      "VIX (^VIX)", "10Y Treasury (^TNX)", "Dollar Index (DX-Y.NYB)",
      "Gold Futures (GC=F)", "Oil Futures (CL=F)", "2Y Treasury (^IRX)",
    ],
  },
];

function App() {
  const [method, setMethod] = useState("pearson");
  const [assets, setAssets] = useState("SPY, QQQ, NVDA, AMD, JPM");
  const [includeMacro, setIncludeMacro] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<NetworkResponse | null>(null);
  const [stressResults, setStressResults] =
    useState<StressTestResponse | null>(null);
  const [fragilityData, setFragilityData] =
    useState<FragilityResponse | null>(null);

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
    setStressResults(null);
    setFragilityData(null);
    try {
      let res: NetworkResponse;
      if (includeMacro) {
        res = await buildMacroNetwork(assetList, method);
      } else {
        res = await buildNetwork(assetList, method);
      }
      setData(res);
      computeFragility(assetList)
        .then(setFragilityData)
        .catch((err) => console.warn("Fragility computation failed:", err));
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
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Hero */}
      <div className="border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg">
              C
            </div>
            <h1 className="text-4xl font-bold tracking-tight">ContagionLab</h1>
            <div className="ml-auto">
              <ThemeToggle />
            </div>
          </div>
          <p className="text-gray-400 text-lg max-w-2xl leading-relaxed">
            Model financial markets as networks. See how assets depend on each
            other, which ones matter most, and what happens when one crashes.
          </p>
          <div className="flex gap-6 mt-6 text-sm text-gray-500">
            <span>6 network methods</span>
            <span className="text-gray-700">|</span>
            <span>RMT noise filtering</span>
            <span className="text-gray-700">|</span>
            <span>Monte Carlo stress tests</span>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-6xl mx-auto px-6 py-10">
        {/* Input section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
          {/* Ticker input */}
          <div className="lg:col-span-2">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Assets
            </label>
            <input
              type="text"
              value={assets}
              onChange={(e) => setAssets(e.target.value)}
              className="w-full rounded-lg bg-gray-900 border border-gray-700 px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
              placeholder="SPY, QQQ, NVDA, AMD, JPM"
            />
            <p className="mt-2 text-sm text-gray-500">
              Enter stock or ETF tickers separated by commas. A{" "}
              <strong className="text-gray-400">ticker</strong> is a 1-5 letter
              code that identifies a publicly traded company or fund on the stock
              market. For example, <span className="font-mono text-gray-400">AAPL</span> is
              Apple, <span className="font-mono text-gray-400">SPY</span> tracks the S&P 500, and{" "}
              <span className="font-mono text-gray-400">TLT</span> tracks long-term
              US Treasury bonds.
            </p>
            <div className="flex flex-wrap gap-2 mt-3">
              {EXAMPLE_PORTFOLIOS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => setAssets(p.tickers)}
                  className="px-3 py-1 text-xs rounded-full border border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-300 transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>
            <div className="mt-4 p-4 rounded-lg bg-gray-900/50 border border-gray-800">
              <div className="text-xs font-medium text-gray-500 mb-3 uppercase tracking-wider">
                Available tickers
              </div>
              <div className="space-y-3">
                {TICKER_CATEGORIES.map((cat) => (
                  <div key={cat.name}>
                    <div className="text-[10px] text-gray-600 mb-1">{cat.name}</div>
                    <div className="flex flex-wrap gap-1">
                      {cat.tickers.map((t) => (
                        <button
                          key={t}
                          onClick={() => {
                            const current = assets
                              .split(",")
                              .map((a) => a.trim().toUpperCase())
                              .filter(Boolean);
                            const clean = t.split(" ")[0];
                            if (!current.includes(clean)) {
                              setAssets(
                                current.length > 0
                                  ? assets + ", " + clean
                                  : clean,
                              );
                            }
                          }}
                          className="px-1.5 py-0.5 text-[10px] rounded font-mono text-gray-500 hover:bg-gray-800 hover:text-gray-300 transition-colors cursor-pointer"
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Method selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Network Method
            </label>
            <div className="space-y-2">
              {METHODS.map((m) => (
                <button
                  key={m.value}
                  onClick={() => setMethod(m.value)}
                  className={`w-full text-left px-4 py-3 rounded-lg border transition-all text-sm ${
                    method === m.value
                      ? "border-blue-500 bg-blue-500/10 text-blue-400"
                      : "border-gray-700 bg-gray-900 text-gray-400 hover:border-gray-600"
                  }`}
                >
                  <div className="font-medium">{m.label}</div>
                  <div className="text-xs mt-1 opacity-70">{m.desc}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Build button */}
        <div className="mb-10 flex items-center gap-6">
          <button
            onClick={handleBuild}
            disabled={loading}
            className="px-8 py-3 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-base"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg
                  className="animate-spin h-4 w-4"
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
                Building network...
              </span>
            ) : (
              "Build Network"
            )}
          </button>
          <label className="flex items-center gap-3 cursor-pointer">
            <div
              className={`relative w-10 h-5 rounded-full transition-colors ${
                includeMacro ? "bg-blue-600" : "bg-gray-700"
              }`}
              onClick={() => setIncludeMacro(!includeMacro)}
            >
              <div
                className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  includeMacro ? "translate-x-5" : ""
                }`}
              />
            </div>
            <div>
              <div className="text-sm text-gray-300">Include macro data</div>
              <div className="text-[10px] text-gray-600">
                VIX, Treasury yields, Dollar index
              </div>
            </div>
          </label>
          {error && <p className="mt-3 text-red-400 text-sm">{error}</p>}
          {loading && (
            <div className="mt-4 w-full">
              <div className="h-1 w-full bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full animate-progress" />
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Fetching price data and building network...
              </p>
            </div>
          )}
        </div>

        {/* Results */}
        {data && (
          <div className="space-y-8">
            {/* Stats bar */}
            <div className="flex flex-wrap items-center gap-8 py-4 border-y border-gray-800">
              <Stat label="Assets" value={data.num_nodes} />
              <Stat label="Connections" value={data.num_edges} />
              <Stat label="Density" value={density.toFixed(3)} />
              <Stat label="Method" value={data.method} />
              <div className="ml-auto">
                <ExportPanel data={data} stressResults={stressResults} />
              </div>
            </div>

            {/* Graph + panels */}
            <div className="flex flex-col xl:flex-row gap-6">
              <div className="flex-1 min-w-0">
                <NetworkGraph data={data} />
              </div>
              <div className="w-full xl:w-[360px] flex-shrink-0 space-y-6">
                <MetricsPanel data={data} />
                <StressTestPanel
                  assets={data.graph.nodes.map((n) => n.id)}
                  method={data.method}
                  onResults={setStressResults}
                />
                {stressResults && <StressTestResults data={stressResults} />}
              </div>
            </div>

            {/* Fragility + Crisis Replay */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {fragilityData && <FragilityGauge data={fragilityData} />}
              <CrisisReplay
                assets={data.graph.nodes.map((n) => n.id)}
                method={data.method}
              />
            </div>
          </div>
        )}

        {/* How it works */}
        {!data && !loading && (
          <div className="mt-16 border-t border-gray-800 pt-12">
            <h2 className="text-2xl font-bold mb-8">How it works</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
              <Step
                number="1"
                title="Pick assets"
                desc="Type in stock or ETF tickers, whatever you want to analyze. The tool pulls price data from Yahoo Finance."
              />
              <Step
                number="2"
                title="Build the network"
                desc="Each asset becomes a node. Edges are drawn between assets that move together. The stronger the relationship, the thicker the edge."
              />
              <Step
                number="3"
                title="Stress test"
                desc="Pick an asset to 'crash' and see how the shock ripples through the network. Monte Carlo simulation runs thousands of scenarios."
              />
              <Step
                number="4"
                title="Replay crises"
                desc="Compare your portfolio's network before, during, and after 2008, 2020, or 2022. See if it would have held up."
              />
            </div>
            <div className="mt-10 p-5 rounded-lg bg-gray-900 border border-gray-800 text-sm text-gray-400 leading-relaxed space-y-3">
              <p>
                <strong className="text-gray-300">What's under the hood.</strong>{" "}
                This project borrows from statistical physics. Random Matrix Theory
                (Laloux et al. 1999) filters noise out of correlation matrices —
                the same technique physicists use to separate signal from noise in
                nuclear spectra. Monte Carlo simulation models shock propagation
                through the network.
              </p>
              <p>
                The fragility index combines network density, clustering, spectral
                gap, and volatility into a single score. Similar to an order
                parameter in a phase transition. When fragility spikes, the network
                is about to undergo a regime change.
              </p>
              <div className="flex flex-wrap gap-x-4 gap-y-1 pt-2 text-xs text-gray-600">
                <a href="https://doi.org/10.1103/PhysRevE.59.6573" target="_blank" rel="noopener noreferrer" className="hover:text-gray-400 underline decoration-gray-800">Laloux et al. (1999)</a>
                <a href="https://doi.org/10.1017/CBO9780511752414" target="_blank" rel="noopener noreferrer" className="hover:text-gray-400 underline decoration-gray-800">Mantegna &amp; Stanley (2000)</a>
                <a href="https://doi.org/10.1016/0304-4076(69)90002-6" target="_blank" rel="noopener noreferrer" className="hover:text-gray-400 underline decoration-gray-800">Granger (1969)</a>
                <a href="https://doi.org/10.1257/aer.98.5.2093" target="_blank" rel="noopener noreferrer" className="hover:text-gray-400 underline decoration-gray-800">Friedman et al. (2008)</a>
                <a href="https://doi.org/10.1007/978-1-4612-2294-3" target="_blank" rel="noopener noreferrer" className="hover:text-gray-400 underline decoration-gray-800">Joe (1997)</a>
                <a href="https://doi.org/10.1016/j.jfineco.2012.08.003" target="_blank" rel="noopener noreferrer" className="hover:text-gray-400 underline decoration-gray-800">Billio et al. (2012)</a>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div>
      <div className="text-xl font-bold">{value}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">
        {label}
      </div>
    </div>
  );
}

function Step({
  number,
  title,
  desc,
}: {
  number: string;
  title: string;
  desc: string;
}) {
  return (
    <div>
      <div className="w-8 h-8 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-sm font-bold mb-3">
        {number}
      </div>
      <h3 className="font-medium text-gray-200 mb-2">{title}</h3>
      <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
    </div>
  );
}

export default App;
