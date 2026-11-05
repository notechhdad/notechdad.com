"""Hardware price tracker: RAM, graphics cards and NVMe SSDs, month by month since January 2026.

Data: _src/data/prices.json (see the README). Every point comes from the source named on its series, by that
source's own method. Charts are inline SVG built here, so they render without scripts; TRACKER_JS only adds the
hover and keyboard readout. Colours come from the site's CSS tokens, so both themes work: the line and the
current-price marker use the accent (--red), and all text uses text tokens.

A point is either a monthly figure, {"month": "2026-03", "value": 649}, drawn at mid-month, or a dated reading,
{"date": "2026-10-24", "label": "17–24 Oct 2026", "value": 72980}, drawn on its date (a survey's last day) and
shown with its label. A month still in progress is a monthly figure with "to": "2026-11-03"; it is drawn on that
date and labelled "1–3 Nov 2026". A null value means the source has no reading that month. Any point may carry
"url", the page its value was read on.
"""
import calendar
import html
import json
from datetime import date

e = html.escape
YEAR_START = date(2026, 1, 1)
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
        "November", "December"]
GAP_DAYS = 45            # a longer gap between two readings breaks the line instead of bridging it


def load(path):
    data = json.loads(path.read_text())
    for s in data["series"]:
        pts = []
        for p in s["points"]:
            if p.get("value") is None:
                continue
            if p.get("date"):
                d = date.fromisoformat(p["date"])
                p["label"] = p.get("label") or f"{d.day} {MONTHS[d.month - 1]} {d.year}"
                p["ym"] = (d.year, d.month)
            else:
                y, m = map(int, p["month"].split("-"))
                p["ym"] = (y, m)
                if p.get("to"):
                    d = date.fromisoformat(p["to"])
                    p["label"] = p.get("label") or f"1–{d.day} {MONTHS[m - 1]} {y}"
                    p["partial"] = True
                else:
                    d = date(y, m, 15)
                    p["label"] = p.get("label") or f"{MONTHS[m - 1]} {y}"
            p["d"] = d
            pts.append(p)
        s["points"] = sorted(pts, key=lambda p: p["d"])
    return data


SYMBOL = {"USD": "$", "JPY": "¥"}


def money(v, cur="USD", cents=False, compact=False):
    sym = SYMBOL.get(cur, cur + " ")
    if compact and abs(v) >= 10000:
        k = v / 1000
        return f"{sym}{k:,.0f}K" if abs(k - round(k)) < 0.05 else f"{sym}{k:,.1f}K"
    if cents and abs(v - round(v)) > 0.004:
        return f"{sym}{v:,.2f}"
    return f"{sym}{round(v):,}"


def change(s):
    """(percent change from the first reading to the latest, first, latest)."""
    first, last = s["points"][0], s["points"][-1]
    return (last["value"] - first["value"]) / first["value"] * 100, first, last


def since(p, full=False):
    """The month of a reading: each series has at most one reading per month."""
    return (FULL if full else MONTHS)[p["ym"][1] - 1]


def delta_html(pct, start):
    if abs(pct) < 0.5:
        cls, arrow, txt = "pt-flat", "–", "no change"
    elif pct > 0:
        cls, arrow, txt = "pt-up", "▲", f"+{pct:.0f}%"
    else:
        cls, arrow, txt = "pt-down", "▼", f"{pct:.0f}%"
    return (f'<span class="pt-delta {cls}"><span aria-hidden="true">{arrow}</span> {txt} '
            f'<span class="pt-since">since {e(start)}</span></span>')


def nice_max(v):
    """Round an axis maximum up so its four equal steps are round numbers (1, 1.5, 2, 2.5, 3, 4, 5, 6 or 8 × 10ⁿ)."""
    raw = v / 4
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 1
    for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        step = m * mag
        if step * 4 >= v:
            return step * 4, step
    return v, v / 4


