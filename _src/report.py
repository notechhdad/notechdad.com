"""Print what changed on the site, old -> new, for the refresh report.

    python3 _src/report.py              # uncommitted changes (working tree against HEAD)
    python3 _src/report.py 15da32d      # everything since that commit, including today's commits

Write the report from this output, never from memory, and quote values exactly as printed here.
It reads only the source data (build.py, data/*.json, news_body.html), never the generated pages.
"""
import ast, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = {"build": "_src/build.py", "prices": "_src/data/prices.json",
         "videos": "_src/data/videos.json", "news": "_src/web/pages/news_body.html"}


def old_text(ref, path):
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def new_text(path):
    p = ROOT / path
    return p.read_text(encoding="utf-8") if p.exists() else ""


def literals(src):
    out = {}
    if not src:
        return out
    for n in ast.parse(src).body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            name = n.targets[0].id
            if name in ("DATES", "DRIVERS", "CHIPSET", "BLURBS"):
                try:
                    out[name] = ast.literal_eval(n.value)
                except ValueError:
                    pass
    return out


def arrow(a, b):
    return f"{a} -> {b}" if a != b else f"{b} (unchanged)"


def money(v, cur):
    if v is None:
        return "blank"
    return f"¥{v:,}" if cur == "JPY" else f"${v:,}"


def report_dates(o, n):
    print("DATES")
    for k in n.get("DATES", {}):
        print(f"  {k}: {arrow(o.get('DATES', {}).get(k), n['DATES'][k])}")


def report_drivers(o, n):
    print("\nDRIVERS (version, status, release date)")
    old = {d[0]: d for d in o.get("DRIVERS", [])}
    if "CHIPSET" in o:
        old[o["CHIPSET"][0]] = o["CHIPSET"]
    rows = list(n.get("DRIVERS", [])) + ([n["CHIPSET"]] if "CHIPSET" in n else [])
    for d in rows:
        was = old.get(d[0])
        a = " · ".join(str(x or "-") for x in (was[2], was[3], was[4])) if was else "(new row)"
        b = " · ".join(str(x or "-") for x in (d[2], d[3], d[4]))
        print(f"  {d[0]}: {arrow(a, b)}")
        if was and was[5] != d[5]:
            print("    note changed")
        if was and was[6] != d[6]:
            print(f"    links: {[u for _, u in d[6]]}")


def point_key(p):
    return p.get("month") or p.get("date")


def point_desc(p, cur):
    s = money(p.get("value"), cur)
    if p.get("to"):
        s += f" (partial, to {p['to']})"
    if p.get("label"):
        s += f" [{p['label']}]"
    return s


def report_prices(old_src, new_src):
    print("\nPRICES")
    o = json.loads(old_src) if old_src else {"series": []}
    n = json.loads(new_src) if new_src else {"series": []}
    print(f"  checked: {arrow(o.get('checked'), n.get('checked'))}")
    old_series = {s["id"]: s for s in o["series"]}
    for s in n["series"]:
        cur = s.get("currency", "USD")
        was = old_series.get(s["id"], {"points": []})
        op = {point_key(p): p for p in was["points"]}
        lines = []
        for p in s["points"]:
            k = point_key(p)
            if k not in op:
                lines.append(f"{k}: ADDED {point_desc(p, cur)}")
            elif op[k] != p:
                ov, nv = op[k].get("value"), p.get("value")
                change = ""
                if isinstance(ov, (int, float)) and isinstance(nv, (int, float)) and ov != nv:
                    d = nv - ov
                    change = f"  ({'up' if d > 0 else 'down'} {money(abs(d), cur)})"
                lines.append(f"{k}: {point_desc(op[k], cur)} -> {point_desc(p, cur)}{change}")
        for k in op:
            if k not in {point_key(p) for p in s["points"]}:
                lines.append(f"{k}: REMOVED {point_desc(op[k], cur)}")
        for f in ("context", "flag", "msrp"):
            if was.get(f) != s.get(f):
                lines.append(f"{f}: {was.get(f)!r} -> {s.get(f)!r}")
        print(f"  {s['id']}: " + ("no change" if not lines else ""))
        for line in lines:
            print(f"    {line}")


def report_videos(old_src, new_src, o, n):
    print("\nVIDEOS")
    ov = json.loads(old_src) if old_src else {"videos": []}
    nv = json.loads(new_src) if new_src else {"videos": []}
    print(f"  checked: {arrow(ov.get('checked'), nv.get('checked'))}")
    old = {v["id"]: v for v in ov["videos"]}
    added = [v for v in nv["videos"] if v["id"] not in old]
    removed = [i for i in old if i not in {v["id"] for v in nv["videos"]}]
    print(f"  count: {arrow(len(ov['videos']), len(nv['videos']))}")
    for v in added:
        blurb = "has blurb" if v["id"] in n.get("BLURBS", {}) else "NO BLURB"
        print(f"  ADDED {v['id']} {v['published']} {v['seconds']}s {v['views']:,} views, {blurb}: {v['title']}")
    for i in removed:
        print(f"  REMOVED {i}: {old[i]['title']}")
    moved = [(v, old[v["id"]]["views"]) for v in nv["videos"] if v["id"] in old and old[v["id"]]["views"] != v["views"]]
    print(f"  view counts changed: {len(moved)}")
    for v, was in sorted(moved, key=lambda t: -abs(t[0]["views"] - t[1]))[:5]:
        print(f"    {v['id']}: {was:,} -> {v['views']:,}  {v['title'][:60]}")


ITEM = re.compile(r'<time datetime="([^"]+)">[^<]*</time>\s*<div>\s*<div class="nh"><span class="tag[^"]*">([^<]*)</span><h3>([^<]*)</h3>')
TL = re.compile(r'<li><time datetime="([^"]+)">[^<]*</time><p>(?:<b class="flag">([^<]*)</b>)?([^<]{0,90})')


def report_news(old_src, new_src):
    print("\nNEWS")
    oi, ni = set(ITEM.findall(old_src)), ITEM.findall(new_src)
    ot, nt = set(TL.findall(old_src)), TL.findall(new_src)
    new_items = [i for i in ni if i not in oi]
    new_tl = [t for t in nt if t not in ot]
    if not new_items and not new_tl:
        print("  no new items")
    for d, tag, h in new_items:
        print(f"  ADDED {d} [{tag}] {h}")
    for d, flag, text in new_tl:
        print(f"  ADDED topic line {d} {('[' + flag + '] ') if flag else ''}{text.strip()}...")


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    print(f"Changes since {ref} (old -> new)\n")
    ob, nb = old_text(ref, FILES["build"]), new_text(FILES["build"])
    o, n = literals(ob), literals(nb)
    report_dates(o, n)
    report_drivers(o, n)
    report_prices(old_text(ref, FILES["prices"]), new_text(FILES["prices"]))
    report_videos(old_text(ref, FILES["videos"]), new_text(FILES["videos"]), o, n)
    report_news(old_text(ref, FILES["news"]), new_text(FILES["news"]))


if __name__ == "__main__":
    main()
