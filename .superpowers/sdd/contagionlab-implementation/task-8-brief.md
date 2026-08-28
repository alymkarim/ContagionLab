# Task 8: React Frontend Setup

**Files:**
- Create: `frontend/` (Vite + React + TypeScript project)
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/index.css`

**Depends on:** Task 7

## Steps

1. Initialize Vite React TypeScript project in `frontend/`:
   ```bash
   cd frontend
   npm create vite@latest . -- --template react-ts
   npm install
   npm install react-force-graph-2d recharts tailwindcss @tailwindcss/vite
   ```

2. Configure Vite (`frontend/vite.config.ts`):
   - Add tailwindcss plugin
   - Add proxy: `/api` -> `http://localhost:8000`

3. Update `frontend/src/index.css`:
   ```css
   @import "tailwindcss";
   ```

4. Create `frontend/src/api/client.ts`:
   - `buildNetwork(assets, method, period, topK, useRmt)` — POST to /api/networks/build
   - `runStressTest(assets, shockAsset, shockMagnitude, method, nSims)` — POST to /api/stress-test/run
   - TypeScript interfaces for NetworkResponse and StressTestResponse

5. Create minimal `frontend/src/App.tsx`:
   - Method selector dropdown (5 methods)
   - "Build Network" button
   - Metric cards (nodes, edges, density) when data loads
   - Dark theme (bg-gray-900)

6. Commit: `git add frontend/ && git commit -m "frontend scaffold — Vite + React + TypeScript, API client, basic layout"`

## Global Constraints

- TypeScript, no JavaScript
- Human-style commit messages
