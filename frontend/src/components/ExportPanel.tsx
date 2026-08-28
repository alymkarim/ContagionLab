import type { NetworkResponse, StressTestResponse } from "../api/client";

interface Props {
  data: NetworkResponse;
  stressResults: StressTestResponse | null;
}

function downloadJSON(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadCSV(data: NetworkResponse, filename: string) {
  const rows = [
    ["source", "target", "weight", "p_value"],
    ...data.graph.edges.map((e) => [
      e.source,
      e.target,
      e.weight.toFixed(4),
      e.p_value?.toFixed(4) ?? "",
    ]),
  ];
  const csv = rows.map((r) => r.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ExportPanel({ data, stressResults }: Props) {
  const handleExportJSON = () => {
    const exportData = {
      method: data.method,
      num_nodes: data.num_nodes,
      num_edges: data.num_edges,
      graph: data.graph,
      metrics: data.metrics,
      stress_test: stressResults ?? null,
    };
    downloadJSON(exportData, `contagion_${data.method}_${Date.now()}.json`);
  };

  const handleExportCSV = () => {
    downloadCSV(data, `contagion_edges_${data.method}_${Date.now()}.csv`);
  };

  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] text-gray-600 uppercase tracking-wider">
        Export
      </span>
      <button
        onClick={handleExportJSON}
        className="px-3 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-300 transition-colors"
      >
        JSON
      </button>
      <button
        onClick={handleExportCSV}
        className="px-3 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-300 transition-colors"
      >
        CSV
      </button>
    </div>
  );
}
