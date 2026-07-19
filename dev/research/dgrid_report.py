#!/usr/bin/env python
"""DGRID aggregation: cells, matched-null excess (ATR-null + vol-matched null),
gauntlet, DGRID.md."""
import numpy as np, pandas as pd, zlib, datetime as dt

SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
OUT = "/home/doom/Public/PROJECT/2026/trader/runs/ladder/DGRID.md"
FLAGSETS = [("none", []), ("F1", ["f1"]), ("F1+F2", ["f1", "f2"]),
            ("F1+F3", ["f1", "f3"]), ("F1+F2+F3", ["f1", "f2", "f3"]), ("F4", ["f4"])]

def load(arm):
    df = pd.read_parquet(f"{SCR}/dgrid_trades_{arm}.parquet")
    df = df.dropna(subset=["null_net"])
    ts = pd.to_datetime(df.ts.astype(str).str[:10])
    if arm == "h4":
        lo, hi = ts.min(), ts.max()
        c1, c2 = lo + (hi - lo) / 3, lo + 2 * (hi - lo) / 3
    else:
        c1, c2 = pd.Timestamp("2009-11-01"), pd.Timestamp("2018-03-01")
    df["era"] = np.where(ts < c1, 0, np.where(ts < c2, 1, 2))
    df["half"] = df.sym.map(lambda s: zlib.crc32(s.encode()) % 2)
    df["d"] = df.net_R - df.null_net
    df["dv"] = df.net_R - df.null_vol
    df["_ts"] = ts
    return df

def cell_stats(sub):
    n = len(sub)
    if n == 0: return None
    d = sub.d.to_numpy()
    ex = d.mean()
    t = ex / (d.std(ddof=1) / np.sqrt(n)) if n > 2 and d.std(ddof=1) > 0 else np.nan
    dv = sub.dv.to_numpy(); exv = dv.mean()
    tv = exv / (dv.std(ddof=1) / np.sqrt(n)) if n > 2 and dv.std(ddof=1) > 0 else np.nan
    eras = [sub[sub.era == e].d.mean() if (sub.era == e).any() else np.nan for e in range(3)]
    halves = [sub[sub.half == h].d.mean() if (sub.half == h).any() else np.nan for h in (0, 1)]
    lg, sh = sub[sub.dir == 1], sub[sub.dir == -1]
    alive = (ex > 0 and all(not np.isnan(v) and v > 0 for v in eras)
             and all(not np.isnan(v) and v > 0 for v in halves))
    qtrs = max(1, sub._ts.dt.to_period("Q").nunique())
    return dict(n=n, net=sub.net_R.mean(), null=sub.null_net.mean(), excess=ex, t=t,
                nullv=sub.null_vol.mean(), exv=exv, tv=tv, cost=sub.cost_R.mean(),
                e0=eras[0], e1=eras[1], e2=eras[2], h0=halves[0], h1=halves[1],
                nL=len(lg), netL=lg.net_R.mean() if len(lg) else np.nan,
                exL=lg.d.mean() if len(lg) else np.nan,
                exvL=lg.dv.mean() if len(lg) else np.nan,
                nS=len(sh), netS=sh.net_R.mean() if len(sh) else np.nan,
                exS=sh.d.mean() if len(sh) else np.nan,
                exvS=sh.dv.mean() if len(sh) else np.nan,
                alive=alive, tpq=len(sub) / qtrs)

def cells_for(arm, df):
    out = []
    for typ in ("FVG", "OB", "BRK", "IFVG"):
        base = df[df.type == typ]
        for fname, cols in FLAGSETS:
            sub = base
            for c in cols: sub = sub[sub[c]]
            for k in (1.5, 2.5):
                for cfg in ("2Rx10", "3Rx20"):
                    s = cell_stats(sub[(sub.k == k) & (sub.cfg == cfg)])
                    if s: out.append(dict(arm=arm, type=typ, flg=fname, k=k, cfg=cfg, **s))
    return out

def fs(v, p=3):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:+.{p}f}"

