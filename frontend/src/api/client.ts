export interface NetworkNode {
  id: string;
  [key: string]: unknown;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
  p_value?: number;
}

export interface NetworkResponse {
  graph: {
    nodes: NetworkNode[];
    edges: NetworkEdge[];
  };
  metrics: {
    centrality: Record<string, Record<string, number>>;
    communities: {
      num_communities: number;
      assignment: Record<string, number>;
      sizes: Record<number, number>;
    };
    systemic_importance: Record<string, number>;
  };
  method: string;
  num_nodes: number;
  num_edges: number;
}

export interface StressTestResult {
  [asset: string]: {
    median: number;
    ci_95: [number, number];
    prob_negative: number;
  };
}

export interface StressTestResponse {
  shock_asset: string;
  shock_magnitude: number;
  n_sims: number;
  method: string;
  results: StressTestResult;
}

export interface AssetUniverse {
  [sector: string]: Record<string, string>;
}

export interface CrisisInfo {
  id: string;
  name: string;
  start: string;
  end: string;
  description: string;
}

export interface CrisisAnalysisResponse {
  crisis: string;
  method: string;
  phases: {
    pre: NetworkResponse;
    during: NetworkResponse;
    post: NetworkResponse;
  };
  comparison: {
    density_change: number;
    clustering_change: number;
    interpretation: string;
  };
}

export interface FragilityResponse {
  summary: {
    current_fragility: number;
    mean_fragility: number;
    regime: string;
    trend: string;
  };
  history: { date: string; fragility: number; density: number; clustering: number; volatility: number }[];
}

const BASE = "/api";

export async function buildNetwork(
  assets: string[],
  method: string,
  period = "1y",
  topK = 3,
  useRmt = false,
): Promise<NetworkResponse> {
  const res = await fetch(`${BASE}/networks/build`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      assets,
      method,
      period,
      top_k: topK,
      use_rmt: useRmt,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Network build failed");
  }
  return res.json();
}

export async function runStressTest(
  assets: string[],
  shockAsset: string,
  shockMagnitude = -0.2,
  method = "pearson",
  nSims = 1000,
): Promise<StressTestResponse> {
  const res = await fetch(`${BASE}/stress-test/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      assets,
      shock_asset: shockAsset,
      shock_magnitude: shockMagnitude,
      method,
      n_sims: nSims,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Stress test failed");
  }
  return res.json();
}

export async function fetchAssets(): Promise<AssetUniverse> {
  const res = await fetch(`${BASE}/assets`);
  if (!res.ok) throw new Error("Failed to fetch assets");
  const data = await res.json();
  return data.universe;
}

export async function listCrises(): Promise<CrisisInfo[]> {
  const res = await fetch(`${BASE}/crisis/list`);
  if (!res.ok) throw new Error("Failed to fetch crises");
  const data = await res.json();
  return data.crises;
}

export async function analyzeCrisis(
  assets: string[],
  crisisId: string,
  method = "pearson",
  topK = 3,
): Promise<CrisisAnalysisResponse> {
  const res = await fetch(`${BASE}/crisis/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      assets,
      crisis_id: crisisId,
      method,
      top_k: topK,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Crisis analysis failed");
  }
  return res.json();
}

export async function computeFragility(
  assets: string[],
  period = "1y",
  window = 21,
  method = "pearson",
  topK = 3,
): Promise<FragilityResponse> {
  const res = await fetch(`${BASE}/fragility/compute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      assets,
      period,
      window,
      method,
      top_k: topK,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Fragility computation failed");
  }
  return res.json();
}

export async function buildMacroNetwork(
  assets: string[],
  method: string,
  macroIndicators: string[] = ["VIX", "DGS10", "DXY"],
  period = "1y",
  topK = 3,
): Promise<NetworkResponse> {
  const res = await fetch(`${BASE}/macro/network`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      assets,
      macro_indicators: macroIndicators,
      period,
      method,
      top_k: topK,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Macro network build failed");
  }
  return res.json();
}
