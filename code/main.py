import sys
import csv
import time
from pathlib import Path

from indexer import build_index
from agent import process_ticket

REPO_ROOT = Path(__file__).resolve().parent.parent
TICKETS_DIR = REPO_ROOT / "support_tickets"
INPUT_CSV = TICKETS_DIR / "support_tickets.csv"
OUTPUT_CSV = TICKETS_DIR / "output.csv"
SAMPLE_CSV = TICKETS_DIR / "sample_support_tickets.csv"

OUTPUT_COLUMNS = ["issue", "subject", "company", "response", "product_area", "status", "request_type", "justification"]


def read_tickets(path: Path) -> list[dict]:
    tickets = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickets.append({
                "issue": row.get("Issue", row.get("issue", "")).strip(),
                "subject": row.get("Subject", row.get("subject", "")).strip(),
                "company": row.get("Company", row.get("company", "")).strip(),
            })
    return tickets


def write_output(results: list[dict], path: Path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"Output written to {path}")


def run(input_path: Path = INPUT_CSV, output_path: Path = OUTPUT_CSV):
    print("=" * 60)
    print("Building corpus index...")
    print("=" * 60)
    build_index()

    print(f"\nReading tickets from {input_path}...")
    tickets = read_tickets(input_path)
    print(f"  Found {len(tickets)} tickets.")

    print(f"\nProcessing tickets...")
    results = []
    for i, ticket in enumerate(tickets, 1):
        print(f"\n  [{i}/{len(tickets)}] {ticket['issue'][:80]}...")
        start = time.time()

        result = process_ticket(ticket["issue"], ticket["subject"], ticket["company"])

        output_row = {
            "issue": ticket["issue"],
            "subject": ticket["subject"],
            "company": ticket["company"],
            "response": result["response"],
            "product_area": result["product_area"],
            "status": result["status"],
            "request_type": result["request_type"],
            "justification": result["justification"],
        }
        results.append(output_row)

        elapsed = time.time() - start
        print(f"    -> {result['status']}, {result['request_type']}, {result['product_area']} ({elapsed:.1f}s)")

    write_output(results, output_path)

    print(f"\n{'=' * 60}")
    print(f"Done. Processed {len(results)} tickets -> {output_path}")
    print(f"{'=' * 60}")


def validate():
    sample_output = TICKETS_DIR / "sample_output.csv"
    if not sample_output.exists():
        print("No sample_output.csv found. Run with --sample first.")
        return

    with open(SAMPLE_CSV) as f:
        expected = list(csv.DictReader(f))
    with open(sample_output) as f:
        actual = list(csv.DictReader(f))

    print(f"Validating sample output ({len(expected)} tickets)")
    print("=" * 60)

    status_correct = type_correct = 0
    for i, (exp, act) in enumerate(zip(expected, actual), 1):
        exp_status = exp.get("Status", "").strip().lower()
        act_status = act.get("status", "").strip().lower()
        exp_type = exp.get("Request Type", "").strip().lower()
        act_type = act.get("request_type", "").strip().lower()

        s_ok = exp_status == act_status
        t_ok = exp_type == act_type
        if s_ok: status_correct += 1
        if t_ok: type_correct += 1

        flag_s = "ok" if s_ok else "MISS"
        flag_t = "ok" if t_ok else "MISS"
        print(f"  [{i:2d}] status:{flag_s} type:{flag_t} | {exp.get('Issue', '')[:50]}...")
        if not s_ok:
            print(f"       status: expected={exp_status} got={act_status}")
        if not t_ok:
            print(f"       type:   expected={exp_type} got={act_type}")

    n = len(expected)
    print(f"\nStatus accuracy:  {status_correct}/{n} ({status_correct/n*100:.0f}%)")
    print(f"Type accuracy:    {type_correct}/{n} ({type_correct/n*100:.0f}%)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        print("Running on sample tickets...")
        run(input_path=SAMPLE_CSV, output_path=TICKETS_DIR / "sample_output.csv")
    elif len(sys.argv) > 1 and sys.argv[1] == "--validate":
        validate()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        import tests
    else:
        run()
