# MedRAG - Clinical Decision Support System

A clinical decision support system leveraging retrieval-augmented generation (RAG) with a 6-agent safety pipeline for enhanced medical decision-making and module extraction.

## Features

- **Multi-Agent Safety Pipeline**: 6-agent system for comprehensive safety validation
- **RAG-Based Retrieval**: Enhanced medical knowledge retrieval from PubMed
- **Web Search Integration**: Optional web search for real-time medical information
- **FastAPI Backend**: High-performance API server
- **React Frontend**: Modern user interface for clinical queries
- **CrewAI Integration**: Multi-agent orchestration for complex medical tasks

## Project Structure

```
├── backend/          # FastAPI backend server
├── frontend/         # React frontend application
├── agents/           # Multi-agent system implementation
├── clinical-med/     # Clinical domain logic
├── tools/            # Utility tools and helpers
├── utils/            # Common utilities
└── eval/             # Evaluation and results
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Luukkeee/clinical-med.git
cd clinical-med
```

2. Install Python dependencies:
```bash
cd major
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
```

### Running the Application

**Backend Server:**
```bash
cd major
python run.py --port 5500
```

**Frontend Development:**
```bash
cd frontend
npm run dev
```

### API Usage

Query the clinical decision support system:
```bash
curl -X POST http://localhost:5500/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the first-line treatment for hypertension?",
    "enable_web_search": false
  }'
```

## Architecture

- **Agent System**: CrewAI-based multi-agent framework with specialized roles
- **Safety Pipeline**: 6-tier validation for clinical accuracy
- **Retrieval System**: FAISS-based vector search over medical literature
- **API Layer**: FastAPI with async support
- **Frontend**: React with modern UI/UX patterns

## License

MIT

## Contact

For questions or issues, please open an issue on GitHub.