def sign3(c):
    return "/".join("+" if v > 0 else "−" for v in c if not np.isnan(v))

rows, spans, arms_df = [], {}, {}
for arm in ("h4", "d1"):
    df = load(arm)
    arms_df[arm] = df
    spans[arm] = (df._ts.min().date(), df._ts.max().date())
    rows += cells_for(arm, df)
cells = pd.DataFrame(rows)
cells.to_csv(f"{SCR}/dgrid_cells.csv", index=False)

MINN = 30
big = cells[cells.n >= MINN].sort_values("excess", ascending=False)
top10 = big.head(10)
alive = cells[cells.alive & (cells.n >= MINN)]
alive_econ = alive[alive.net > 0]
nc = len(cells)

L = []
L.append("# DGRID — definitive combination x geometry sweep (4H + DAILY, pure SMC)\n")
L.append("Question: does any zone-type x elimination-flag x stop/exit geometry cell at 4H or")
L.append("DAILY carry edge **in excess of matched drift**? Anchor: LADDER.md (M15/H1/H4 excess~0,")
L.append("buy-hold 18.4%/yr beat every config); fade thesis already falsified at 5m.\n")
L.append("## Design\n")
L.append("- **4H arm**: `l4_h1.parquet` H1, session-aware 2 buckets/day (09:15-12:15, 12:15-15:30),")
L.append(f"  138 syms, {spans['h4'][0]} -> {spans['h4'][1]} (~3y).")
L.append("- **DAILY arm**: `dailymax.parquet`, NIFTY dropped, cut >= 2001-07-01 (25y; pre-2001")
L.append(f"  thin-universe years excluded), 138 syms, {spans['d1'][0]} -> {spans['d1'][1]}.")
L.append("  Residual early-era thinness handled by the matched null (same symbol, same quarter).")
L.append("- **Data hygiene**: splice guard (LADDER rule) — symbol history cut at >25% close->open")
L.append("  jumps; nothing spans a splice (kills unadjusted single-row spikes, e.g. BEL 2005-07-28")
L.append("  7.6->251->7.6, GLENMARK 2003-04-02). ATR-eligibility floor 0.2% of close (D1) /")
L.append("  0.14% (4H) on real signals AND null pool, symmetric (tiny-SL blowup guard).")
L.append("- **Zones** (native-TF, ports of hulinv_run/chartpar_run): FVG (wick-valid 3-candle gap,")
L.append("  displacement close + adaptive range%-threshold), OB (lux swing-break origin box),")
L.append("  BREAKER (EmreKb zz9 MSB swept-swing origin candle), iFVG (FVG closed-through,")
L.append("  flipped zone born at invalidation). Entry: first retest (band overlap, zone not")
L.append("  closed-through on the touch bar) -> next-bar open, fade direction. Dedup (type,dir,entry-bar).")
L.append("- **Flags**: F1 birth in a prior bar-period (4H: prior session; DAILY: prior ISO week)")
L.append("  than the retest. F2 HTF-nest: zone midpoint inside a live direction-matched HTF OB/FVG")
L.append("  (4H: D1 zones from the same H1, prior sessions only; DAILY: W-FRI weekly zones, prior")
L.append("  weeks only; live = confirmed and no HTF close beyond far edge yet). F3 sweep-aligned:")
L.append("  birth <=3 bars after the first sweep (wick-through + close-back) of an EQ pool (2+")
L.append("  same-side 5/5 fractal swings within 0.25xATR14), direction-aligned. F4 gap-origin:")
L.append("  |open(birth) - close(birth-1)| >= 0.5xATR14.")
L.append("- **Geometry**: stop k in {1.5, 2.5} x ATR(14,TF) (SMA-TR, detector formula); exits")
L.append("  {2R tgt + 10-bar time-stop, 3R tgt + 20-bar}. Gap-through stop AND target fill at the")
L.append("  actual next open, both directions — daily gaps are the whole risk, modeled honestly")
L.append("  (post-guard worst single trade ~ -7R).")
L.append("- **Costs** (delivery): STT 0.1% both legs, exch 0.004%, DP Rs15/sell, slip 2bp/leg;")
L.append("  Rs1L capital, 0.5% risk (Rs500), notional cap 5x; R = actual rupee risk; fractional")
L.append("  qty. Shorts costed identically (futures-only in practice; slightly overstated).")
L.append("- **Nulls (mandatory)**: per trade, 5 random entries from the SAME symbol + calendar")
L.append("  quarter, same direction/geometry/costs. Two stop conventions: `null` = the null bar's")
L.append("  own ATR (task spec); `null_vol` = same stop-%-of-price as the real trade (controls the")
L.append("  artifact where real entries carry post-displacement elevated ATR, so drift costs them")
L.append("  fewer R than it costs low-ATR random bars). excess = net_R - null; exV = net_R - null_vol.")
L.append("- **Gauntlet**: temporal thirds (4H: ~1y each; DAILY: 2001-07/2009-11/2018-03, ~8.3y)")
L.append("  x crc32(sym)%2 symbol halves. ALIVE = excess>0 pooled AND >0 in all 3 eras AND both")
L.append("  halves (task-spec, ATR-null based).\n")
L.append(f"**Multiple testing**: 96 cells/arm defined (4 zones x 6 flagsets x 2 stops x 2 exits),")
L.append(f"{nc} populated total; directions inspected inside each => ~{nc*2} looks (and the 2 stop")
L.append("widths share identical signal sets, so cells are heavily correlated). Isolated excess>0")
L.append("is expected by chance; only gauntlet survivors with coherent structure count.\n")

