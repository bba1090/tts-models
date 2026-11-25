"""Download licensed Adobe Stock files from short-lived presigned URLs and
transcode them to small 1080p clips. Input: JSON list via env STOCK_ITEMS.
Only S3 presigned URLs are accepted; ids must be numeric; sizes are capped."""
import json, os, re, subprocess, sys, urllib.request, pathlib

URL_RE = re.compile(r"^https://[a-z0-9.-]+\.s3\.[a-z0-9-]+\.amazonaws\.com/[^\s]+$")
ID_RE = re.compile(r"^[0-9]{5,12}$")
MAX_BYTES, MAX_ITEMS = 900 * 1024 * 1024, 20

def fail(m): print(f"invalid: {m}", file=sys.stderr); sys.exit(2)

items = json.loads(os.environ["STOCK_ITEMS"])
if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS: fail("items")
for it in items:
    if not (isinstance(it, dict) and ID_RE.match(str(it.get("id",""))) and
            it.get("kind") in ("video","photo","audio") and URL_RE.match(str(it.get("url","")))): fail("item")
    print(f"::add-mask::{it['url']}")          # keep signed URLs out of the log

out = pathlib.Path("stock"); out.mkdir(exist_ok=True); raw = pathlib.Path("raw"); raw.mkdir(exist_ok=True)
for it in items:
    src = raw / it["id"]
    with urllib.request.urlopen(it["url"], timeout=120) as r, open(src, "wb") as f:
        n = 0
        while chunk := r.read(1 << 20):
            n += len(chunk)
            if n > MAX_BYTES: fail(f"too large {it['id']}")
            f.write(chunk)
    if it["kind"] == "video":
        cmd = ["ffmpeg","-y","-loglevel","error","-i",str(src),"-t","15","-an",
               "-vf","scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30",
               "-c:v","libx264","-crf","20","-preset","veryfast","-pix_fmt","yuv420p",str(out/f"{it['id']}.mp4")]
    elif it["kind"] == "audio":   # cap at 5 minutes, normalised format
        cmd = ["ffmpeg","-y","-loglevel","error","-i",str(src),"-t","300","-vn","-ar","48000","-ac","2",
               "-c:a","pcm_s16le",str(out/f"{it['id']}.wav")]
    else:
        cmd = ["ffmpeg","-y","-loglevel","error","-i",str(src),"-vf","scale=2880:-2","-q:v","3",str(out/f"{it['id']}.jpg")]
    subprocess.run(cmd, check=True)
    print(f"ok {it['id']} {n//1024} KB")
