# Task 9: Network Visualization Component

**Files:**
- Create: `frontend/src/components/NetworkGraph.tsx`
- Modify: `frontend/src/App.tsx`

**Depends on:** Task 8

## Steps

1. Create `frontend/src/components/NetworkGraph.tsx`:
   - Force-directed layout using vanilla canvas (no heavy deps)
   - Node radius sized by systemic importance percentile
   - Node color by community (Louvain assignment)
   - Edge lines with transparency
   - Node labels (asset tickers)
   - Simple force simulation: repulsion between all nodes, attraction along edges, center gravity, damping

2. Update `frontend/src/App.tsx`:
   - Import and render `<NetworkGraph data={data} />` when data is available
   - Layout: graph on left/center, metric cards on right or below

3. Verify build: `cd frontend && npm run build` — should succeed

4. Commit: `git add frontend/ && git commit -m "network graph visualization — force-directed layout, community colors, node sizing"`

## Global Constraints

- TypeScript, no JavaScript
- Human-style commit messages
