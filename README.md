# OptiFlow OMS — Streamlit Version

AI-powered eyewear order management. Pure Python, no Node.js needed.

## Quick Start

### Step 1 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Install & start Ollama
```bash
# Download from https://ollama.ai and install, then:
ollama pull llama3.2
ollama serve
```

### Step 3 — Run the app
```bash
streamlit run app.py
```
Opens at **http://localhost:8501**

---

## Features

### 📋 Order Dashboard
- View all orders with SLA countdown
- Filter by stage, lens type, store, search by name/ID
- Color-coded SLA health (green / yellow / red / BREACHED)
- Stage progress bars
- Update order stage + log delay reason
- Add new orders with prescription details

### 🔍 Lens Inventory
- Full inventory table with color-coded stock status
- Edit stock quantities
- Prescription availability checker (instant)
- AI-powered optical advice via Ollama

### 🤖 TAT Prediction & Alerts
- Run AI breach analysis (per order or bulk)
- Risk levels: LOW / MEDIUM / HIGH / CRITICAL
- Breach probability bar, bottleneck, recommendation
- Alert log for high-risk orders
- Custom natural language queries

---

## Files
```
eyewear-streamlit/
├── app.py          ← Main Streamlit app (all 3 pages)
├── data.py         ← Sample orders, inventory, SLA rules
├── ollama_utils.py ← Ollama API functions
└── requirements.txt
```

## SLA Rules
| Lens Type      | Days |
|----------------|------|
| Single Vision  | 2    |
| Bifocal        | 3    |
| Progressive    | 4    |
| Blue Cut       | 2    |
| Photochromic   | 5    |
| Toric          | 4    |
