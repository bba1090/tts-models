"""Generate speech for one job file with edge-tts.

Job file (tts-jobs/<name>.json):
  {"name": "intro-v1", "items": [{"id": "s01", "voice": "zh-TW-YunJheNeural",
                                   "rate": "+0%", "text": "..."}]}
All fields are validated against allow-lists; text is passed to edge-tts as data,
never to a shell.
"""
import asyncio, json, re, sys, pathlib
import edge_tts

VOICES = {"zh-TW-YunJheNeural", "zh-TW-HsiaoChenNeural", "zh-TW-HsiaoYuNeural"}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
ID_RE = re.compile(r"^[a-z0-9_-]{1,20}$")
RATE_RE = re.compile(r"^[+-](?:[0-9]|[1-4][0-9]|50)%$")   # -50% .. +50%
MAX_ITEMS, MAX_CHARS = 60, 500

def fail(msg):
    print(f"invalid job: {msg}", file=sys.stderr); sys.exit(2)

def load(path):
    job = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    name = job.get("name", "")
    if not isinstance(name, str) or not NAME_RE.match(name): fail("name")
    items = job.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS: fail("items")
    seen = set()
    for it in items:
        if not isinstance(it, dict): fail("item type")
        if not ID_RE.match(str(it.get("id", ""))) or it["id"] in seen: fail("id")
        seen.add(it["id"])
        if it.get("voice") not in VOICES: fail("voice")
        if not RATE_RE.match(str(it.get("rate", "+0%"))): fail("rate")
        t = it.get("text")
        if not isinstance(t, str) or not 1 <= len(t) <= MAX_CHARS: fail("text")
    return name, items

async def main(path, outdir):
    name, items = load(path)
    out = pathlib.Path(outdir) / name
    out.mkdir(parents=True, exist_ok=True)
    for it in items:
        c = edge_tts.Communicate(it["text"], it["voice"], rate=it.get("rate", "+0%"))
        await c.save(str(out / f"{it['id']}.mp3"))
        print(f"ok {it['id']}")
    (out / "job.json").write_text(json.dumps({"name": name, "items": items},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print(name)

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
