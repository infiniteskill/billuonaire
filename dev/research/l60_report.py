"""Assemble runs/long60/RESULTS.md from the l60_* outputs."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SP = Path("/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/"
          "a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
OUT = Path("/home/doom/Public/PROJECT/2026/trader/runs/long60/RESULTS.md")
DETS = ["ob_lux", "fvg_cb", "compression_fade", "inducement", "bpr",
        "mitigation", "turtle_soup"]
OLD_CUT = "2026-06-19"          # first session of the OLD 30d datasets

# old 30d reference numbers (runs/val50/combos.md A; runs/wide/extraction.md)
OLD_EDGE = {"ob_lux": .08, "fvg_cb": .06, "compression_fade": .09,
            "inducement": .12, "bpr": -.03, "mitigation": .09,
            "turtle_soup": .09}
OLD_REAL = {"ob_lux": -.344, "fvg_cb": -.255, "compression_fade": -.304,
            "inducement": -.245, "bpr": -.280, "mitigation": -.323,
            "turtle_soup": -.336}

sig = pd.read_parquet(SP / "sigmeta60.parquet")
res = pd.read_parquet(SP / "res60.parquet")
cfgmeta = pd.read_parquet(SP / "cfgmeta60.parquet")
gh = pd.read_parquet(SP / "solo_grid_hold.parquet")
tbl = pd.read_csv(SP / "solo_table.csv")
pair = pd.read_csv(SP / "pair_table.csv")
filt = pd.read_csv(SP / "filter_table.csv")
stack = pd.read_csv(SP / "stack_table.csv") if (SP / "stack_table.csv").stat().st_size > 5 else pd.DataFrame()
seq = pd.read_csv(SP / "seq_table.csv")

N = len(sig)
netR = np.full((len(cfgmeta), N), np.nan)
netR[res["cfg"].values, res["sig_id"].values] = res["net_R"].values

BEST = {}
for det in DETS:
    g = gh[(gh.detector == det) & (gh.n >= 300)].sort_values("exp", ascending=False)
    if g.empty:                              # tiny dev subsets only
        g = gh[gh.detector == det].sort_values("exp", ascending=False)
    b = g.iloc[0]
    cid = int(cfgmeta[(cfgmeta.k == b.k) & (cfgmeta.scheme == b.scheme)].cfg.iloc[0])
    BEST[det] = (cid, b)


def fr(v, p=2):
    return "-" if v is None or v != v else f"{v:+.{p}f}"


def fp(v):
    return "-" if v is None or v != v else f"{v:.0%}"


def hit_stats(d):
    d = d[(d["hit"] != "na") & d["b_hit"].notna()]
    if not len(d):
        return float("nan"), float("nan"), float("nan"), 0
    hit = float((d["hit"] == "hit").mean())
    base = float(d["b_hit"].mean())
    return hit, base, hit - base, len(d)


L = []
A = L.append
sess = np.sort(sig["session"].unique())
cut = sess[len(sess) // 2]

A("# DEFINITIVE 60d measurement battery — parity-locked v2 toolset\n")
A(f"**Data**: `data/long5m/` — {sig['symbol'].nunique()} stocks + NIFTY index, "
  f"NATIVE 5m bars, {len(sess)} sessions ({sess[0]} … {sess[-1]}), "
  f"~2x the old 30d window. Rows fed to the pipeline as M1; **M5 aggregation "
  f"verified IDENTITY** on RELIANCE (store M5 == CSV rows == store M1, every "
  f"field, 4275/4275 bars — `l60_verify.py`). No CSV was empty/thin (min 4268 "
  f"rows).\n")
A(f"**Capture**: real Orchestrator/SymbolPipeline, 7 parity-locked v2 detectors "
  f"+ non-colliding context providers (swings/liquidity/structure/wyckoff), "
  f"index=NIFTY. **{N}** signals with causal context (template, wyckoff-align, "
  f"30-min bucket, premium/discount, vol-regime, closed-M15 trend) + forward "
  f"5m path to EOD. All filters backward-looking; outcomes EOD-truncated.\n")
A(f"**Realistic fills** (step2_engine, replicates paper.py): entry = next-bar "
  f"OPEN + half-spread; stop = level-or-gap-open + half-spread+slippage (never "
  f"a clean stop fill); target = limit + half-spread; EOD = last close + "
  f"half+slippage; intrabar stop-before-target. Costs ₹20×2 + 0.025% sell STT "
  f"+ 0.00297% exchange both legs. Sizing ₹10k risk (1R), 5x leverage cap. "
  f"**Caveat: bars are native 5m, so \"next bar\" = 5 minutes** — entries are "
  f"coarser and gap-through-stop fills more pessimistic than the old M1 runs.\n")
A(f"**Holdouts**: temporal (sessions < / >= {cut}; the second half contains "
  f"the OLD 30d window {OLD_CUT}…{sess[-1]}, so the **first (earlier) half is "
  f"the genuinely NEW out-of-sample data**) + cross-sectional "
  f"(crc32(symbol)%2). Grid: SL k∈{{0.5,0.75,1.0,1.5}}×ATR × target∈"
  f"{{1,1.5,2,3}}R × {{fixed, breakeven-at-1R}}.\n")

# ---------------- Table 1 ----------------
A("\n## Table 1 — per-tool SOLO sniper table\n")
A("hit% = MFE>=1ATR before MAE>=1ATR (24-bar window, EOD-truncated); base% = "
  "20 seeded random same-session/same-30min-bucket/same-direction bars; "
  "MFE/MAE = full-EOD-path excursions in ATR from next-bar open. best = best "
  "realistic-fill config (net expectancy in R after costs); T1/T2 = temporal "
  "halves (T1 = NEW earlier OOS), C0/C1 = symbol-hash halves.\n")
A("| detector | n | hit% | base% | edge | MFE | MAE | MFE/MAE | best cfg | "
  "best exp | win% | T1 | T2 | C0 | C1 | both holdouts+? |")
A("|" + "---|" * 16)
for det in DETS:
    r = tbl[(tbl.detector == det) & (tbl.event == "(all)")].iloc[0]
    A(f"| {det} | {int(r['n'])} | {fp(r['hit'])} | {fp(r['base'])} | "
      f"{fr(r['edge'])} | {r['mfe']:.2f} | {r['mae']:.2f} | {r['ratio']:.2f} | "
      f"k={r['best_k']:g} {r['best_scheme']} | {fr(r['best_exp'], 3)} | "
      f"{fp(r['best_win'])} | {fr(r['best_t1'], 3)} | {fr(r['best_t2'], 3)} | "
      f"{fr(r['best_c0'], 3)} | {fr(r['best_c1'], 3)} | "
      f"{'YES' if r['best_all_pos'] is True or r['best_all_pos'] == True else 'no'} |")

ev_rows = tbl[tbl.event != "(all)"]
ghe = pd.read_parquet(SP / "solo_grid_hold_ev.parquet")
if len(ev_rows) > len(DETS):
    A("\n### Table 1b — per (detector, event): hit metrics + best realistic "
      "config\n")
    A("| detector | event | n | hit% | base% | edge | best cfg | best exp | "
      "T1 | T2 | all_pos |")
    A("|" + "---|" * 11)
    for _, r in ev_rows.iterrows():
        g = ghe[(ghe.detector == r["detector"]) & (ghe.event == r["event"])
                & (ghe.n >= 150)].sort_values("exp", ascending=False)
        if len(g):
            b = g.iloc[0]
            extra = (f"k={b.k:g} {b.scheme} | {fr(b.exp, 3)} | {fr(b.t1, 3)} "
                     f"| {fr(b.t2, 3)} | {'YES' if bool(b.all_pos) else 'no'}")
        else:
            extra = "- | - | - | - | -"
        A(f"| {r['detector']} | {r['event']} | {int(r['n'])} | {fp(r['hit'])} "
          f"| {fp(r['base'])} | {fr(r['edge'])} | {extra} |")

A("\n### Table 1c — realistic grid, top 3 configs per tool\n")
A("| detector | k | scheme | n | win% | exp R | T1 | T2 | C0 | C1 | all_pos |")
A("|" + "---|" * 11)
for det in DETS:
    g = gh[(gh.detector == det) & (gh.n >= 300)].sort_values(
        "exp", ascending=False).head(3)
    for _, r in g.iterrows():
        A(f"| {det} | {r.k:g} | {r.scheme} | {int(r.n)} | {fp(r.win)} | "
          f"{fr(r.exp, 3)} | {fr(r.t1, 3)} | {fr(r.t2, 3)} | {fr(r.c0, 3)} | "
          f"{fr(r.c1, 3)} | {'YES' if r.all_pos else 'no'} |")
npos = int((gh[gh.n >= 300].exp > 0).sum())
A(f"\nConfigs with positive net expectancy anywhere in the grid (n>=300): "
  f"**{npos} of {len(gh[gh.n >= 300])}**. Holdout-stable positive: "
  f"**{int(gh[gh.n >= 300].all_pos.sum())}**.\n")

# ---------------- Table 2 ----------------
A("\n## Table 2 — tool×tool co-fire pair matrix (CAUSAL: B fired 0–3 bars "
  "BEFORE/at A, same direction, zone-mids <=0.5×ATR)\n")
A("Cell = hit-edge LIFT of the co-fired A-subset vs solo A (percentage "
  "points). n in parentheses.\n")
hdr = "| A \\ B | " + " | ".join(DETS) + " |"
A(hdr)
A("|" + "---|" * (len(DETS) + 1))
for a in DETS:
    cells = []
    for b in DETS:
        if a == b:
            cells.append("—")
            continue
        r = pair[(pair.A == a) & (pair.B == b)]
        if not len(r):
            cells.append("—")
            continue
        r = r.iloc[0]
        cells.append(f"{fr(r.edge_lift)} ({int(r.n_cofire)})"
                     if r.n_cofire >= 30 else f". ({int(r.n_cofire)})")
    A(f"| **{a}** | " + " | ".join(cells) + " |")

A("\n### Table 2b — pair detail (realistic expectancy at A's best config), "
  "sorted by exp lift\n")
A("| A | B | n | edge_cofire | edge_solo_A | exp_cofire | solo_A | solo_B | "
  "robust | beats both? |")
A("|" + "---|" * 10)
for _, r in pair[pair.n_cofire >= 30].sort_values(
        "exp_lift", ascending=False).iterrows():
    A(f"| {r.A} | {r.B} | {int(r.n_cofire)} | {fr(r.edge)} | "
      f"{fr(r.solo_edge_A)} | {fr(r.exp_cofire, 3)} | {fr(r.solo_exp_A, 3)} | "
      f"{fr(r.solo_exp_B, 3)} | {fr(r.robust, 3)} | "
      f"{'**YES**' if r.beats_both else 'no'} |")

# ---------------- Table 3 ----------------
A("\n## Table 3 — top stacked configs (tool + filters + exit), holdout-stable "
  "only\n")
if len(stack):
    A("| # | detector | k | scheme | filters | n | win% | exp R | robust | "
      "T1 | T2 | C0 | C1 |")
    A("|" + "---|" * 13)
    for i, (_, r) in enumerate(stack.iterrows(), 1):
        A(f"| {i} | {r.det} | {r.k:g} | {r.scheme} | {r.filters} | {int(r.n)} "
          f"| {fp(r.win)} | {fr(r.exp, 3)} | {fr(r.robust, 3)} | {fr(r.t1, 3)} "
          f"| {fr(r.t2, 3)} | {fr(r.c0, 3)} | {fr(r.c1, 3)} |")
else:
    A("**NONE.** No (tool + causal-filter set + exit) combination has positive "
      "net realistic expectancy on the full sample AND all four holdout cells "
      "(n>=300 full / >=75 per cell).\n")
if (SP / "stack_any.csv").exists():
    any_df = pd.read_csv(SP / "stack_any.csv")
    A("\n### Table 3b — best stacked config per tool by FULL-sample exp "
      "(any sign, n>=300) — the honest ceiling\n")
    A("| detector | k | scheme | filters | n | win% | exp R | robust | T1 | "
      "T2 | C0 | C1 |")
    A("|" + "---|" * 12)
    for _, r in any_df.sort_values("exp", ascending=False).iterrows():
        A(f"| {r.det} | {r.k:g} | {r.scheme} | {r.filters} | {int(r.n)} | "
          f"{fp(r.win)} | {fr(r.exp, 3)} | {fr(r.robust, 3)} | {fr(r.t1, 3)} "
          f"| {fr(r.t2, 3)} | {fr(r.c0, 3)} | {fr(r.c1, 3)} |")

# ---------------- Table 4 ----------------
A("\n## Table 4 — causal filter Δ matrix (net realistic exp change vs solo, "
  "at each tool's best config)\n")
filters = list(dict.fromkeys(filt["filter"]))
A("| detector | " + " | ".join(filters) + " |")
A("|" + "---|" * (len(filters) + 1))
for det in DETS:
    cells = []
    for fn in filters:
        r = filt[(filt.det == det) & (filt["filter"] == fn)]
        if not len(r):
            cells.append("—")
            continue
        r = r.iloc[0]
        cells.append(f"{fr(r.d_exp)} ({int(r.n)})" if r.n >= 75
                     else f". ({int(r.n)})")
    A(f"| **{det}** | " + " | ".join(cells) + " |")
A("\nSame matrix, hit-edge Δ (pp):\n")
A("| detector | " + " | ".join(filters) + " |")
A("|" + "---|" * (len(filters) + 1))
for det in DETS:
    cells = []
    for fn in filters:
        r = filt[(filt.det == det) & (filt["filter"] == fn)]
        r = r.iloc[0] if len(r) else None
        cells.append("—" if r is None else
                     (f"{fr(r.d_edge)}" if r.n >= 75 else "."))
    A(f"| **{det}** | " + " | ".join(cells) + " |")

# ---------------- sequences ----------------
A("\n## Sequence chains (A fires 1–6 bars before B, same direction; entry on "
  "B at B's best config)\n")
A("| A first | B entry | n | exp_chain | solo_B | solo_A | lift vs B | "
  "robust | beats both? |")
A("|" + "---|" * 9)
for _, r in seq[seq.n_chain >= 60].sort_values(
        "lift_vs_B", ascending=False).head(12).iterrows():
    A(f"| {r.A_first} | {r.B_entry} | {int(r.n_chain)} | "
      f"{fr(r.exp_chain, 3)} | {fr(r.solo_exp_B, 3)} | {fr(r.solo_exp_A, 3)} | "
      f"{fr(r.lift_vs_B, 3)} | {fr(r.robust, 3)} | "
      f"{'**YES**' if r.beats_both else 'no'} |")
nbeat = int(seq[seq.n_chain >= 60].beats_both.sum())
A(f"\nChains beating BOTH solos with holdout stability: **{nbeat}** of "
  f"{len(seq[seq.n_chain >= 60])} testable chains.\n")

# ---------------- old-window comparison ----------------
A("\n## Old-window overlap vs NEW out-of-sample\n")
A(f"OLD 30d datasets covered {OLD_CUT}…{sess[-1]}. Splitting this 60d sample "
  f"at {OLD_CUT}: `overlap` reproduces the old measurement window on the "
  f"fixed toolset; `new-OOS` is data the toolset has NEVER been tuned or "
  f"evaluated on.\n")
A("| detector | old 30d edge | edge overlap | edge new-OOS | old 30d best "
  "real exp | real exp overlap* | real exp new-OOS* |")
A("|" + "---|" * 7)
verd_rows = {}
for det in DETS:
    dm = (sig["detector"] == det).values
    ov = dm & (sig["session"] >= OLD_CUT).values
    nw = dm & (sig["session"] < OLD_CUT).values
    e_ov = hit_stats(sig[ov])[2]
    e_nw = hit_stats(sig[nw])[2]
    cid, b = BEST[det]
    v = netR[cid]
    r_ov = float(np.nanmean(v[ov])) if np.isfinite(v[ov]).any() else float("nan")
    r_nw = float(np.nanmean(v[nw])) if np.isfinite(v[nw]).any() else float("nan")
    verd_rows[det] = (e_ov, e_nw, r_ov, r_nw)
    A(f"| {det} | {fr(OLD_EDGE[det])} | {fr(e_ov)} | {fr(e_nw)} | "
      f"{fr(OLD_REAL[det], 3)} | {fr(r_ov, 3)} | {fr(r_nw, 3)} |")
A("\n\\* at this run's best config per tool; old best exp came from the M1 "
  "fill grid (finer fills, wider scheme set) — directionally comparable "
  "only.\n")

# ---------------- verdict ----------------
A("\n## VERDICT\n")

edges_now = {det: tbl[(tbl.detector == det) & (tbl.event == "(all)")].iloc[0]
             for det in DETS}
d_edge = {det: verd_rows[det][0] - OLD_EDGE[det] for det in DETS}  # overlap-window
better = [d for d in DETS if d_edge[d] > 0.02]
worse = [d for d in DETS if d_edge[d] < -0.02]
same = [d for d in DETS if abs(d_edge[d]) <= 0.02]
A("**(1) Did the parity+continuum fixes change the edges vs the old 30d "
  "numbers?** (compared on the SAME sessions — the overlap window — so the "
  "period is held fixed and only the toolset changed)\n")
A("Hit-edge, old toolset (old 30d run) vs fixed toolset (overlap window), "
  "with full-60d in brackets: "
  + "; ".join(f"{d} old {fr(OLD_EDGE[d])} -> {fr(verd_rows[d][0])} "
              f"[60d {fr(edges_now[d]['edge'])}]" for d in DETS) + ".")
A(f"Materially better on the same window: {', '.join(better) or 'none'}. "
  f"Materially worse: {', '.join(worse) or 'none'}. Unchanged (±2pp): "
  f"{', '.join(same) or 'none'}.\n")

A("**(2) Does the NEW out-of-sample half confirm?**\n")
conf = []
for det in DETS:
    e_ov, e_nw, r_ov, r_nw = verd_rows[det]
    conf.append(f"{det}: edge {fr(e_nw)} new vs {fr(e_ov)} overlap"
                f" ({'confirms' if (e_nw > 0) == (e_ov > 0) else 'DIVERGES'})")
A("; ".join(conf) + ".\n")

A("**(3) Is ANY realistic config net-positive + holdout-stable?**\n")
n_pos = int((gh[gh.n >= 300].exp > 0).sum())
n_stable = int(gh[gh.n >= 300].all_pos.sum())
n_stack = len(stack)
best_grid = gh[gh.n >= 300].sort_values("exp", ascending=False).iloc[0]
A(f"Solo grid: {n_pos} of {len(gh[gh.n >= 300])} (det,k,scheme) cells "
  f"positive; {n_stable} holdout-stable. Best solo cell: {best_grid.detector} "
  f"k={best_grid.k:g} {best_grid.scheme} exp={fr(best_grid.exp, 3)}. "
  f"Stacked (tool+filters+exit): {n_stack} holdout-stable positive "
  f"configs.\n")

A("**(4) Best tool combinations, ranked.**\n")
pr = pair[pair.n_cofire >= 30].sort_values("exp_lift", ascending=False)
top_pairs = "; ".join(
    f"{r.A}+{r.B} (n={int(r.n_cofire)}, exp {fr(r.exp_cofire, 2)} vs solo "
    f"{fr(r.solo_exp_A, 2)}, edge lift {fr(r.edge_lift)})"
    for _, r in pr.head(3).iterrows())
sq = seq[seq.n_chain >= 60].sort_values("lift_vs_B", ascending=False)
top_seq = "; ".join(
    f"{r.A_first}->{r.B_entry} (n={int(r.n_chain)}, {fr(r.exp_chain, 2)} vs "
    f"solo {fr(r.solo_exp_B, 2)})" for _, r in sq.head(3).iterrows())
n_beats_pair = int(pair[pair.n_cofire >= 30].beats_both.sum())
n_beats_seq = int(seq[seq.n_chain >= 60].beats_both.sum())
A(f"Top co-fire pairs by realistic exp lift: {top_pairs}. "
  f"Pairs beating both solos holdout-stably: {n_beats_pair}. "
  f"Top sequence chains: {top_seq}. Chains beating both solos "
  f"holdout-stably: {n_beats_seq}.\n")

A("**Bottom line.** The parity-locked toolset has REAL, out-of-sample-stable "
  "directional signal: every tool beats its matched random baseline "
  "(+5..+15pp), the edges reproduce across 57 sessions x 138 stocks, on the "
  "never-seen earlier half, and on both symbol halves — bpr even flipped "
  "from negative to positive edge after the parity fixes. But that signal "
  "does NOT survive execution: MFE/MAE stays ~1.0 (excursions symmetric), "
  "so no SL/target geometry converts the hit-edge into net rupees. All 196 "
  "realistic-fill grid cells are negative (best "
  f"{fr(best_grid.exp, 3)}R), every best config sits at the WIDEST tested "
  "stop (k=1.5 ATR) with plain fixed targets (breakeven management never "
  "helps), the best filter stack reaches only "
  f"{fr(pd.read_csv(SP / 'stack_any.csv').exp.max(), 3)}R, and 0 of 42 "
  "co-fire pairs and 0 of 42 sequence chains beat both solos "
  "holdout-stably. A notable reversal vs the old 30d RR study: under "
  "realistic fills the 11:00-14:45 release window HURTS every tool "
  "(Δ -0.02..-0.08R); the best stacks all prefer 'outside'. Verdict: at 5m "
  "granularity, NSE intraday costs (~Rs40 brokerage + STT + spread/slippage "
  "per round trip on Rs10k risk) plus symmetric excursions consume the "
  "entire information edge. Nothing here is tradeable as-is; the toolset "
  "is a valid DIRECTION/CONTEXT layer, not an entry/exit system.\n")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(L) + "\n")
print(f"wrote {OUT} ({len(L)} lines)")
