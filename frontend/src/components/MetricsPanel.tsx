import type { NetworkResponse } from "../api/client";

interface Props {
  data: NetworkResponse;
}

export default function MetricsPanel({ data }: Props) {
  const { centrality, communities, systemic_importance } = data.metrics;

  // Sort nodes by eigenvector centrality (most important first)
  const byCentrality = Object.entries(centrality)
    .sort(([, a], [, b]) => b.eigenvector - a.eigenvector)
    .slice(0, 8);

  // Sort by systemic importance
  const bySystemic = Object.entries(systemic_importance)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8);

  // Group nodes by community using assignment map
  const communityGroups: Record<number, string[]> = {};
  Object.entries(communities.assignment).forEach(([node, comm]) => {
    const c = comm as number;
    if (!communityGroups[c]) communityGroups[c] = [];
    communityGroups[c].push(node);
  });

  return (
    <div className="space-y-4">
      {/* Systemic Importance */}
      <div className="rounded bg-gray-800 border border-gray-700 p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">
          Systemic Importance
        </h3>
        <div className="space-y-2">
          {bySystemic.map(([node, score]) => (
            <div key={node} className="flex items-center gap-2">
              <span className="text-xs font-mono w-12 text-gray-300">
                {node}
              </span>
              <div className="flex-1 h-2 bg-gray-700 rounded overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded"
                  style={{ width: `${score * 100}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 w-10 text-right">
                {(score * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Eigenvector Centrality */}
      <div className="rounded bg-gray-800 border border-gray-700 p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">
          Eigenvector Centrality
        </h3>
        <div className="space-y-2">
          {byCentrality.map(([node, c]) => (
            <div key={node} className="flex items-center gap-2">
              <span className="text-xs font-mono w-12 text-gray-300">
                {node}
              </span>
              <div className="flex-1 h-2 bg-gray-700 rounded overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded"
                  style={{ width: `${c.eigenvector * 100}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 w-10 text-right">
                {c.eigenvector.toFixed(3)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Communities */}
      <div className="rounded bg-gray-800 border border-gray-700 p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">
          Communities ({communities.num_communities} detected)
        </h3>
        <div className="space-y-3">
          {Object.entries(communityGroups).map(([comm, nodes]) => (
            <div key={comm}>
              <div className="text-xs text-gray-500 mb-1">
                Community {parseInt(comm) + 1} ({nodes.length} nodes)
              </div>
              <div className="flex flex-wrap gap-1">
                {nodes.map((node) => (
                  <span
                    key={node}
                    className="px-2 py-0.5 text-xs rounded bg-gray-700 text-gray-300 font-mono"
                  >
                    {node}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Betweenness Centrality */}
      <div className="rounded bg-gray-800 border border-gray-700 p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">
          Betweenness Centrality
        </h3>
        <div className="space-y-2">
          {Object.entries(centrality)
            .sort(([, a], [, b]) => b.betweenness - a.betweenness)
            .slice(0, 5)
            .map(([node, c]) => (
              <div key={node} className="flex items-center gap-2">
                <span className="text-xs font-mono w-12 text-gray-300">
                  {node}
                </span>
                <div className="flex-1 h-2 bg-gray-700 rounded overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded"
                    style={{ width: `${c.betweenness * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-10 text-right">
                  {c.betweenness.toFixed(3)}
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