L.append("## Pooled per arm: net vs the two nulls, costs\n")
L.append("| arm | rows | net_R | null(ATR) | excess | null(vol) | exV | cost_R | cost k=1.5 | k=2.5 |")
L.append("|---|---|---|---|---|---|---|---|---|---|")
for arm in ("h4", "d1"):
    d = arms_df[arm]
    L.append(f"| {arm.upper()} | {len(d)} | {d.net_R.mean():+.3f} | {d.null_net.mean():+.3f} | "
             f"{d.d.mean():+.3f} | {d.null_vol.mean():+.3f} | {d.dv.mean():+.3f} | "
             f"{d.cost_R.mean():.3f} | {d[d.k==1.5].cost_R.mean():.3f} | {d[d.k==2.5].cost_R.mean():.3f} |")
L.append("")
L.append("Costs at these TFs are small in R (stops are a few % of price), ~0.06-0.13R/trade,")
L.append("k=2.5 cheaper than k=1.5 (smaller notional per R).\n")

L.append("## Long/short decomposition (pooled per arm, all zone types, all flags)\n")
L.append("| arm | dir | n | net_R | null(ATR) | excess | null(vol) | exV |")
L.append("|---|---|---|---|---|---|---|---|")
for arm in ("h4", "d1"):
    d = arms_df[arm]
    for dr, nm in ((1, "LONG"), (-1, "SHORT")):
        s = d[d.dir == dr]
        L.append(f"| {arm.upper()} | {nm} | {len(s)} | {s.net_R.mean():+.3f} | "
                 f"{s.null_net.mean():+.3f} | {s.d.mean():+.3f} | {s.null_vol.mean():+.3f} | {s.dv.mean():+.3f} |")
L.append("")
L.append("Raw long net_R rides the India drift — the null carries the same drift, so only the")
L.append("excess columns are evidence. Any 'long edge' whose null is equally positive is drift.\n")

