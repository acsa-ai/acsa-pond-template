# AGENTS.md — stand up this pond

You are an agent helping a human run a **fork-a-pond**: a signed, self-hosted
set of claims that can join the A.C.S.A. knowledge lake. This repo already
holds a working example that publishes unmodified — change it into theirs.

**No install.** The two scripts here (`sava_produce.py`, `sava_verify.py`) are
pinned by sha256 and use only the Python 3.10+ standard library. Run them with
`python3`; do not `pip install` anything.

## Integrity first

Before running either script, confirm it matches its pinned hash:
```
python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" sava_produce.py
# expect: 5676242714c34674a6b822188bf7ea0b7ac02926e009a0db5746b43888136175
python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" sava_verify.py
# expect: 4fb6045a01d43912884018285d0e559c1a9560b822d79af1ae5bf1e6b5e9eec6
```
If a hash does not match, stop — do not run it.

## Repository layout

- `src/pond.json` — `{lake_id, pond_id, domain}`. Set `pond_id` to the human's
  chosen name and `domain` to `<pond_id>.ponds.acsa.ai` (the operator pins this
  label; the key is what carries authority).
- `src/claims.json` — the claims. Evidence is **quote-only**: give `source_id`
  and the exact `quote`; the producer finds it in the source and derives the
  offset. Do not hand-write byte locators. The quote must occur once, verbatim.
- `src/sources/<source_id>.txt` — the full text each claim cites.
- `sava_produce.py` / `sava_verify.py` — pinned tools (above).
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

3. **Produce + self-check (locally):**
   ```
   python3 sava_produce.py publish --pond src --key keys/pond.key --out out
   python3 sava_verify.py drop out/drops/<claim>.json --sources out/sources \
     --trust <pubkey-hex> --json
   python3 sava_verify.py head out/pond_head.json --trust <pubkey-hex> --json
   ```
   Expect `"result": 0`. A `source_checkable` claim should show
   `"source_fidelity": "checked-ok"` and `"verdict": "verified"`.

4. **Publish:** commit your edits (not the key). Enable **Settings → Pages →
   Source = GitHub Actions**, add the `POND_SIGNING_KEY` secret
   (`base64 -w0 keys/pond.key`), and push. The workflow republishes the pond at
   `https://<owner>.github.io/<repo>/`.

5. **Register (request admission):**
   ```
   python3 sava_produce.py register --pond src --key keys/pond.key \
     --head-url https://<owner>.github.io/<repo>/pond_head.json --out out
   ```
   Give the human `out/registration.json` to send the lake operator. The
   operator pulls it, re-grounds every claim, and admits the pond only if it
   holds. A live lake to target: https://nike-getto.github.io/acsa-lake.

## The guarantee

Everything you publish is re-derivable by anyone, offline: the signature over
the pond key, the byte-exact quote in the source, and the verdict. You are not
asking anyone to trust the pond — you are handing them a proof.
