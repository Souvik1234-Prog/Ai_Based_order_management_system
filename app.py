import streamlit as st
from datetime import datetime, timedelta
import copy, json

from data import SAMPLE_ORDERS, SAMPLE_INVENTORY, SLA_RULES, STAGES, STORES, LENS_TYPES, COATINGS
from ollama_utils import (
    check_ollama_status, ask_ollama,
    build_breach_prompt, build_inventory_prompt, parse_breach_json,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OptiFlow OMS",
    page_icon="👓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #f8f7f4; }
  [data-testid="stSidebar"] { background: #1a1a2e; }
  [data-testid="stSidebar"] * { color: #ccc !important; }
  [data-testid="stSidebar"] .stRadio label { color: #fff !important; font-size: 15px; }
  h1, h2, h3 { color: #1a1a2e !important; }
  .metric-card {
    background: #fff;
    border: 1px solid #e5e3dc;
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
  }
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }
  .badge-placed    { background:#e8f4fd; color:#1565c0; }
  .badge-verified  { background:#f3e5f5; color:#6a1b9a; }
  .badge-cutting   { background:#fff3e0; color:#e65100; }
  .badge-coating   { background:#fce4ec; color:#880e4f; }
  .badge-qc        { background:#fff8e1; color:#f57f17; }
  .badge-fitting   { background:#e8eaf6; color:#1a237e; }
  .badge-finalqc   { background:#e0f2f1; color:#004d40; }
  .badge-dispatch  { background:#e8f5e9; color:#1b5e20; }
  .badge-delivered { background:#f5f5f5; color:#424242; }
  .sla-green  { background:#e8f5e9; color:#2e7d32; padding:3px 8px; border-radius:6px; font-weight:700; font-size:12px; }
  .sla-yellow { background:#fffde7; color:#f57f17; padding:3px 8px; border-radius:6px; font-weight:700; font-size:12px; }
  .sla-red    { background:#fff3e0; color:#e65100; padding:3px 8px; border-radius:6px; font-weight:700; font-size:12px; }
  .sla-breach { background:#ffebee; color:#b71c1c; padding:3px 8px; border-radius:6px; font-weight:700; font-size:12px; }
  .risk-LOW      { background:#e8f5e9; color:#2e7d32; padding:2px 10px; border-radius:6px; font-weight:700; font-size:12px; }
  .risk-MEDIUM   { background:#fffde7; color:#f57f17; padding:2px 10px; border-radius:6px; font-weight:700; font-size:12px; }
  .risk-HIGH     { background:#fff3e0; color:#e65100; padding:2px 10px; border-radius:6px; font-weight:700; font-size:12px; }
  .risk-CRITICAL { background:#ffebee; color:#b71c1c; padding:2px 10px; border-radius:6px; font-weight:700; font-size:12px; }
  .order-card {
    background: #fff;
    border: 1px solid #e5e3dc;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
  }
  .stButton button {
    border-radius: 7px !important;
    font-weight: 600 !important; 
  }
  .stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "orders" not in st.session_state:
    st.session_state.orders = copy.deepcopy(SAMPLE_ORDERS)
if "inventory" not in st.session_state:
    st.session_state.inventory = copy.deepcopy(SAMPLE_INVENTORY)
if "predictions" not in st.session_state:
    st.session_state.predictions = {}
if "alert_log" not in st.session_state:
    st.session_state.alert_log = []
if "ollama_model" not in st.session_state:
    st.session_state.ollama_model = "llama3.2"

# ── Helpers ───────────────────────────────────────────────────────────────────
def hours_left(deadline):
    return round((deadline - datetime.now()).total_seconds() / 3600)

def sla_html(h, sla_days):
    pct = h / (sla_days * 24) if sla_days else 0
    if h < 0:    return f'<span class="sla-breach">BREACHED</span>'
    if pct < 0.2: return f'<span class="sla-red">{h}h left</span>'
    if pct < 0.5: return f'<span class="sla-yellow">{h}h left</span>'
    return f'<span class="sla-green">{h}h left</span>'

STAGE_BADGE = {
    "Order Placed": "badge-placed", "Prescription Verified": "badge-verified",
    "Lens Cutting": "badge-cutting", "Coating Applied": "badge-coating",
    "QC Check": "badge-qc", "Frame Fitting": "badge-fitting",
    "Final QC": "badge-finalqc", "Dispatched": "badge-dispatch",
    "Delivered": "badge-delivered",
}

def stage_html(stage):
    cls = STAGE_BADGE.get(stage, "badge-placed")
    return f'<span class="badge {cls}">{stage}</span>'

def progress_bar(stage):
    idx = STAGES.index(stage) if stage in STAGES else 0
    bars = ""
    for i in range(7):
        if i < idx:
            color = "#1a1a2e"
        elif i == idx:
            color = "#e8b84b"
        else:
            color = "#ddd"
        bars += f'<div style="flex:1;height:6px;border-radius:3px;background:{color}"></div>'
    return f'<div style="display:flex;gap:2px;margin-top:4px">{bars}</div>'

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👓 OptiFlow OMS")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["📋 Order Dashboard", "🔍 Lens Inventory", "🤖 TAT & Predictions"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    # Ollama status
    ok, models = check_ollama_status()
    if ok:
        st.success("🟢 Ollama Running")
        if models:
            st.session_state.ollama_model = st.selectbox("Model", models, index=0)
        else:
            st.warning("No models found.\nRun: `ollama pull llama3.2`")
    else:
        st.error("🔴 Ollama Offline")
        st.code("ollama serve\nollama pull llama3.2")

    st.markdown("---")
    st.markdown("**SLA Reference**")
    for lens, days in SLA_RULES.items():
        st.markdown(f"• {lens}: **{days}d**")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — ORDER DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📋 Order Dashboard":
    st.title("📋 Order Dashboard")

    orders = st.session_state.orders

    # ── Metrics ──
    total   = len(orders)
    active  = sum(1 for o in orders if o["current_stage"] != "Delivered")
    breached = sum(1 for o in orders if hours_left(o["deadline"]) < 0 and o["current_stage"] != "Delivered")
    at_risk  = sum(1 for o in orders if 0 <= hours_left(o["deadline"]) < 12 and o["current_stage"] != "Delivered")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Total Orders", total)
    c2.metric("⚙️ Active", active)
    c3.metric("🚨 SLA Breached", breached)
    c4.metric("⚠️ At Risk (<12h)", at_risk)

    st.markdown("---")

    # ── Filters ──
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        search = st.text_input("🔍 Search by name / order ID", placeholder="e.g. ORD-1001 or Priya")
    with col2:
        filter_stage = st.selectbox("Filter by Stage", ["All"] + STAGES)
    with col3:
        filter_lens = st.selectbox("Filter by Lens Type", ["All"] + LENS_TYPES)
    with col4:
        filter_store = st.selectbox("Filter by Store", ["All"] + STORES)

    # Apply filters
    filtered = [
        o for o in orders
        if (not search or search.lower() in o["id"].lower() or search.lower() in o["customer"].lower())
        and (filter_stage == "All" or o["current_stage"] == filter_stage)
        and (filter_lens == "All" or o["lens_type"] == filter_lens)
        and (filter_store == "All" or o["store"] == filter_store)
    ]

    st.markdown(f"**{len(filtered)} orders** shown")

    # ── Add New Order ──
    with st.expander("➕ Add New Order"):
        with st.form("new_order_form"):
            na, nb = st.columns(2)
            with na:
                n_customer = st.text_input("Customer Name")
                n_phone    = st.text_input("Phone", placeholder="+91 9XXXXXXXXX")
                n_store    = st.selectbox("Store", STORES)
                n_lens     = st.selectbox("Lens Type", LENS_TYPES)
            with nb:
                n_frame   = st.text_input("Frame Model")
                n_coating = st.selectbox("Coating", COATINGS)
                n_sph     = st.number_input("SPH", min_value=-10.0, max_value=10.0, value=0.0, step=0.25)
                nc, nd = st.columns(2)
                with nc: n_cyl  = st.number_input("CYL", min_value=-6.0, max_value=0.0, value=0.0, step=0.25)
                with nd: n_axis = st.number_input("Axis", min_value=0, max_value=180, value=90)

            submitted = st.form_submit_button("✅ Create Order", use_container_width=True)
            if submitted and n_customer:
                sla = SLA_RULES[n_lens]
                now = datetime.now()
                new_o = {
                    "id": f"ORD-{2000 + len(orders)}",
                    "customer": n_customer, "phone": n_phone,
                    "store": n_store, "lens_type": n_lens, "index": 1.56,
                    "coating": n_coating, "frame": n_frame,
                    "sph": n_sph, "cyl": n_cyl, "axis": n_axis,
                    "order_date": now,
                    "deadline": now + timedelta(days=sla),
                    "sla_days": sla, "current_stage": "Order Placed",
                    "stage_log": [{"stage": "Order Placed", "time": now.strftime("%d %b %H:%M"), "note": ""}],
                    "delayed": False, "delay_reason": "", "in_stock": True,
                }
                st.session_state.orders.insert(0, new_o)
                st.success(f"✅ Order {new_o['id']} created for {n_customer}!")
                st.rerun()

    st.markdown("---")

    # ── Orders List ──
    if not filtered:
        st.info("No orders match the current filters.")

    for order in filtered:
        h = hours_left(order["deadline"])
        delayed_tag = ' <span style="background:#fff3e0;color:#e65100;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700">DELAYED</span>' if order["delayed"] else ""

        with st.container():
            st.markdown(f"""
            <div class="order-card">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div>
                        <b style="font-size:15px;color:#1a1a2e">{order['id']}</b>{delayed_tag}
                        &nbsp; <span style="color:#666">{order['customer']}</span>
                        &nbsp; <span style="color:#999;font-size:12px">{order['phone']}</span>
                    </div>
                    <div>{sla_html(h, order['sla_days'])}</div>
                </div>
                <div style="display:flex;gap:20px;margin-top:8px;font-size:13px;color:#555">
                    <span>🏪 {order['store'].split(' - ')[0]}</span>
                    <span>🔭 {order['lens_type']} · Idx {order['index']}</span>
                    <span>🕶 {order['frame']}</span>
                    <span>💊 SPH {order['sph']} | CYL {order['cyl']} | Ax {order['axis']}°</span>
                </div>
                <div style="margin-top:8px">{stage_html(order['current_stage'])}</div>
                {progress_bar(order['current_stage'])}
            </div>
            """, unsafe_allow_html=True)

            col_a, col_b, col_c = st.columns([3, 1, 1])
            with col_b:
                view_key = f"view_{order['id']}"
                if st.button("📄 View History", key=f"vh_{order['id']}", use_container_width=True):
                    st.session_state[view_key] = not st.session_state.get(view_key, False)
            with col_c:
                if st.button("✏️ Update Status", key=f"upd_{order['id']}", use_container_width=True):
                    st.session_state[f"edit_{order['id']}"] = True

            # Stage history
            if st.session_state.get(f"view_{order['id']}", False):
                with st.container():
                    st.markdown("**Stage History:**")
                    for log in order["stage_log"]:
                        note = f" — ⚠️ {log['note']}" if log["note"] else ""
                        st.markdown(f"• **{log['stage']}** at {log['time']}{note}")

            # Update form
            if st.session_state.get(f"edit_{order['id']}", False):
                with st.form(f"update_form_{order['id']}"):
                    st.markdown(f"**Update: {order['id']}**")
                    new_stage = st.selectbox("New Stage", STAGES, index=STAGES.index(order["current_stage"]))
                    delay_note = st.text_area("Delay Reason (optional)", placeholder="e.g. QC failure, supplier issue…")
                    save = st.form_submit_button("💾 Save Update")
                    cancel = st.form_submit_button("Cancel")
                    if save:
                        for o in st.session_state.orders:
                            if o["id"] == order["id"]:
                                o["current_stage"] = new_stage
                                o["stage_log"].append({
                                    "stage": new_stage,
                                    "time": datetime.now().strftime("%d %b %H:%M"),
                                    "note": delay_note,
                                })
                                if delay_note:
                                    o["delayed"] = True
                                    o["delay_reason"] = delay_note
                        st.session_state[f"edit_{order['id']}"] = False
                        st.success(f"✅ {order['id']} updated to **{new_stage}**")
                        st.rerun()
                    if cancel:
                        st.session_state[f"edit_{order['id']}"] = False
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — LENS INVENTORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Lens Inventory":
    st.title("🔍 Lens Inventory")

    inv = st.session_state.inventory

    low_stock  = [i for i in inv if 0 < i["stock"] <= i["min_stock"]]
    out_stock  = [i for i in inv if i["stock"] == 0]

    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Total SKUs", len(inv))
    c2.metric("⚠️ Low Stock", len(low_stock))
    c3.metric("🚫 Out of Stock", len(out_stock))

    st.markdown("---")

    col_left, col_right = st.columns([1.5, 1])

    with col_left:
        st.subheader("Stock Levels")

        import pandas as pd
        rows = []
        for item in inv:
            status = "🚫 Out" if item["stock"] == 0 else ("⚠️ Low" if item["stock"] <= item["min_stock"] else "✅ OK")
            rows.append({
                "ID": item["id"],
                "Lens Type": item["lens_type"],
                "Index": item["index"],
                "Power": item["power"],
                "Coating": item["coating"],
                "Stock": item["stock"],
                "Min": item["min_stock"],
                "Status": status,
            })
        df = pd.DataFrame(rows)

        # Color rows
        def color_row(row):
            if row["Status"] == "🚫 Out":
                return ["background-color: #ffebee"] * len(row)
            elif row["Status"] == "⚠️ Low":
                return ["background-color: #fff3e0"] * len(row)
            return [""] * len(row)

        styled = df.style.apply(color_row, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("✏️ Update Stock Quantity")
        with st.form("update_stock"):
            item_ids = [i["id"] for i in inv]
            selected_id = st.selectbox("Select SKU", item_ids)
            new_qty = st.number_input("New Quantity", min_value=0, max_value=500, value=0)
            if st.form_submit_button("💾 Save Stock", use_container_width=True):
                for item in st.session_state.inventory:
                    if item["id"] == selected_id:
                        item["stock"] = new_qty
                st.success(f"✅ {selected_id} stock updated to {new_qty}")
                st.rerun()

    with col_right:
        st.subheader("🔍 Check Prescription Availability")
        with st.form("check_rx"):
            rx_lens = st.selectbox("Lens Type", LENS_TYPES)
            rx_sph  = st.number_input("SPH", min_value=-10.0, max_value=10.0, value=-1.5, step=0.25)
            rx_cyl  = st.number_input("CYL", min_value=-6.0, max_value=0.0, value=0.0, step=0.25)
            rx_axis = st.number_input("Axis (°)", min_value=0, max_value=180, value=90)
            check = st.form_submit_button("✅ Check Stock", use_container_width=True)

        if check:
            matches = [
                i for i in inv
                if i["lens_type"] == rx_lens
                and abs(float(i["power"]) - rx_sph) < 0.5
                and i["stock"] > 0
            ]
            if matches:
                st.success(f"✅ **In Stock!** {len(matches)} matching SKU(s) found — can fulfil immediately.")
                for m in matches:
                    st.markdown(f"• {m['id']} · Index {m['index']} · {m['coating']} · **{m['stock']} units**")
            else:
                st.error("❌ **Not in Stock.** Needs supplier order — expect +2 days to SLA.")

        st.markdown("---")
        st.subheader("🤖 AI Prescription Advice")
        st.caption("Uses local Ollama model for optical recommendations.")

        with st.form("ai_rx"):
            ai_lens = st.selectbox("Lens Type ", LENS_TYPES, key="ai_lens")
            ai_sph  = st.number_input("SPH ", min_value=-10.0, max_value=10.0, value=-1.5, step=0.25, key="ai_sph")
            ai_cyl  = st.number_input("CYL ", min_value=-6.0, max_value=0.0, value=0.0, step=0.25, key="ai_cyl")
            ai_axis = st.number_input("Axis ", min_value=0, max_value=180, value=90, key="ai_axis")
            ask_ai  = st.form_submit_button("🤖 Get AI Advice", use_container_width=True)

        if ask_ai:
            with st.spinner("Asking Ollama..."):
                prompt = build_inventory_prompt(ai_lens, ai_sph, ai_cyl, ai_axis)
                resp = ask_ollama(prompt, st.session_state.ollama_model)
            st.info(resp)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — TAT PREDICTION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 TAT & Predictions":
    st.title("🤖 TAT Prediction & Breach Alerts")

    orders  = st.session_state.orders
    active  = [o for o in orders if o["current_stage"] != "Delivered"]
    preds   = st.session_state.predictions
    alerts  = st.session_state.alert_log

    high_risk = [o for o in active if preds.get(o["id"], {}).get("riskLevel") in ("HIGH", "CRITICAL")]
    analysed  = len([o for o in active if o["id"] in preds])
    avg_breach = (
        round(sum(preds[o["id"]]["breachProbability"] for o in active if o["id"] in preds) / analysed)
        if analysed else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Active Orders",    len(active))
    c2.metric("🤖 Analysed",         analysed)
    c3.metric("🚨 High/Critical",     len(high_risk))
    c4.metric("📊 Avg Breach Risk",  f"{avg_breach}%" if analysed else "—")

    st.markdown("---")

    col_main, col_side = st.columns([1.6, 0.8])

    with col_main:
        st.subheader("Order Risk Analysis")

        # Bulk run button
        if st.button("🤖 Run AI Analysis on ALL Orders", use_container_width=True, type="primary"):
            progress = st.progress(0, text="Analysing orders...")
            for i, order in enumerate(active):
                with st.spinner(f"Analysing {order['id']}..."):
                    raw = ask_ollama(build_breach_prompt(order), st.session_state.ollama_model)
                    result = parse_breach_json(raw)
                    st.session_state.predictions[order["id"]] = result
                    if result["riskLevel"] in ("HIGH", "CRITICAL"):
                        st.session_state.alert_log.insert(0, {
                            "id": order["id"],
                            "customer": order["customer"],
                            "level": result["riskLevel"],
                            "probability": result["breachProbability"],
                            "time": datetime.now().strftime("%H:%M:%S"),
                        })
                progress.progress((i + 1) / len(active), text=f"Done {i+1}/{len(active)}")
            st.success("✅ Analysis complete!")
            st.rerun()

        st.markdown("")

        for order in active:
            pred = preds.get(order["id"])
            h = hours_left(order["deadline"])

            with st.container():
                st.markdown(f"""
                <div class="order-card">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                            <b>{order['id']}</b> &nbsp;
                            <span style="color:#666">{order['customer']}</span> &nbsp;
                            <span style="color:#999;font-size:12px">{order['lens_type']} · {order['current_stage']}</span>
                        </div>
                        <div>
                            {f'<span class="risk-{pred["riskLevel"]}">{pred["riskLevel"]}</span>' if pred else ""}
                            &nbsp; {sla_html(h, order['sla_days'])}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if pred:
                    pb = pred["breachProbability"]
                    bar_color = "#f44336" if pb > 70 else "#ff9800" if pb > 40 else "#4caf50"
                    ca, cb, cc = st.columns(3)
                    ca.markdown(f"**Breach risk:** {pb}%")
                    ca.markdown(f'<div style="height:6px;border-radius:3px;background:#eee"><div style="width:{pb}%;height:6px;border-radius:3px;background:{bar_color}"></div></div>', unsafe_allow_html=True)
                    cb.markdown(f"**ETA:** {pred['estimatedCompletionHours']}h")
                    cc.markdown(f"**Bottleneck:** {pred['bottleneck']}")
                    if pred.get("recommendation"):
                        st.info(f"💡 {pred['recommendation']}")

                btn_col, _ = st.columns([1, 4])
                with btn_col:
                    if st.button("Analyse this order", key=f"single_{order['id']}"):
                        with st.spinner(f"Analysing {order['id']}..."):
                            raw = ask_ollama(build_breach_prompt(order), st.session_state.ollama_model)
                            result = parse_breach_json(raw)
                            st.session_state.predictions[order["id"]] = result
                            if result["riskLevel"] in ("HIGH", "CRITICAL"):
                                st.session_state.alert_log.insert(0, {
                                    "id": order["id"],
                                    "customer": order["customer"],
                                    "level": result["riskLevel"],
                                    "probability": result["breachProbability"],
                                    "time": datetime.now().strftime("%H:%M:%S"),
                                })
                        st.rerun()

                st.markdown("---")

    with col_side:
        # Alert log
        st.subheader("🚨 Alert Log")
        if not alerts:
            st.caption("No alerts yet. Run analysis to generate alerts.")
        else:
            for alert in alerts[:10]:
                risk_color = "#b71c1c" if alert["level"] == "CRITICAL" else "#e65100"
                st.markdown(f"""
                <div style="border-left:3px solid {risk_color};padding:6px 10px;margin-bottom:8px;background:#fff;border-radius:0 6px 6px 0">
                    <b>{alert['id']}</b> — {alert['customer']}<br>
                    <span class="risk-{alert['level']}">{alert['level']}</span>
                    &nbsp; {alert['probability']}% risk &nbsp;
                    <span style="color:#aaa;font-size:11px">{alert['time']}</span>
                </div>
                """, unsafe_allow_html=True)
            if st.button("🗑️ Clear Alerts"):
                st.session_state.alert_log = []
                st.rerun()

        st.markdown("---")

        # Custom AI query
        st.subheader("💬 Ask AI about Operations")
        custom_q = st.text_area("Your question", placeholder="e.g. Which lens type causes most delays?\nHow to reduce Progressive TAT?", height=90)
        if st.button("Ask Ollama ↗", use_container_width=True):
            if custom_q.strip():
                context = f"""You are an AI assistant for an eyewear OMS.
Active orders: {len(active)}. Lens types in queue: {', '.join(set(o['lens_type'] for o in active))}.
Delayed orders: {sum(1 for o in active if o['delayed'])}.
Answer concisely: {custom_q}"""
                with st.spinner("Thinking..."):
                    resp = ask_ollama(context, st.session_state.ollama_model)
                st.info(resp)
