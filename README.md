# ContagionLab

ContagionLab is a platform for simulating and analyzing financial contagion effects across global markets.

## Features

- SIR epidemic model adapted for financial contagion
- Network graph analysis of market interdependencies
- Monte Carlo simulation engine
- Real-time market data integration via yfinance
- Interactive dashboard

## Project Structure

```
contagionlab/
├── backend/           # FastAPI backend
│   ├── app/          # Application code
│   ├── tests/        # Test suite
│   └── requirements.txt
└── frontend/         # Frontend (coming soon)
```

## Getting Started

1. Create virtual environment: `python -m venv .venv`
2. Activate it: `.venv\Scripts\activate`
3. Install dependencies: `pip install -r backend/requirements.txt`
4. Run tests: `cd backend && python -m pytest tests/ -v`
5. Start server: `cd backend && uvicorn app.main:app --reload`

## Development

- Python 3.11+
- Testing: pytest
- Backend: FastAPI + uvicorn
