"""Cell tables + pass/fail from ts1_events.parquet.
Cells: pooled + temporal thirds (y1..y3 over global span) + crc32(symbol)%2 halves.
Paired stat: x_i = r_i - nullmean_i; z = mean(x)/sem(x). PASS = lift same-sign all 5 cells."""
import numpy as np, pandas as pd
from zlib import crc32
SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"

ev = pd.read_parquet(f"{SCR}/ts1_events.parquet")
ev["ts"] = pd.to_datetime(ev["ts"], utc=True)
t0, t1 = ev.ts.min(), ev.ts.max()
cut1, cut2 = t0 + (t1 - t0) / 3, t0 + 2 * (t1 - t0) / 3
ev["third"] = np.where(ev.ts <= cut1, "y1", np.where(ev.ts <= cut2, "y2", "y3"))
ev["half"] = ["h" + str(crc32(s.encode()) % 2) for s in ev.symbol]

def cellstats(d):
    if len(d) == 0: return dict(n=0, rate=np.nan, null=np.nan, lift=np.nan, z=np.nan)
    x = (d.r - d.nullm).values
    n = len(x); m = x.mean()
    se = x.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return dict(n=n, rate=d.r.mean(), null=d.nullm.mean(), lift=m,
                z=m / se if se and se > 0 else np.nan)

