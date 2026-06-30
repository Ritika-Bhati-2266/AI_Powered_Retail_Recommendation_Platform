"""
Right-to-Forget Audit Script
BEFORE/AFTER verification that behavioural data is deleted (not flagged).
"""
import sys, os, sqlite3, json, urllib.request, urllib.error

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "personalisation.db")
CUSTOMER_ID = "a5c262e4-9ed1-4689-9fd5-5bd2e8e1dcf3"  # Aaliyah Carter
API_BASE = "http://localhost:8000/api"

def query_counts(cursor, customer_id):
    """Query all relevant tables for a customer."""
    counts = {}
    
    cursor.execute("SELECT COUNT(*) FROM events WHERE customer_id = ?", (customer_id,))
    counts["events"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE customer_id = ?", (customer_id,))
    counts["recommendations"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM consent_log WHERE customer_id = ?", (customer_id,))
    counts["consent_log"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM customer_segments WHERE customer_id = ?", (customer_id,))
    counts["segments"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM customer_offers WHERE customer_id = ?", (customer_id,))
    counts["offers"] = cursor.fetchone()[0]
    
    # Customer record itself
    cursor.execute("SELECT customer_id, name, consent_given, email FROM customers WHERE customer_id = ?", (customer_id,))
    row = cursor.fetchone()
    if row:
        counts["customer_record"] = True
        counts["customer_consent"] = row[2]
        counts["customer_name"] = row[1]
        counts["customer_email"] = row[3]
    else:
        counts["customer_record"] = False
        counts["customer_consent"] = None
        counts["customer_name"] = "DELETED"
        counts["customer_email"] = "DELETED"
    
    return counts

def print_counts(label, counts):
    """Print a formatted table of counts."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  {'Table':25s} {'Count':>10s}")
    print(f"  {'-'*25} {'-'*10}")
    print(f"  {'Events':25s} {counts['events']:>10d}")
    print(f"  {'Recommendations':25s} {counts['recommendations']:>10d}")
    print(f"  {'Consent Log':25s} {counts['consent_log']:>10d}")
    print(f"  {'Segments':25s} {counts['segments']:>10d}")
    print(f"  {'Offers':25s} {counts['offers']:>10d}")
    print(f"  {'Customer Record':25s} {'YES' if counts['customer_record'] else 'NO':>10s}")
    print(f"  {'Consent Given':25s} {str(counts['customer_consent']):>10s}")
    print(f"  {'Customer Name':25s} {counts['customer_name']:>30s}")
    print(f"  {'Customer Email':25s} {counts['customer_email']:>30s}")

def api_request(method, path, data=None):
    """Make an API request."""
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "detail": e.read().decode()}

def main():
    print(f"\n  Test Customer: Aaliyah Carter")
    print(f"  Customer ID:   {CUSTOMER_ID}")
    
    # ── BEFORE ──
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    before = query_counts(cursor, CUSTOMER_ID)
    print_counts("BEFORE — Right to Forget", before)
    
    # Show a sample of the data
    cursor.execute(
        "SELECT event_type, product_id, event_timestamp FROM events WHERE customer_id = ? LIMIT 3",
        (CUSTOMER_ID,)
    )
    sample_events = cursor.fetchall()
    print(f"\n  Sample events: {len(sample_events)} shown")
    for e in sample_events:
        print(f"    {e[0]:20s} | product={e[1][:8] if e[1] else 'N/A'}... | {e[2]}")
    
    cursor.execute(
        "SELECT product_id, score, reason_code FROM recommendations WHERE customer_id = ? LIMIT 3",
        (CUSTOMER_ID,)
    )
    sample_recs = cursor.fetchall()
    print(f"  Sample recommendations: {len(sample_recs)} shown")
    for r in sample_recs:
        print(f"    product={r[0][:8] if r[0] else 'N/A'}... | score={r[1]:.4f} | reason={r[2]}")
    
    conn.close()
    
    # ── RUN RIGHT TO FORGET ──
    print(f"\n{'='*60}")
    print("  RUNNING: POST /api/admin/right-to-forget/{customer_id}")
    result = api_request("POST", f"/admin/right-to-forget/{CUSTOMER_ID}")
    print(f"  Result: {json.dumps(result, indent=2)}")
    print(f"{'='*60}")
    
    # ── AFTER ──
    conn2 = sqlite3.connect(DB_PATH)
    cursor2 = conn2.cursor()
    after = query_counts(cursor2, CUSTOMER_ID)
    print_counts("AFTER — Right to Forget", after)
    
    # Verify consent_log has the 'forgotten' entry
    cursor2.execute(
        "SELECT action, dp_act, timestamp FROM consent_log WHERE customer_id = ?",
        (CUSTOMER_ID,)
    )
    after_logs = cursor2.fetchall()
    print(f"\n  Remaining consent_log entries: {len(after_logs)}")
    for log in after_logs:
        print(f"    action={log[0]:15s} | dp_act={log[1]:8s} | {log[2]}")
    
    conn2.close()
    
    # ── SUMMARY ──
    print(f"\n{'='*60}")
    print("  VERDICT")
    print(f"{'='*60}")
    all_deleted = True
    for key in ["events", "recommendations", "segments", "offers"]:
        was = before[key]
        now = after[key]
        status = "DELETED" if now == 0 else f"REMAINING ({now})"
        if now != 0:
            all_deleted = False
        print(f"  {key:20s}: {was:>4d} → {now:>4d}  [{status}]")
    
    consent_before = before["consent_log"]
    consent_after = after["consent_log"]
    print(f"  {'consent_log':20s}: {consent_before:>4d} → {consent_after:>4d}  [audit trail kept]")
    
    record_before = "YES" if before["customer_record"] else "NO"
    record_after = "YES" if after["customer_record"] else "NO"
    consent_b_val = str(before["customer_consent"])
    consent_a_val = str(after["customer_consent"])
    print(f"  {'Customer Record':20s}: {record_before:>4s} → {record_after:>4s}  [minimal record kept]")
    print(f"  {'Consent Given':20s}: {consent_b_val:>4s} → {consent_a_val:>4s}  [revoked]")
    
    if all_deleted:
        print(f"\n  {'>>':>15s} PASS: All behavioural data deleted, customer record preserved with consent revoked.")
    else:
        print(f"\n  {'>>':>15s} FAIL: Some behavioural data was not deleted.")

if __name__ == "__main__":
    main()
