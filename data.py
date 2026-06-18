import random
from datetime import datetime, timedelta

SLA_RULES = {
    "Single Vision": 2,
    "Bifocal": 3,
    "Progressive": 4,
    "Blue Cut": 2,
    "Photochromic": 5,
    "Toric": 4,
}

STAGES = [
    "Order Placed",
    "Prescription Verified",
    "Lens Cutting",
    "Coating Applied",
    "QC Check",
    "Frame Fitting",
    "Final QC",
    "Dispatched",
    "Delivered",
]

STORES = [
    "Store A - Koramangala",
    "Store B - Indiranagar",
    "Store C - HSR Layout",
    "Store D - Whitefield",
]

COATINGS = ["Anti-Reflective", "UV Protection", "Blue Cut", "Scratch Resistant", "Hydrophobic"]
LENS_TYPES = list(SLA_RULES.keys())
CUSTOMERS = [
    "Priya Sharma", "Rahul Nair", "Ananya Roy", "Vikram Patel",
    "Sneha Iyer", "Arjun Singh", "Divya Menon", "Kiran Kumar",
    "Meera Joshi", "Sanjay Gupta",
]
FRAMES = ["Ray-Ban RB3025", "Titan Eye+", "Lenskart HQ", "Fastrack FT001", "Vincent Chase"]


def make_order(order_num, days_ago, stage, lens_type, store, delayed=False):
    sla = SLA_RULES[lens_type]
    order_date = datetime.now() - timedelta(days=days_ago)
    deadline = order_date + timedelta(days=sla)
    stage_idx = STAGES.index(stage)
    stage_log = []
    for i in range(stage_idx + 1):
        t = order_date + timedelta(hours=i * 5 + random.random() * 2)
        stage_log.append({
            "stage": STAGES[i],
            "time": t.strftime("%d %b %H:%M"),
            "note": "Supplier delay on coating" if (delayed and i == stage_idx) else "",
        })
    sph = round(random.uniform(-4, 1), 2)
    return {
        "id": f"ORD-{1000 + order_num}",
        "customer": random.choice(CUSTOMERS),
        "phone": f"+91 9{random.randint(100000000, 999999999)}",
        "store": store,
        "lens_type": lens_type,
        "index": random.choice([1.5, 1.56, 1.6, 1.67, 1.74]),
        "coating": random.choice(COATINGS),
        "frame": random.choice(FRAMES),
        "sph": sph,
        "cyl": round(random.uniform(-2, 0), 2),
        "axis": random.randint(0, 180),
        "order_date": order_date,
        "deadline": deadline,
        "sla_days": sla,
        "current_stage": stage,
        "stage_log": stage_log,
        "delayed": delayed,
        "delay_reason": "Supplier delay on coating" if delayed else "",
        "in_stock": random.random() > 0.4,
    }


SAMPLE_ORDERS = [
    make_order(0,  0.3,  "Order Placed",          "Single Vision",  STORES[0]),
    make_order(1,  1.0,  "Prescription Verified",  "Progressive",    STORES[1]),
    make_order(2,  1.5,  "Lens Cutting",           "Bifocal",        STORES[2]),
    make_order(3,  2.0,  "Coating Applied",        "Blue Cut",       STORES[0]),
    make_order(4,  2.5,  "QC Check",               "Single Vision",  STORES[3], delayed=True),
    make_order(5,  3.0,  "Frame Fitting",          "Photochromic",   STORES[1], delayed=True),
    make_order(6,  3.5,  "Final QC",               "Toric",          STORES[2]),
    make_order(7,  0.2,  "Order Placed",           "Blue Cut",       STORES[0]),
    make_order(8,  1.8,  "Lens Cutting",           "Progressive",    STORES[3], delayed=True),
    make_order(9,  4.0,  "Dispatched",             "Single Vision",  STORES[1]),
    make_order(10, 4.5,  "Delivered",              "Bifocal",        STORES[2]),
    make_order(11, 0.8,  "Prescription Verified",  "Toric",          STORES[0]),
    make_order(12, 2.2,  "Coating Applied",        "Single Vision",  STORES[3]),
    make_order(13, 1.2,  "QC Check",               "Blue Cut",       STORES[1], delayed=True),
    make_order(14, 3.0,  "Frame Fitting",          "Progressive",    STORES[0]),
]

SAMPLE_INVENTORY = [
    {"id": "INV-001", "lens_type": "Single Vision", "index": 1.50, "power": "-1.00", "stock": 12, "min_stock": 5,  "coating": "Anti-Reflective"},
    {"id": "INV-002", "lens_type": "Single Vision", "index": 1.56, "power": "-2.00", "stock": 8,  "min_stock": 5,  "coating": "UV Protection"},
    {"id": "INV-003", "lens_type": "Progressive",   "index": 1.60, "power": "-1.50", "stock": 3,  "min_stock": 4,  "coating": "Anti-Reflective"},
    {"id": "INV-004", "lens_type": "Blue Cut",      "index": 1.56, "power": "-0.50", "stock": 15, "min_stock": 6,  "coating": "Blue Cut"},
    {"id": "INV-005", "lens_type": "Bifocal",       "index": 1.60, "power": "-2.50", "stock": 6,  "min_stock": 4,  "coating": "Scratch Resistant"},
    {"id": "INV-006", "lens_type": "Toric",         "index": 1.67, "power": "-3.00", "stock": 2,  "min_stock": 3,  "coating": "UV Protection"},
    {"id": "INV-007", "lens_type": "Photochromic",  "index": 1.50, "power": "-1.75", "stock": 7,  "min_stock": 4,  "coating": "Photochromic"},
    {"id": "INV-008", "lens_type": "Single Vision", "index": 1.67, "power": "-4.00", "stock": 4,  "min_stock": 3,  "coating": "Hydrophobic"},
    {"id": "INV-009", "lens_type": "Blue Cut",      "index": 1.74, "power": "+1.00", "stock": 0,  "min_stock": 3,  "coating": "Blue Cut"},
    {"id": "INV-010", "lens_type": "Progressive",   "index": 1.74, "power": "-2.25", "stock": 1,  "min_stock": 2,  "coating": "Anti-Reflective"},
]