def segments(pts):
    segs, cur = [], [pts[0]]
    for a, b in zip(pts, pts[1:]):
        if (b["d"] - a["d"]).days > GAP_DAYS:
            segs.append(cur)
            cur = []
        cur.append(b)
    segs.append(cur)
    return segs


def chart_svg(s, cid, end, w=320, h=176, compact=False):
    """Line chart of one series on a shared time axis (1 Jan 2026 to `end`), with a zero-based y axis."""
    top, right, bottom, left = (8, 6, 6, 6) if compact else (26, 16, 24, 46)
    pw, ph = w - left - right, h - top - bottom
    days = (end - YEAR_START).days
    ref = s.get("msrp")
    pts = s["points"]
    cur = s.get("currency", "USD")
    vmax = max([p["value"] for p in pts] + ([ref["value"]] if ref else []))
    ymax, step = (vmax * 1.1, 0) if compact else nice_max(vmax * 1.08)

    def X(d):
        return left + (d - YEAR_START).days / days * pw

    def Y(v):
        return top + ph - v / ymax * ph

    segs = segments(pts)
    lines, areas = [], []
    for seg in segs:
        xy = [(X(p["d"]), Y(p["value"])) for p in seg]
        path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in xy)
        lines.append(f'<path class="pt-line" d="{path}"/>')
        if len(seg) > 1:
            base = Y(0)
            areas.append(f'<path class="pt-area" d="{path} L{xy[-1][0]:.1f},{base:.1f} L{xy[0][0]:.1f},{base:.1f} Z"/>')

    out = []
    last = pts[-1]
    lx, ly = X(last["d"]), Y(last["value"])
    if not compact:
        v = 0
        while v <= ymax + 1e-9:
            y = Y(v)
            out.append(f'<line class="{"pt-base" if v == 0 else "pt-grid"}" x1="{left}" x2="{w - right}" '
                       f'y1="{y:.1f}" y2="{y:.1f}"/>')
            out.append(f'<text class="pt-ytick" x="{left - 6}" y="{y + 3.5:.1f}" text-anchor="end">{money(v, cur, compact=ymax >= 10000)}</text>')
            v += step
        m = 1
        while m <= 12 and date(2026, m, 1) <= end:
            if m % 2 == 1:
                out.append(f'<text class="pt-xtick" x="{X(date(2026, m, 1)):.1f}" y="{h - 7}" '
                           f'text-anchor="middle">{MONTHS[m - 1]}</text>')
            m += 1
        if ref:
            y = Y(ref["value"])
            below = last["value"] >= ref["value"]      # the label sits on the side of the line the latest price isn't
            out.append(f'<line class="pt-ref" x1="{left}" x2="{w - right}" y1="{y:.1f}" y2="{y:.1f}"/>')
            out.append(f'<text class="pt-reflabel" x="{w - right - 2}" y="{y + 12 if below else y - 5:.1f}" '
                       f'text-anchor="end">{e(ref.get("label", "MSRP"))} {money(ref["value"], cur)}</text>')
    out += areas + lines
    for seg in segs:                                   # a reading with no neighbour on either side still shows
        if len(seg) == 1 and seg[0] is not last:
            out.append(f'<circle class="pt-lone" cx="{X(seg[0]["d"]):.1f}" cy="{Y(seg[0]["value"]):.1f}" r="3"/>')
    if compact:
        out.append(f'<circle class="pt-now" cx="{lx:.1f}" cy="{ly:.1f}" r="3.5"/>')
        return (f'<svg class="pt-spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true" '
                f'focusable="false">{"".join(out)}</svg>')
    if len(segs[0]) > 1:
        out.append(f'<circle class="pt-start" cx="{X(pts[0]["d"]):.1f}" cy="{Y(pts[0]["value"]):.1f}" r="3.5"/>')
    out.append(f'<circle class="pt-halo" cx="{lx:.1f}" cy="{ly:.1f}" r="11"/>')
    out.append(f'<circle class="pt-now" cx="{lx:.1f}" cy="{ly:.1f}" r="5"/>')
    out.append(f'<text class="pt-nowlabel" x="{min(lx, w - right - 2):.1f}" y="{max(ly - 15, 11):.1f}" '
               f'text-anchor="end">{money(last["value"], cur)}</text>')
    out.append(f'<line class="pt-x" x1="0" x2="0" y1="{top}" y2="{top + ph}" visibility="hidden"/>')
    out.append('<circle class="pt-f" r="4.5" cx="0" cy="0" visibility="hidden"/>')
    pct, first, _ = change(s)
    summary = (f"{s['title']}: {money(first['value'], cur)} in {first['label']}, {money(last['value'], cur)} in "
               f"{last['label']}, {'up' if pct >= 0 else 'down'} {abs(pct):.0f}%.")
    data = json.dumps([[round(X(p["d"]), 1), round(Y(p["value"]), 1), p["label"], money(p["value"], cur, True)]
                       for p in pts])
    return (f'<svg class="pt-svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{cid}-t" tabindex="0" '
            f'data-pts="{e(data)}"><title id="{cid}-t">{e(summary)}</title>{"".join(out)}</svg>')