def table(d, name):
    rows = [dict(cell="pooled", **cellstats(d))]
    for c in ("y1", "y2", "y3"): rows.append(dict(cell=c, **cellstats(d[d.third == c])))
    for c in ("h0", "h1"): rows.append(dict(cell=c, **cellstats(d[d.half == c])))
    t = pd.DataFrame(rows)
    lifts = t[t.cell != "pooled"].lift.values
    ok = np.all(lifts > 0) if t.lift.iloc[0] > 0 else np.all(lifts < 0)
    passes = bool(ok and t.lift.iloc[0] > 0)  # prophecy = positive lift required
    print(f"\n== {name}  ->  {'PASS' if passes else 'FAIL'} (pooled lift {t.lift.iloc[0]:+.4f})")
    print(t.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    return t, passes

def gatetable(d, name):
    """T2-style: lift(location-ok) - lift(location-bad) per cell."""
    ok = d[d.gate == 1]; bad = d[d.gate == 0]
    rows = []
    for cell, so, sb in [("pooled", ok, bad)] + \
            [(c, ok[ok.third == c], bad[bad.third == c]) for c in ("y1", "y2", "y3")] + \
            [(c, ok[ok.half == c], bad[bad.half == c]) for c in ("h0", "h1")]:
        a, b = cellstats(so), cellstats(sb)
        dz = np.nan
        if a["n"] > 1 and b["n"] > 1:
            xo = (so.r - so.nullm).values; xb = (sb.r - sb.nullm).values
            se = np.sqrt(xo.var(ddof=1) / len(xo) + xb.var(ddof=1) / len(xb))
            dz = (a["lift"] - b["lift"]) / se if se > 0 else np.nan
        rows.append(dict(cell=cell, n_ok=a["n"], lift_ok=a["lift"], n_bad=b["n"],
                         lift_bad=b["lift"], dlift=a["lift"] - b["lift"], dz=dz))
    t = pd.DataFrame(rows)
    dl = t[t.cell != "pooled"].dlift.values
    passes = bool(t.dlift.iloc[0] > 0 and np.all(dl > 0))
    print(f"\n== {name}  ->  {'PASS' if passes else 'FAIL'} (pooled dlift {t.dlift.iloc[0]:+.4f})")
    print(t.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    return t, passes

res = {}
# T1: CHoCH follow-through, minor vs major (+BOS bonus)
ch = ev[(ev.test == "T1") & ev.tag.str.startswith("CHOCH")]
res["T1_major"] = table(ch[ch.tag == "CHOCH_major"], "T1 CHoCH major follow-through")
res["T1_minor"] = table(ch[ch.tag == "CHOCH_minor"], "T1 CHoCH minor follow-through")
res["T1_bos"] = table(ev[(ev.test == "T1") & (ev.tag == "BOS_major")], "T1x BOS follow-through (bonus)")

# T2: photon gate. location-ok = bull in discount / bear in premium (pos direction-normalized)
g = ch.dropna(subset=["pos"]).copy()
g["gate"] = np.where(((g.d == 1) & (g.pos < 0.5)) | ((g.d == -1) & (g.pos > 0.5)), 1, 0)
res["T2_all"] = gatetable(g, "T2 photon gate (all CHoCH): right-half vs wrong-half lift")
res["T2_major"] = gatetable(g[g.tag == "CHOCH_major"], "T2 photon gate (major only)")
res["T2_minor"] = gatetable(g[g.tag == "CHOCH_minor"], "T2 photon gate (minor only)")
gb = g[g.d == 1].copy()
res["T2_bull"] = gatetable(gb, "T2 photon gate (bullish CHoCH only: discount vs premium)")
# tercile sensitivity
g["posn"] = np.where(g.d == 1, g.pos, 1 - g.pos)  # normalized: low = favorable half
for lo, hi, nm in ((0, 1 / 3, "deep-favorable"), (1 / 3, 2 / 3, "mid"), (2 / 3, 9e9, "deep-unfavorable")):
    s = cellstats(g[(g.posn >= lo) & (g.posn < hi)])
    print(f"  tercile {nm}: n={s['n']} rate={s['rate']:.4f} null={s['null']:.4f} lift={s['lift']:+.4f} z={s['z']:.2f}")

# T3: band retest quality
res["T3_wick"] = table(ev[(ev.test == "T3") & (ev.tag == "wick")], "T3 wick-band retest rejection")
res["T3_atr"] = table(ev[(ev.test == "T3") & (ev.tag == "atr")], "T3 atr-band retest rejection (old)")
w, a = ev[(ev.test == "T3") & (ev.tag == "wick")], ev[(ev.test == "T3") & (ev.tag == "atr")]
print("\n-- T3 head-to-head (wick lift - atr lift) per cell:")
for cell, sw, sa in [("pooled", w, a)] + [(c, w[w.third == c], a[a.third == c]) for c in ("y1", "y2", "y3")] + \
        [(c, w[w.half == c], a[a.half == c]) for c in ("h0", "h1")]:
    cw, ca = cellstats(sw), cellstats(sa)
    print(f"  {cell}: wick {cw['lift']:+.4f} (n{cw['n']}) vs atr {ca['lift']:+.4f} (n{ca['n']}) -> d {cw['lift']-ca['lift']:+.4f}")

# T4
res["T4A"] = table(ev[ev.test == "T4A"], "T4A PO3 next-candle direction vs null")
res["T4B"] = table(ev[ev.test == "T4B"], "T4B PO3 wick-zone retest respect")

# T5
b = ev[ev.test == "T5B"]
print(f"\n== T5B descriptive: {b.r.mean()*100:.1f}% of {len(b)} major CHoCH preceded by same-dir minor CH within 50 bars")
for c in ("y1", "y2", "y3"): print(f"   {c}: {b[b.third==c].r.mean()*100:.1f}% (n={len(b[b.third==c])})")
for c in ("h0", "h1"): print(f"   {c}: {b[b.half==c].r.mean()*100:.1f}% (n={len(b[b.half==c])})")
res["T5P"] = table(ev[ev.test == "T5P"], "T5P minor CH -> major CHoCH within 50 bars (prophecy)")

print("\n===== SUMMARY =====")
for k, (t, p) in res.items():
    key = "dlift" if "dlift" in t.columns else "lift"
    print(f"{k}: {'PASS' if p else 'FAIL'} pooled {key} {t[key].iloc[0]:+.4f} n={t.n_ok.iloc[0] if 'n_ok' in t else t.n.iloc[0]}")
