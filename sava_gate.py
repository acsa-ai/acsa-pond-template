#!/usr/bin/env python3
"""Cold, self-contained SAVA pond admission gate.

Runs the SAME checks the lake runs to admit a pond — but with nothing
installed beyond system python3 and the two pinned sibling tools this
script shells out to:

  * sava_verify.py     — verify the pond head and every Drop (signatures +
                         source fidelity; the proof travels IN each Drop).
  * sava_content_id.py — recompute each Drop's content_id = sha256(JCS(content)).

The only cryptography this file itself does is the SAVA Merkle rebuild
(15 lines, stdlib hashlib, domain-separated 0x00/0x01, unpaired node
promoted unchanged), used to confirm the Drops reconstruct the head's
signed merkle_root and member_count — i.e. the head commits exactly these
Drops, no smuggling.

A pond author runs this on their own pond before submitting. Because the
gate is deterministic, **if it passes here it passes at the lake.** Exit 0
= admissible, 1 = refused. Use --out to capture the JSON report to a file.

The gate proves provenance + faithful quotation, never that a source is
any good — worth-of-source is a policy concern (stake layer), deliberately
outside this cryptographic gate.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

# Sibling tools this gate shells out to resolve relative to THIS script, not the
# caller's CWD -- a pond author runs the gate from their own pond directory.
_HERE = Path(__file__).resolve().parent


def _leaf(cid_hex: str) -> bytes:
    return hashlib.sha256(b"\x00" + bytes.fromhex(cid_hex)).digest()


def _node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _merkle_root(content_ids: list) -> str:
    if not content_ids:
        return hashlib.sha256(b"\x00").hexdigest()
    cur = [_leaf(c) for c in sorted(content_ids)]
    while len(cur) > 1:
        nxt, i, n = [], 0, len(cur)
        while i < n:
            if i + 1 < n:
                nxt.append(_node(cur[i], cur[i + 1]))
                i += 2
            else:
                nxt.append(cur[i])  # promoted unchanged
                i += 1
        cur = nxt
    return cur[0].hex()


def _run(tool: str, *args: str) -> str:
    r = subprocess.run(
        [sys.executable, "-S", tool, *args], capture_output=True, text=True
    )
    return r.stdout


def _last_json(text: str) -> dict:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError("no JSON object on the tool's stdout")


def gate(pond_dir: Path, trust: str, verifier: str, contentid: str, now: str) -> dict:
    report: dict = {"admissible": False, "reason": None, "member_count": None, "claims": []}

    head = pond_dir / "pond_head.json"
    hv = _last_json(_run(verifier, "head", str(head), "--trust", trust, "--now", now, "--json"))
    if hv.get("result") != 0:
        report["reason"] = f"pond head failed verify (result {hv.get('result')})"
        return report

    content = json.loads(head.read_text())["content"]
    root, member_count = content["merkle_root"], content["member_count"]
    report["member_count"] = member_count

    content_ids, all_ok = [], True
    for dp in sorted((pond_dir / "drops").glob("*.json")):
        # The gate is a trust-critical admission context (decision B): it always
        # re-EXECUTES a check-grounded Drop's check (--execute-checks) rather than
        # deferring it, so a pond is admitted only if every check actually
        # re-derives its sealed verdict. Quote Drops are unaffected by the flag.
        dv = _last_json(
            _run(verifier, "drop", str(dp), "--trust", trust, "--execute-checks", "--json")
        )
        report["claims"].append({"drop": dp.stem, "result": dv.get("result"), "verdict": dv.get("verdict")})
        if dv.get("result") != 0:
            all_ok = False
        content_ids.append(_run(contentid, str(dp)).strip().splitlines()[-1].strip())

    if not all_ok:
        report["reason"] = "one or more Drops failed verify (result != 0)"
        return report
    if _merkle_root(content_ids) != root or len(set(content_ids)) != member_count:
        report["reason"] = "Drops do not reconstruct the pond head's signed merkle_root/member_count"
        return report

    report["admissible"] = True
    report["reason"] = "all Drops verify and reconstruct the signed pond head"
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cold, self-contained SAVA pond admission gate")
    ap.add_argument("pond_dir", help="directory with pond_head.json and drops/*.json")
    ap.add_argument("--trust", required=True, help="the pond's public key, hex")
    ap.add_argument("--now", required=True, help="ISO8601 timestamp for head expiry check")
    ap.add_argument("--verifier", default=None, help="path to pinned sava_verify.py (default: beside this script)")
    ap.add_argument("--contentid", default=None, help="path to pinned sava_content_id.py (default: beside this script)")
    ap.add_argument("--out", default=None, help="write the JSON report to this file")
    args = ap.parse_args(argv)

    verifier = Path(args.verifier) if args.verifier else _HERE / "sava_verify.py"
    contentid = Path(args.contentid) if args.contentid else _HERE / "sava_content_id.py"
    for tool, flag in ((verifier, "--verifier"), (contentid, "--contentid")):
        if not tool.is_file():
            print(
                f"required tool not found: {tool}\n"
                f"  put sava_verify.py and sava_content_id.py beside sava_gate.py, "
                f"or pass {flag} <path>",
                file=sys.stderr,
            )
            return 2

    report = gate(Path(args.pond_dir), args.trust, str(verifier), str(contentid), args.now)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2))
    else:
        print(("ADMISSIBLE" if report["admissible"] else "REFUSED"), "—", report["reason"])
        for c in report["claims"]:
            print(f"  {c['drop']}: result={c['result']} verdict={c['verdict']}")
    return 0 if report["admissible"] else 1


if __name__ == "__main__":
    sys.exit(main())