def cat(s):
    return f'{s["category"]} · {s["market"]}' if s.get("market") else s["category"]


def card(s, end):
    pct, first, last = change(s)
    ref = s.get("msrp")
    cur = s.get("currency", "USD")
    over = ""
    if ref:
        o = (last["value"] - ref["value"]) / ref["value"] * 100
        over = (f'<span class="pt-over">{"+" if o >= 0 else ""}{o:.0f}% vs {e(ref.get("label", "MSRP"))} '
                f'{money(ref["value"], cur)}</span>')
    ctx = ""
    if s.get("context"):
        link = (f' <a class="inline" href="{e(s["context_url"])}" target="_blank" rel="noopener">'
                f'{e(s["context_src"])}&nbsp;↗</a>') if s.get("context_url") else ""
        ctx = f'\n          <p class="pt-ctx">{e(s["context"])}{link}</p>'
    cid = f'pt-{s["id"]}'
    return f"""        <figure class="pt-card" id="{cid}">
          <p class="pt-cat">{e(cat(s))}</p>
          <h3 class="pt-title">{e(s["title"])}</h3>
          <p class="pt-now-row"><span class="pt-price">{money(last["value"], cur)}</span><span class="pt-when">{e(last["label"])}</span></p>
          <p class="pt-metric">{e(s["metric"])}</p>
          <p class="pt-deltas">{delta_html(pct, since(first))}{over}</p>
          <div class="pt-chart">{chart_svg(s, cid, end)}<div class="pt-tip" hidden></div></div>{ctx}
          <figcaption class="pt-src">{e(s["region"])} · Source: <a href="{e(s["source_url"])}" target="_blank" rel="noopener">{e(s["source_name"])}&nbsp;↗</a></figcaption>
        </figure>"""


def more_rows(series, end):
    rows = []
    for s in series:
        pct, first, last = change(s)
        ref = s.get("msrp")
        cur = s.get("currency", "USD")
        msrp = f'<span class="pm-msrp">MSRP {money(ref["value"], cur)}</span>' if ref else ""
        flag = ""
        if s.get("flag"):
            txt = e(s["flag"])
            if s.get("flag_url"):
                txt = f'<a class="inline" href="{e(s["flag_url"])}" target="_blank" rel="noopener">{txt}&nbsp;↗</a>'
            flag = f'<span class="pm-flag">{txt}</span>'
        rows.append(f'<li><span class="pm-name">{e(s["title"])}{msrp}</span>'
                    f'<span class="pm-spark">{chart_svg(s, "x", end, w=120, h=44, compact=True)}</span>'
                    f'<span class="pm-vals"><span class="pm-was">{money(first["value"], cur)} <small>{e(since(first))}</small></span>'
                    f'<span aria-hidden="true"> → </span><b>{money(last["value"], cur)}</b> <small>{e(since(last))}</small></span>'
                    f'<span class="pm-change">{delta_html(pct, since(first))}{flag}</span></li>')
    return '<ul class="pt-more">' + "".join(rows) + "</ul>"


