import type { NetworkResponse } from "../api/client";

interface Props {
  data: NetworkResponse;
}

export default function MetricsPanel({ data }: Props) {
  const { centrality, communities, systemic_importance } = data.metrics;

  const bySystemic = Object.entries(systemic_importance)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6);

  const byCentrality = Object.entries(centrality)
    .sort(([, a], [, b]) => b.eigenvector - a.eigenvector)
    .slice(0, 6);

  // Group nodes by community
  const communityGroups: Record<number, string[]> = {};
  Object.entries(communities.assignment).forEach(([node, comm]) => {
    const c = comm as number;
    if (!communityGroups[c]) communityGroups[c] = [];
    communityGroups[c].push(node);
  });

  return (
    <div className="space-y-4">
      {/* Systemic Importance */}
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-5">
        <h3 className="text-sm font-medium text-gray-300 mb-4">
          Systemic Importance
        </h3>
        <div className="space-y-2.5">
          {bySystemic.map(([node, score]) => (
            <div key={node} className="flex items-center gap-2.5">
              <span className="text-xs font-mono w-10 text-gray-400">
                {node}
              </span>
              <div className="flex-1 h-1.5 bg-gray-800 rounded overflow-hidden">
                <div
                  className="h-full bg-blue-500/80 rounded"
                  style={{ width: `${score * 100}%` }}
                />
              </div>
              <span className="text-[10px] text-gray-600 w-8 text-right">
                {(score * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Communities */}
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-5">
        <h3 className="text-sm font-medium text-gray-300 mb-4">
          Communities
          <span className="text-gray-600 font-normal ml-2">
            {communities.num_communities} detected
          </span>
        </h3>
        <div className="space-y-3">
          {Object.entries(communityGroups).map(([comm, nodes]) => (
            <div key={comm}>
              <div className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5">
                Group {parseInt(comm) + 1}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {nodes.map((node) => (
                  <span
                    key={node}
                    className="px-2 py-0.5 text-xs rounded-md bg-gray-800 text-gray-400 font-mono border border-gray-700/50"
                  >
                    {node}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Eigenvector Centrality */}
      <div className="rounded-lg border border-gray-700 bg-gray-900 p-5">
        <h3 className="text-sm font-medium text-gray-300 mb-1">
          Eigenvector Centrality
        </h3>
        <p className="text-[10px] text-gray-600 mb-4">
          Connection to other important nodes. Not just "who do you know" but
          "who do your contacts know"
        </p>
        <div className="space-y-2.5">
          {byCentrality.map(([node, c]) => (
            <div key={node} className="flex items-center gap-2.5">
              <span className="text-xs font-mono w-10 text-gray-400">
                {node}
              </span>
              <div className="flex-1 h-1.5 bg-gray-800 rounded overflow-hidden">
                <div
                  className="h-full bg-emerald-500/80 rounded"
                  style={{ width: `${c.eigenvector * 100}%` }}
                />
              </div>
              <span className="text-[10px] text-gray-600 w-12 text-right">
                {c.eigenvector.toFixed(3)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
