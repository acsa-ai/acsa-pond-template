# AGENTS.md — stand up this pond

You are an agent helping a human run a **fork-a-pond**: a signed, self-hosted
set of claims that can join the A.C.S.A. knowledge lake. This repo already
holds a working example that publishes unmodified — change it into theirs.

**No install.** The four scripts here (`sava_produce.py`, `sava_verify.py`,
`sava_content_id.py`, `sava_gate.py`) are pinned by sha256 and use only the
Python 3.10+ standard library. Run them with `python3`; do not `pip install`
anything.

## Integrity first

Before running any script, confirm it matches its pinned hash:
```
python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" sava_produce.py
# expect: fd9a24e2a36d546ec147963e47657b61fab1d9de1dcce618e7e1c3525f7d2714
python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" sava_verify.py
# expect: f76588d6ee80f9ba622afb1f9f4df77fbfe50ac8d1e5bb1c4fafb081cc05eccc
python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" sava_content_id.py
# expect: f7cb109cbd16c1f9d3d509d04b89ac3a1fd2c4bf42715ab98f3f8ab43cdb1a8e
python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" sava_gate.py
# expect: 4c8088f17756a4354db38c789eadcf207ddcc5da80097c4db2c0ed1795df3c32
```
If a hash does not match, stop — do not run it.

## Repository layout

- `src/pond.json` — `{lake_id, pond_id, domain}`. Set `pond_id` to the human's
  chosen name and `domain` to `<pond_id>.ponds.acsa.ai` (the operator pins this
  label; the key is what carries authority).
- `src/claims.json` — the claims. Most claims are **quote-grounded**: give
  `source_id` and the exact `quote`; the producer finds it in the source and
  derives the offset. Do not hand-write byte locators. The quote must occur once,
  verbatim.
  A code fact can instead be **check-grounded**: give a `check` field instead of
  `evidence_refs` — a short deterministic Python snippet that binds `result` to
  `True` (no imports, no I/O; runs under a resource cap). The producer *executes*
  it to grade the claim, and the check source travels on the wire so a verifier
  re-runs it. Example claim:
  `{"id":"c1","text":"sorted([3,1,2]) == [1,2,3]","declared_type":"source_checkable","check":"result = (sorted([3, 1, 2]) == [1, 2, 3])"}`.
  A check that does not execute to `True` grades as `not_established` (never
  `false`). A check-only pond needs no `src/sources/`.
- `src/sources/<source_id>.txt` — the full text each quote-grounded claim cites.
- `sava_produce.py` / `sava_verify.py` / `sava_content_id.py` / `sava_gate.py`
  — pinned tools (above). `sava_gate.py` runs the lake's whole admission gate
  on your pond in one command (step 3).
- `.github/workflows/publish-on-push.yml` — grades, signs, cold-verifies, and
  deploys to GitHub Pages on every push (needs the `POND_SIGNING_KEY` secret).

## Steps

1. **Key (once, locally):** `python3 sava_produce.py keygen --out keys`
   → writes `keys/pond.key` (0600) and prints the public key + fingerprint.
   Never commit `keys/pond.key`. Add it to `.gitignore` if not already ignored.

2. **Author:** edit `src/pond.json`, replace the example in `src/claims.json`
   with the human's claims, and put each cited source text under
   `src/sources/`. Keep `declared_type` honest: `source_checkable` for a fact a
   quote grounds; `opinion` / `forward_looking` / `external` otherwise (those
   verify as `not_established` by design — that is correct, not a failure).

3. **Produce, then self-gate (locally):**
   ```
   python3 sava_produce.py publish --pond src --key keys/pond.key --out out
   # gate your whole pond the same way the lake will — one command:
   python3 -S sava_gate.py out --trust <pubkey-hex> --now <ISO8601>
   # -> ADMISSIBLE — all Drops verify and reconstruct the signed pond head  (exit 0)
   ```
   **`ADMISSIBLE` means the lake will admit it too** — the gate is deterministic,
   so this is your real go/no-go before submitting. For per-Drop detail,
   `sava_verify.py drop out/drops/<claim>.json --sources out/sources --trust
   <pubkey-hex> --json` and `sava_verify.py head …` give `"result": 0` (a
   `source_checkable` claim shows `"source_fidelity": "checked-ok"` and
   `"verdict": "verified"`).

4. **Publish:** commit your edits (not the key). Enable **Settings → Pages →
   Source = GitHub Actions**, add the `POND_SIGNING_KEY` secret
   (`base64 -w0 keys/pond.key`), and push. The workflow republishes the pond at
   `https://<owner>.github.io/<repo>/` and writes `pubkey.hex` beside
   `pond_head.json`, so anyone can anchor your key (`sha256(pubkey)[:16]` equals
   the head's `key_fingerprint`) and cold-verify the pond from its own URL.
   Hosting somewhere other than GitHub Pages? Publish `pubkey.hex` yourself:
   `echo <public_key_hex from keygen> > out/pubkey.hex`.

5. **Register + submit:**
   ```
   python3 sava_produce.py register --pond src --key keys/pond.key \
     --head-url https://<owner>.github.io/<repo>/pond_head.json --out out
   ```
   Submit `out/registration.json` by opening a pull request that adds it as
   `submissions/<domain>.json` to **github.com/acsa-ai/acsa-lake** (see that
   repo's `submissions/README.md`). The lake pulls your pond, re-runs the same
   gate you ran in step 3, and admits it on a pass — there is no CI check to wait
   on. **Confirmation is a signature, not a badge:** your pond appears in the
   signed lake head at https://acsa.ai/lake, re-verifiable by anyone.

## The guarantee

Everything you publish is re-derivable by anyone, offline: the signature over
the pond key, the byte-exact quote in the source, and the verdict. You are not
asking anyone to trust the pond — you are handing them a proof.