def cell(s, p):
    """A table value. It links to its own report when each reading has one; a single page per series is linked in
    the notes instead, so the table isn't a wall of identical links."""
    v = money(p["value"], s.get("currency", "USD"), True)
    if p.get("url") and len({q.get("url") for q in s["points"]}) > 1:
        v = f'<a class="inline" href="{e(p["url"])}" target="_blank" rel="noopener">{v}</a>'
    if p.get("partial") or "date" in p:
        note = p["label"].removesuffix(f' {p["d"].year}')
        v += f' <span class="pt-d">{e(note)}</span>'
    return v


def table_view(series):
    months = sorted({p["ym"] for s in series for p in s["points"]})
    head = "".join(f'<th scope="col">{e(s["title"])}</th>' for s in series)
    body = []
    for y, m in months:
        cells = []
        for s in series:
            hit = [p for p in s["points"] if p["ym"] == (y, m)]
            if hit:
                cells.append("<td>" + "<br>".join(cell(s, p) for p in hit) + "</td>")
            else:
                cells.append('<td class="pt-na">no reading</td>')
        body.append(f'<tr><th scope="row">{MONTHS[m - 1]} {y}</th>{"".join(cells)}</tr>')
    return (f'<details class="pt-table"><summary>See every reading</summary><div class="tbl"><table>'
            f'<thead><tr><th scope="col">Month</th>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div></details>')


