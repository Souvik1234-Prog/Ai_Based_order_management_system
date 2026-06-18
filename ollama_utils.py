import requests
import json

OLLAMA_URL = "http://localhost:11434"


def check_ollama_status():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if r.ok:
            models = [m["name"] for m in r.json().get("models", [])]
            return True, models
        return False, []
    except Exception:
        return False, []


def ask_ollama(prompt: str, model: str = "llama3.2") -> str:
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        if r.ok:
            return r.json().get("response", "No response.")
        return f"⚠️ Ollama returned HTTP {r.status_code}"
    except requests.exceptions.ConnectionError:
        return "⚠️ Cannot reach Ollama. Make sure it's running:\n```\nollama serve\n```"
    except Exception as e:
        return f"⚠️ Error: {e}"


def build_breach_prompt(order: dict) -> str:
    from datetime import datetime
    now = datetime.now()
    deadline = order["deadline"]
    hours_left = round((deadline - now).total_seconds() / 3600)
    stages = [
        "Order Placed", "Prescription Verified", "Lens Cutting",
        "Coating Applied", "QC Check", "Frame Fitting", "Final QC",
        "Dispatched", "Delivered",
    ]
    stage_idx = stages.index(order["current_stage"]) if order["current_stage"] in stages else 0
    pct = round((stage_idx / (len(stages) - 1)) * 100)

    return f"""You are an operations analyst for an eyewear manufacturing company.
Analyze this order and predict SLA breach risk.

Order: {order['id']}
Customer: {order['customer']}
Lens Type: {order['lens_type']}
SLA: {order['sla_days']} days
Current Stage: {order['current_stage']} ({pct}% complete, stage {stage_idx+1} of {len(stages)})
Hours until deadline: {hours_left}
Has delay history: {'Yes - ' + order['delay_reason'] if order['delayed'] else 'No'}
In stock: {'Yes' if order['in_stock'] else 'No'}

Based on typical eyewear manufacturing flows:
- QC failures add 24-48 hours
- Coating stages are often bottlenecks
- Progressive and Toric lenses take longer

Respond ONLY in this exact JSON format (no other text):
{{
  "riskLevel": "LOW|MEDIUM|HIGH|CRITICAL",
  "breachProbability": <number 0-100>,
  "estimatedCompletionHours": <number>,
  "bottleneck": "<one sentence>",
  "recommendation": "<one actionable sentence>"
}}"""


def build_inventory_prompt(lens_type: str, sph: float, cyl: float, axis: int) -> str:
    return f"""You are an eyewear inventory specialist.
A customer needs:
- Lens type: {lens_type}
- Sphere (SPH): {sph}
- Cylinder (CYL): {cyl}
- Axis: {axis}

Based on standard optical inventory practices, advise:
1. Is this a common or rare prescription?
2. What index would you recommend?
3. Expected availability (in-house vs special order)?

Keep response to 3 concise bullet points."""


def parse_breach_json(raw: str) -> dict:
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        pass
    return {
        "riskLevel": "MEDIUM",
        "breachProbability": 50,
        "estimatedCompletionHours": 24,
        "bottleneck": "Could not parse AI response.",
        "recommendation": raw[:150] if raw else "Run Ollama and try again.",
    }
