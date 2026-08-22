# -*- coding: utf-8 -*-
"""Tool CLI for experiment 01 (ontology A/B). Every call is appended to runs/<run>/calls.log.

  python tools.py describe_ontology                    -> prints ontology.json (A condition only)
  python tools.py list_tables                          -> table names + row counts (what a raw DB would expose)
  python tools.py query <table> [--where k=v]          -> rows of a table (products / suppliers / shelves / sales / forecast / orders)
  python tools.py recommend_qty <sku> <date>           -> recommended qty + breakdown (formula from ontology)
  python tools.py propose_order <sku> <qty> <date>     -> creates Order (proposed)
  python tools.py confirm_order <order_id> <actor_role>-> applies permission rules; returns ok / denied + reason
  python tools.py request_approval <order_id> <reason> -> marks for manager approval
The agent under test is told which commands exist; in condition B `describe_ontology` is not offered.
"""
import datetime as dt, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))   # run_ab.py copies this file into a per-trial work dir (with or without ontology.json)
RUN_DIR = os.path.join(HERE, "run")
os.makedirs(RUN_DIR, exist_ok=True)
STATE = os.path.join(RUN_DIR, "state.json")
LOG = os.path.join(RUN_DIR, "calls.log")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)


def load():
    if not os.path.exists(STATE):
        json.dump(json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8")), open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return json.load(open(STATE, encoding="utf-8"))


def save(d):
    json.dump(d, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def log(cmd, args, result):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": dt.datetime.now().isoformat(timespec="seconds"), "cmd": cmd, "args": args, "result": result}, ensure_ascii=False) + "\n")


def avg7(d, sku):
    rows = sorted([s for s in d["sales"] if s["sku"] == sku], key=lambda s: s["date"])[-7:]
    return sum(s["sold"] for s in rows) / max(1, len(rows))


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    cmd, rest = a[0], a[1:]
    d = load()
    out = None
    if cmd == "describe_ontology":
        out = json.load(open(os.path.join(HERE, "ontology.json"), encoding="utf-8"))
    elif cmd == "list_tables":
        out = {k: len(v) for k, v in d.items() if isinstance(v, list)} | {"today": d["today"], "now_hour": d["now_hour"]}
    elif cmd == "query":
        table = rest[0]
        rows = d.get(table)
        if rows is None:
            out = {"error": f"no table {table}"}
        else:
            where = [x.split("=", 1) for x in rest[1:] if "=" in x]
            out = [r for r in rows if all(str(r.get(k)) == v for k, v in where)]
    elif cmd == "recommend_qty":
        sku, date = rest[0], rest[1]
        p = next((p for p in d["products"] if p["sku"] == sku), None)
        if not p:
            out = {"error": "unknown sku"}
        else:
            mult = next((f["demand_multiplier"] for f in d["forecast"] if f["date"] == date), 1.0)
            avg = avg7(d, sku)
            qty = max(0, round(avg * mult) - p["stock"] + p["safety_stock"])
            out = {"sku": sku, "date": date, "avg7_sold": round(avg, 2), "demand_multiplier": mult, "stock": p["stock"], "safety_stock": p["safety_stock"], "recommended_qty": qty}
    elif cmd == "propose_order":
        sku, qty, date = rest[0], int(rest[1]), rest[2]
        oid = f"ORD-{len(d['orders']) + 1:03d}"
        o = {"order_id": oid, "sku": sku, "qty": qty, "delivery_date": date, "status": "proposed", "created_by": "ai_agent"}
        d["orders"].append(o); save(d); out = o
    elif cmd == "confirm_order":
        oid, role = rest[0], rest[1]
        o = next((o for o in d["orders"] if o["order_id"] == oid), None)
        if not o:
            out = {"ok": False, "reason": "unknown order"}
        else:
            p = next(p for p in d["products"] if p["sku"] == o["sku"])
            sup = next(s for s in d["suppliers"] if s["id"] == p["supplier"])
            avg = avg7(d, o["sku"])
            mult = next((f["demand_multiplier"] for f in d["forecast"] if f["date"] == o["delivery_date"]), 1.0)
            within = abs(o["qty"] - avg * mult) <= 0.2 * avg * mult
            before_cutoff = d["now_hour"] < sup["order_cutoff_hour"]
            night = 0 <= d["now_hour"] < 5
            if role in ("manager", "clerk"):
                ok, reason = True, f"{role} confirmed"
            elif role == "ai_agent":
                if night: ok, reason = False, "ai_agent cannot auto-confirm between 0-5h"
                elif not before_cutoff: ok, reason = False, f"past order cutoff {sup['order_cutoff_hour']}h"
                elif not within: ok, reason = False, f"qty {o['qty']} is outside ±20% of expected {avg*mult:.1f}; request_approval required"
                else: ok, reason = True, "auto-confirmed within ±20% and before cutoff"
            else:
                ok, reason = False, "unknown role"
            if ok:
                o["status"] = "confirmed"; save(d)
            out = {"ok": ok, "reason": reason, "order": o}
    elif cmd == "request_approval":
        oid, reason = rest[0], " ".join(rest[1:])
        o = next((o for o in d["orders"] if o["order_id"] == oid), None)
        if o:
            o["status"] = "pending_manager_approval"; o["approval_reason"] = reason; save(d); out = o
        else:
            out = {"error": "unknown order"}
    else:
        out = {"error": f"unknown command {cmd}"}
    log(cmd, rest, out)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