def and_list(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def sources(series):
    """One note per source and method, naming every product it covers."""
    groups = {}
    for s in series:
        groups.setdefault((s["source_name"], s["method"]), []).append(s)
    items = []
    for (name, method), ss in groups.items():
        titles = and_list([e(s["title"]) for s in ss])
        cav = "".join(f' {e(s["caveats"])}' for s in ss if s.get("caveats"))
        links = [f'<a class="inline" href="{e(s["source_url"])}" target="_blank" rel="noopener">'
                 f'{e(s["title"]) if len(ss) > 1 else e(name)}</a>' for s in ss]
        src = f'{e(name)} ({", ".join(links)})' if len(ss) > 1 else links[0]
        items.append(f'<li><b>{titles}.</b> {e(method)}{cav} Source: {src}.</li>')
    return '<ul class="pt-notes">' + "".join(items) + "</ul>"


def end_date(data):
    last = max(p["d"] for s in data["series"] for p in s["points"])
    return date(last.year, last.month, calendar.monthrange(last.year, last.month)[1])


def headline(data):
    parts = []
    for s in data["series"]:
        if s.get("featured"):
            pct, first, _ = change(s)
            month = e(since(first, full=True))
            if abs(pct) < 0.5:
                moved = f"is unchanged since {month}"
            else:
                moved = f'has {"risen" if pct > 0 else "fallen"} {abs(pct):.0f}% since {month}'
            parts.append(f'{e(s["short"])} {moved}')
    if not parts:
        return ""
    text = and_list(parts) + "."
    return text[0].upper() + text[1:]


def news_section(data, checked_label):
    end = end_date(data)
    featured = [s for s in data["series"] if s.get("featured")]
    others = [s for s in data["series"] if not s.get("featured")]
    cards = "\n".join(card(s, end) for s in featured)
    more = ""
    if others:
        more = f'\n      <h3 class="subhead-label pt-more-h">More graphics cards</h3>\n      {more_rows(others, end)}'
    return f"""      <section class="pt" id="prices" aria-labelledby="prices-title">
        <div class="pt-head">
          <h2 class="pt-h" id="prices-title">Price tracker</h2>
          <p class="pt-lead">What the same parts have cost each month since January, with the latest price highlighted. {headline(data)}</p>
          <p class="pt-checked">Checked {e(checked_label)}. {e(data.get("note", ""))}</p>
        </div>
        <div class="pt-grid">
{cards}
        </div>{more}
      {table_view(data["series"])}
      <h3 class="subhead-label pt-more-h">How these are tracked</h3>
      {sources(data["series"])}
      </section>"""


def home_strip(data):
    end = end_date(data)
    tiles = []
    for s in data["series"]:
        if not s.get("featured"):
            continue
        pct, first, last = change(s)
        tiles.append(f'<li><a href="news.html#pt-{e(s["id"])}"><span class="ps-cat">{e(cat(s))}</span>'
                     f'<span class="ps-name">{e(s["title"])}</span>'
                     f'<span class="ps-row"><span class="ps-price">{money(last["value"], s.get("currency", "USD"))}</span>'
                     f'{chart_svg(s, "x", end, w=120, h=44, compact=True)}</span>{delta_html(pct, since(first))}</a></li>')
    return ('      <div class="ps">\n        <div class="ps-head"><h3 class="subhead-label">Price tracker</h3>'
            '<a class="more" href="news.html#prices">Full tracker →</a></div>\n'
            f'        <ul class="ps-tiles">{"".join(tiles)}</ul>\n      </div>')


TRACKER_JS = r"""
document.querySelectorAll('svg.pt-svg').forEach(function (svg) {
  // Hover or arrow keys: a crosshair snaps to the nearest reading and the readout shows its date and price.
  var pts = JSON.parse(svg.getAttribute('data-pts')), tip = svg.parentNode.querySelector('.pt-tip');
  var cross = svg.querySelector('.pt-x'), dot = svg.querySelector('.pt-f'), cur = pts.length - 1;
  function show(i) {
    cur = i;
    var p = pts[i];
    cross.setAttribute('x1', p[0]); cross.setAttribute('x2', p[0]); cross.setAttribute('visibility', 'visible');
    dot.setAttribute('cx', p[0]); dot.setAttribute('cy', p[1]); dot.setAttribute('visibility', 'visible');
    tip.replaceChildren();
    var b = document.createElement('b'); b.textContent = p[3];
    var s = document.createElement('span'); s.textContent = p[2];
    tip.append(b, s);
    tip.hidden = false;
    var box = svg.getBoundingClientRect(), host = svg.parentNode.getBoundingClientRect();
    var vb = svg.viewBox.baseVal, x = box.left - host.left + p[0] / vb.width * box.width;
    var y = box.top - host.top + p[1] / vb.height * box.height;
    var w = tip.offsetWidth, left = Math.min(Math.max(x - w / 2, 0), host.width - w);
    tip.style.left = left + 'px';
    tip.style.top = Math.max(y - tip.offsetHeight - 12, 0) + 'px';
  }
  function hide() {
    cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); tip.hidden = true;
  }
  function nearest(ev) {
    var box = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
    var x = (ev.clientX - box.left) / box.width * vb.width, best = 0;
    pts.forEach(function (p, i) { if (Math.abs(p[0] - x) < Math.abs(pts[best][0] - x)) best = i; });
    return best;
  }
  svg.addEventListener('pointermove', function (ev) { show(nearest(ev)); });
  svg.addEventListener('pointerdown', function (ev) { show(nearest(ev)); });
  svg.addEventListener('pointerleave', hide);
  svg.addEventListener('focus', function () { show(pts.length - 1); });
  svg.addEventListener('blur', hide);
  svg.addEventListener('keydown', function (ev) {
    if (ev.key === 'ArrowLeft' && cur > 0) { show(cur - 1); ev.preventDefault(); }
    else if (ev.key === 'ArrowRight' && cur < pts.length - 1) { show(cur + 1); ev.preventDefault(); }
    else if (ev.key === 'Home') { show(0); ev.preventDefault(); }
    else if (ev.key === 'End') { show(pts.length - 1); ev.preventDefault(); }
    else if (ev.key === 'Escape') { hide(); }
  });
});
"""