L.append(f"## Top-10 cells by excess (n >= {MINN})\n")
L.append("| arm | zone | flags | k | exit | n | net_R | null | excess | t | exV | tV | eras | halves | exL(n) | exS(n) | ALIVE |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for _, r in top10.iterrows():
    L.append(f"| {r['arm'].upper()} | {r['type']} | {r['flg']} | {r['k']} | {r['cfg']} | {r['n']} | "
             f"{fs(r['net'])} | {fs(r['null'])} | **{fs(r['excess'])}** | {r['t']:+.2f} | "
             f"{fs(r['exv'])} | {r['tv']:+.2f} | "
             f"{sign3([r['e0'], r['e1'], r['e2']])} | {sign3([r['h0'], r['h1']])} | "
             f"{fs(r['exL'])}({r['nL']}) | {fs(r['exS'])}({r['nS']}) | {'**YES**' if r['alive'] else 'no'} |")
L.append("")

L.append("## Flags=none baseline (the raw retest-timing effect, per zone type)\n")
L.append("Excess of the UNFILTERED first-retest cells (mean over the 4 geometry variants; the")
L.append("same signals underlie all four). If this is already positive, the elimination flags")
L.append("are refinements of a generic pullback-timing effect, not its source.\n")
L.append("| arm | zone | n/geom | net_R | null | excess | exV | exL | exS |")
L.append("|---|---|---|---|---|---|---|---|---|")
for arm in ("h4", "d1"):
    b = cells[(cells.arm == arm) & (cells.flg == "none")]
    for typ in ("FVG", "OB", "BRK", "IFVG"):
        s = b[b.type == typ]
        if not len(s): continue
        L.append(f"| {arm.upper()} | {typ} | {int(s.n.mean())} | {fs(s.net.mean())} | "
                 f"{fs(s['null'].mean())} | {fs(s.excess.mean())} | {fs(s.exv.mean())} | "
                 f"{fs(s.exL.mean())} | {fs(s.exS.mean())} |")
L.append("")

L.append("## Gauntlet survivors (ALIVE, task-spec excess)\n")
if len(alive):
    L.append(f"{len(alive)} of {len(cells[cells.n >= MINN])} qualifying cells are ALIVE on the")
    L.append("task-spec (ATR-null) excess. Survivors with net_R>0 (the only economically live ones):\n")
    L.append("| arm | zone | flags | k | exit | n | net_R | excess | t | exV | tV | exL | exS | trades/qtr |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in alive_econ.sort_values("excess", ascending=False).iterrows():
        L.append(f"| {r['arm'].upper()} | {r['type']} | {r['flg']} | {r['k']} | {r['cfg']} | {r['n']} | "
                 f"{fs(r['net'])} | {fs(r['excess'])} | {r['t']:+.2f} | {fs(r['exv'])} | {r['tv']:+.2f} | "
                 f"{fs(r['exL'])} | {fs(r['exS'])} | {r['tpq']:.1f} |")
    L.append("")
    neg = alive[alive.net <= 0]
    L.append(f"The other {len(neg)} ALIVE cells all have net_R <= 0: their 'excess' means the real")
    L.append("entries lose LESS than matched random entries — timing without economics. Nothing")
    L.append("to trade there.")
else:
    L.append("**None.**")
L.append("")

L.append("## Verdict\n")
VERDICT_PLACEHOLDER = True
L.append("@@VERDICT@@")
L.append("")
L.append(f"*Generated {dt.date.today()} by dgrid_run.py / dgrid_report.py (scratchpad, prefix dgrid_).*")

open(f"{SCR}/dgrid_body.md", "w").write("\n".join(L) + "\n")
print(f"body -> {SCR}/dgrid_body.md  cells={nc} alive={len(alive)} alive_econ={len(alive_econ)}")
cols = ["arm", "type", "flg", "k", "cfg", "n", "net", "null", "excess", "t", "exv", "tv", "alive"]
print(top10[cols].to_string())
print("\nALIVE + net>0:")
print(alive_econ[cols + ["tpq"]].to_string())
print("\npooled:")
for arm in ("h4", "d1"):
    d = arms_df[arm]
    for dr in (1, -1):
        s = d[d.dir == dr]
        print(f"{arm} dir={dr:+d} n={len(s)} net={s.net_R.mean():+.3f} nullA={s.null_net.mean():+.3f} "
              f"ex={s.d.mean():+.3f} nullV={s.null_vol.mean():+.3f} exV={s.dv.mean():+.3f}")
