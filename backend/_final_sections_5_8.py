"""Live verification of Sections 5-8:
  5. Cart & Checkout      6. Privacy Guardrails
  7. Product Images       8. Event Tracking
Runs against http://localhost:8000/api.
"""
import asyncio
import json
import uuid
import httpx

BASE = "http://localhost:8000/api"
RESULTS = []


def record(section, name, passed, detail=""):
    RESULTS.append({"section": section, "name": name, "passed": passed, "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {section} :: {name} :: {detail}")


async def api(client, method, path, token=None, json_body=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = await client.request(method, BASE + path, headers=headers, json=json_body)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


async def make_customer(client, name, prefs=None, consent=True):
    email = f"{name.lower().replace(' ', '.')}.{uuid.uuid4().hex[:8]}@test.local"
    st, c = await api(client, "POST", "/customers", json_body={
        "name": name, "email": email, "password": "TestPass@9876",
        "consent_given": consent, "currency": "USD", "category_preferences": prefs or [],
    })
    _, lg = await api(client, "POST", "/auth/login", json_body={"email": email, "password": "TestPass@9876"})
    return st, c, lg.get("access_token")


async def fetch_cat(client, cat, limit=30):
    from urllib.parse import quote
    st, data = await api(client, "GET", f"/products/search?category={quote(cat)}&limit={limit}")
    return data if isinstance(data, list) else []


async def run_section_5(client):
    print("\n======== SECTION 5: CART & CHECKOUT ========")
    st, cust, tok = await make_customer(client, "Checkout Chloe")
    if st != 201:
        record("5.Cart", "create customer", False, f"signup={st}")
        return

    electronics = await fetch_cat(client, "Electronics")
    if len(electronics) < 2:
        record("5.Cart", "fetch products", False, f"electronics={len(electronics)}")
        return
    p1, p2 = electronics[0], electronics[1]
    cid = cust["customer_id"]

    # Add to cart (both events tracked)
    a = await api(client, "POST", "/events", token=tok, json_body={
        "customer_id": cid, "event_type": "add_to_cart", "product_id": p1["product_id"], "session_id": "s5"})
    b = await api(client, "POST", "/events", token=tok, json_body={
        "customer_id": cid, "event_type": "page_view", "product_id": p2["product_id"], "session_id": "s5"})
    record("5.Cart", "Add-to-cart + page_view events accepted", a[0] == 200 and b[0] == 200,
           f"add={a[0]} view={b[0]}")

    # Adjust quantity via remove_from_cart event (frontend cart uses these)
    d = await api(client, "POST", "/events", token=tok, json_body={
        "customer_id": cid, "event_type": "remove_from_cart", "product_id": p1["product_id"], "session_id": "s5"})
    record("5.Cart", "Remove/quantity event accepted", d[0] == 200, f"remove={d[0]}")

    # Checkout: server-side prices, ignores client-supplied prices
    st_o, order = await api(client, "POST", f"/customers/{cid}/orders", token=tok, json_body={
        "items": [{"product_id": p1["product_id"], "quantity": 2}, {"product_id": p2["product_id"], "quantity": 1}],
        "shipping_name": "Chloe Checkout", "shipping_address": "123 Main St",
    })
    expected_total = round((p1["price"] * 2 + p2["price"]), 2)
    items_ok = isinstance(order.get("items"), list) and len(order.get("items", [])) == 2
    total_ok = abs((order.get("total_amount") or 0) - expected_total) < 0.01
    record("5.Cart", "Checkout completes, computes server-side total (qty respected)",
           st_o == 201 and items_ok and total_ok,
           f"status={st_o} total={order.get('total_amount')} expected={expected_total} items={len(order.get('items', [])) if isinstance(order.get('items'), list) else '?'}")

    # Order history (newest first) + order detail
    st_h, orders = await api(client, "GET", f"/customers/{cid}/orders", token=tok)
    record("5.Cart", "Order history returns placed order", st_h == 200 and len(orders) == 1 and orders[0]["order_id"] == order["order_id"],
           f"status={st_h} count={len(orders) if isinstance(orders, list) else '?'}")
    st_d, detail = await api(client, "GET", f"/customers/{cid}/orders/{order['order_id']}", token=tok)
    record("5.Cart", "Order detail endpoint returns full order",
           st_d == 200 and detail.get("status") == "placed" and len(detail.get("items", [])) == 2,
           f"status={st_d} items={len(detail.get('items', [])) if isinstance(detail.get('items'), list) else '?'}")

    # Checkout emits purchase events (feeds recommender/segmentation)
    st_pf, prof = await api(client, "GET", f"/customers/{cid}", token=tok)
    record("5.Cart", "Checkout emits purchase events (visible in metrics)",
           prof.get("metrics", {}).get("total_purchases", 0) >= 2,
           f"purchases={prof.get('metrics', {}).get('total_purchases')}")


async def run_section_6(client):
    print("\n======== SECTION 6: PRIVACY GUARDRAILS ========")
    st, cust, tok = await make_customer(client, "Privacy Paula", prefs=["Books"])
    cid = cust["customer_id"]
    if st != 201:
        record("6.Privacy", "create customer", False, f"signup={st}")
        return

    # Baseline: consenting customer gets recs + can track events
    st_r, _ = await api(client, "GET", f"/customers/{cid}/recommendations", token=tok)
    st_e, _ = await api(client, "POST", "/events", token=tok, json_body={
        "customer_id": cid, "event_type": "page_view", "product_id": None, "session_id": "s6"})
    record("6.Privacy", "Consenting customer: recs 200 + events 200", st_r == 200 and st_e == 200,
           f"recs={st_r} event={st_e}")

    # Revoke consent
    st_rv, prof = await api(client, "PATCH", f"/customers/{cid}", token=tok, json_body={"consent_given": False})
    record("6.Privacy", "Consent revoke returns updated profile", st_rv == 200 and prof.get("consent_status") is False,
           f"status={st_rv} consent={prof.get('consent_status')}")

    # Revoked: recs blocked
    st_r, resp_r = await api(client, "GET", f"/customers/{cid}/recommendations", token=tok)
    clear = "consent" in str(resp_r.get("detail", "")).lower()
    record("6.Privacy", "Recs blocked with 403 + clear consent message when revoked",
           st_r == 403 and clear, f"status={st_r} msg={resp_r.get('detail')}")

    # Revoked: offers blocked
    st_o, resp_o = await api(client, "GET", f"/customers/{cid}/offers", token=tok)
    clear_o = "consent" in str(resp_o.get("detail", "")).lower()
    record("6.Privacy", "Offers blocked with 403 when revoked", st_o == 403 and clear_o,
           f"status={st_o} msg={resp_o.get('detail')}")

    # Revoked: event ingestion blocked
    st_e, resp_e = await api(client, "POST", "/events", token=tok, json_body={
        "customer_id": cid, "event_type": "page_view", "product_id": None, "session_id": "s6"})
    clear_e = "consent" in str(resp_e.get("detail", "")).lower()
    record("6.Privacy", "Event tracking blocked with 403 when revoked", st_e == 403 and clear_e,
           f"status={st_e} msg={resp_e.get('detail')}")

    # Grant back -> accessible again
    st_g, _ = await api(client, "PATCH", f"/customers/{cid}", token=tok, json_body={"consent_given": True})
    st_r2, _ = await api(client, "GET", f"/customers/{cid}/recommendations", token=tok)
    st_e2, _ = await api(client, "POST", "/events", token=tok, json_body={
        "customer_id": cid, "event_type": "page_view", "product_id": None, "session_id": "s6"})
    record("6.Privacy", "Granting consent re-enables recs + events", st_g == 200 and st_r2 == 200 and st_e2 == 200,
           f"grant={st_g} recs={st_r2} event={st_e2}")

    # Data export: full JSON with audit trail
    st_x, export = await api(client, "GET", f"/customers/{cid}/data-export", token=tok)
    keys = list(export.keys()) if isinstance(export, dict) else []
    has_audit = isinstance(export.get("consent_audit_trail"), list)
    actions = [x.get("action") for x in export.get("consent_audit_trail", [])]
    has_events = isinstance(export.get("events"), list)
    has_consumer_blocks = {"exported_at", "customer", "events", "consent_audit_trail"} <= set(keys)
    record("6.Privacy", "Data export is full portable JSON incl. consent audit trail",
           st_x == 200 and has_consumer_blocks and has_audit and has_events,
           f"status={st_x} keys={len(keys)} audit_actions={actions} events={len(export.get('events', []))}")

    # Audit trail records both granted and revoked
    record("6.Privacy", "Audit trail logs grant AND revoke", {"granted", "revoked"} <= set(actions),
           f"actions={sorted(set(actions))}")


async def run_section_7(client):
    print("\n======== SECTION 7: PRODUCT IMAGES ========")
    categories = ["Electronics", "Pet Supplies", "Health & Wellness", "Sports & Outdoors"]
    bad = []
    sample_stats = {}
    for cat in categories:
        prods = await fetch_cat(client, cat, limit=30)
        if not prods:
            record("7.Images", f"Category '{cat}' has products", False, f"count=0")
            continue
        empty = [p["name"][:40] for p in prods if not p.get("image_url")]
        placeholder = [p["name"][:40] for p in prods if p.get("image_url") and "placeholder" in p["image_url"].lower()]
        sample_stats[cat] = {"count": len(prods), "empty": len(empty), "placeholder": len(placeholder)}
        if empty or placeholder:
            bad.append((cat, empty, placeholder))
        # HTTP-check a small sample of the images (redirect-following client:
        # Unsplash returns 30x to a CDN which the default client would call a
        # "bad" image even though the URL is perfectly fine).
        http_ok = http_bad = 0
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as ic:
            for p in prods[:5]:
                url = p.get("image_url")
                if not url:
                    http_bad += 1
                    continue
                try:
                    rr = await ic.get(url)
                    if rr.status_code == 200 and rr.headers.get("content-type", "").startswith("image/"):
                        http_ok += 1
                    else:
                        http_bad += 1
                except Exception:
                    http_bad += 1
        record("7.Images", f"'{cat}': all images non-empty & no placeholders",
               not empty and not placeholder, f"{sample_stats[cat]} http_ok={http_ok} http_bad={http_bad}")

    record("7.Images", "No placeholder/missing images across all sample categories",
           not bad, f"sample={sample_stats}")
    return sample_stats


async def run_section_8(client):
    print("\n======== SECTION 8: EVENT TRACKING ========")
    st, cust, tok = await make_customer(client, "Event Erica", prefs=["Books"])
    cid = cust["customer_id"]
    if st != 201:
        record("8.Events", "create customer", False, f"signup={st}")
        return
    electronics = await fetch_cat(client, "Electronics")
    pid = electronics[0]["product_id"] if electronics else None

    event_types = ["page_view", "add_to_cart", "remove_from_cart", "wishlist_add", "email_open", "email_click", "purchase"]
    results = {}
    for idx, et in enumerate(event_types):
        st_e, resp = await api(client, "POST", "/events", token=tok, json_body={
            "customer_id": cid, "event_type": et,
            "product_id": pid, "session_id": f"s8-{idx}"})
        results[et] = st_e
    all_ok = all(v == 200 for v in results.values())
    record("8.Events", "All 7 behavioural event types accepted (page_view..purchase)",
           all_ok, f"results={results}")

    # Verify persistence: profile metrics reflect the events
    st_pf, prof = await api(client, "GET", f"/customers/{cid}", token=tok)
    m = prof.get("metrics", {})
    record("8.Events", "Events persisted - metrics reflect views + cart + purchases",
           m.get("total_views", 0) >= 1 and m.get("total_cart_events", 0) >= 2 and m.get("total_purchases", 0) >= 1,
           f"views={m.get('total_views')} cart={m.get('total_cart_events')} purchases={m.get('total_purchases')} email={m.get('total_email_engagement')}")

    # Data export mirrors the raw events
    st_x, export = await api(client, "GET", f"/customers/{cid}/data-export", token=tok)
    ev_types_db = [e.get("event_type") for e in export.get("events", [])]
    record("8.Events", "Raw events present in data export", set(event_types) <= set(ev_types_db),
           f"exported={len(ev_types_db)} types={sorted(set(ev_types_db))}")

    # Unauthenticated event rejected
    st_unauth, _ = await api(client, "POST", "/events", json_body={
        "customer_id": cid, "event_type": "page_view", "product_id": pid})
    record("8.Events", "Event without token rejected 401", st_unauth == 401, f"status={st_unauth}")


async def main():
    async with httpx.AsyncClient(timeout=120) as client:
        await run_section_5(client)
        await run_section_6(client)
        await run_section_7(client)
        await run_section_8(client)

    print("\n======== SUMMARY (Sections 5-8) ========")
    passed = sum(1 for r in RESULTS if r["passed"])
    print(f"PASS {passed}/{len(RESULTS)}")
    for r in RESULTS:
        if not r["passed"]:
            print(f"  FAILED: {r['section']} :: {r['name']} :: {r['detail']}")
    with open("final_sections_5_8_report.json", "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2, ensure_ascii=False)
    print("Report written to final_sections_5_8_report.json")


if __name__ == "__main__":
    asyncio.run(main())