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
