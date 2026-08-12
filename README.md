# Fork-a-Pond — your own signed, verifiable claim set

This is a **template repository**. Click **“Use this template”** and you have
a working *pond*: a small, self-hosted, cryptographically signed set of claims,
each carrying the evidence that grounds it. Anyone can re-derive every verdict
**cold — with nothing installed beyond `python3`.**

A pond can then join a **lake** (an authority that pulls ponds in only after
re-grounding every claim). One is already live:
**https://acsa-ai.github.io/acsa-lake**.

Nothing here needs `pip`. The two scripts you run — `sava_produce.py` (grade +
sign) and `sava_verify.py` (verify) — are pinned by sha256 and use only the
Python standard library.

---

## Quickstart (about 5 minutes)

1. **Use this template** → create your repo.

2. **Make a signing key** (locally, once):
   ```
   python3 sava_produce.py keygen --out keys
   ```
   This writes `keys/pond.key` (a raw 32-byte seed, mode 0600) and prints your
   public key + fingerprint. **Never commit `keys/pond.key`.**

3. **Give the Action your key as a secret** so it can re-sign on every push:
   ```
   base64 -w0 keys/pond.key     # Linux   (macOS: base64 keys/pond.key)
   ```
   Copy the output into **Settings → Secrets and variables → Actions → New
   repository secret**, named `POND_SIGNING_KEY`.

4. **Name your pond.** Edit `src/pond.json`:
   ```json
   { "lake_id": "acsa.ai", "pond_id": "your-pond-id",
     "domain": "your-pond-id.ponds.acsa.ai" }
   ```
   The `domain` is a label the lake operator pins for you (convention:
   `<pond_id>.ponds.acsa.ai`); your real authority is your key, not the name.

5. **Write your claims.** Edit `src/claims.json`. Each claim cites a quote from
   a source file in `src/sources/`. **You do not compute byte offsets** — write
   the quote and the producer finds it:
   ```json
   [{ "id": "c-1",
      "text": "Your factual, checkable claim.",
      "declared_type": "source_checkable",
      "evidence_refs": [{ "source_id": "mysrc",
                          "quote": "the exact sentence from the source" }],
      "licensed_source_ids": ["mysrc"] }]
   ```
   Drop the full source text at `src/sources/mysrc.txt`. (The quote must appear
   **once**, verbatim; otherwise `publish` tells you and stops.)

6. **Enable Pages:** Settings → Pages → Source = **GitHub Actions**. Push. The
   `publish-on-push` workflow grades, signs, **cold-verifies**, and publishes
   your pond at `https://<you>.github.io/<repo>/`.

7. **Ask to join the lake.** Once your pond is live, self-sign a registration
   and send it to the operator:
   ```
   python3 sava_produce.py register --pond src --key keys/pond.key \
     --head-url https://<you>.github.io/<repo>/pond_head.json --out out
   ```
   Hand them `out/registration.json` (a link, not an API call). They pull it,
   re-ground every claim, and — if it holds — pin your key and admit you.

---

## Verify it yourself, cold

You never have to trust this repo. From the published pond, with only
`python3`:
```
python3 sava_verify.py drop drops/<claim>.json --sources sources --trust <your-pubkey-hex>
python3 sava_verify.py head pond_head.json --trust <your-pubkey-hex>
#   -> {"result": 0, "source_fidelity": "checked-ok", "verdict": "verified"}
```
`result 0` means the signature checked, the quote is byte-exact in the source,
and the verdict was re-derived — not taken on faith.

## What ships here

| path | what it is |
|------|------------|
| `src/pond.json` | your pond's id + domain label |
| `src/claims.json` | your claims (quote-only evidence; a working example ships) |
| `src/sources/` | one `.txt` per cited source |
| `sava_produce.py` | pinned, stdlib-only producer: `keygen` / `publish` / `register` |
| `sava_verify.py` | pinned, stdlib-only offline verifier |
| `.github/workflows/publish-on-push.yml` | grade → sign → cold-verify → Pages |

## More

- **Agent-driven?** See [`AGENTS.md`](AGENTS.md) — the same steps, written for
  your coding agent to run.
- **Full protocol + operator side:** the engine’s front door,
  `docs/onboarding/AGENTS.md` in the A.C.S.A. engine repo.
