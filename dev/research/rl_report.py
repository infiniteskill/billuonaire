"""rl_report -- TARGET-R LADDER tables for the top grade tier (g>=2). Reads rl_h1_trades /
rl_daily_trades. Per tgtR: n, wins, hit%, gross, net (+clustered CI), breakeven hit%, holdout
sign. Daily adds EXCESS over matched-drift null. Plus a TRAIL row each."""
import sys
import numpy as np, pandas as pd
SP = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
TGTS = [2, 3, 4, 5, 6, 7, 8, 9, 10]
pd.set_option("display.width", 240); pd.set_option("display.max_columns", 40)


def grade(df):
    return (df.nst0 >= 4).astype(int) + (df.plive != 0).astype(int) + (df.dist <= 2).astype(int)


def cci(s, col):
    m = s.groupby("sym")[col].mean()
    return s[col].mean(), 1.96 * m.std(ddof=1) / np.sqrt(m.notna().sum())


def sign_str(vals):
    vals = [v for v in vals if np.isfinite(v)]
    if all(v > 0 for v in vals): return "all +"
    if all(v < 0 for v in vals): return "all -"
    return "mixed"


def h1():
    a = pd.read_parquet(f"{SP}/rl_h1_trades.parquet"); a["g"] = grade(a)
    s = a[a.g >= 2].copy(); n = len(s)
    med = s.ts0.median()
    cells = {f"{tl}/h{h}": s[(m) & (s.half == h)] for tl, m in
             (("early", s.ts0 < med), ("late", s.ts0 >= med)) for h in (0, 1)}
    print(f"### H1 top tier g>=2  n={n}  syms={s.sym.nunique()}  zh_stop={s.zh_stop.mean():.2f}")
    print(f"{'tgtR':>4} {'wins':>7} {'hit%':>6} {'gross':>8} {'net':>16} {'costR':>6} {'BE_hit%':>8} {'beat?':>5} {'4way_net_sign':>14} {'minWin/cell':>11}")
    for r in TGTS:
        win = s[f"lad{r}_win"]; net = s[f"lad{r}_net"]; gr = s[f"lad{r}_gross"]
        mu, ci = cci(s, f"lad{r}_net"); hit = win.mean(); cost = gr.mean() - net.mean()
        be = (1 + cost) / (r + 1)
        cellsign = [c[f"lad{r}_net"].mean() for c in cells.values()]
        minw = min(int(c[f"lad{r}_win"].sum()) for c in cells.values())
        print(f"{r:>3}R {int(win.sum()):>7} {100*hit:>5.1f} {gr.mean():>+8.4f} {mu:>+9.4f}±{ci:.4f} {cost:>6.3f} {100*be:>7.1f} "
              f"{('Y' if hit>be else 'n'):>5} {sign_str(cellsign):>14} {minw:>11}")
    # trail
    mu, ci = cci(s, "tr_net"); wtr = (s.tr_net > 0).mean()
    tsign = [c.tr_net.mean() for c in cells.values()]
    pk = s.tr_peakR
    print(f"{'TRAIL':>4} {'-':>7} {100*wtr:>5.1f} {'-':>8} {mu:>+9.4f}±{ci:.4f} {'-':>6} {'-':>8} {'-':>5} {sign_str(tsign):>14}")
    print(f"     trail peakR: mean={pk.mean():.2f} median={pk.median():.2f}  %>=5R={100*(pk>=5).mean():.1f}  %>=10R={100*(pk>=10).mean():.1f}  (hit%col=win rate net>0)")
    print(f"     argmax net over tgtR: {max(TGTS, key=lambda r: s[f'lad{r}_net'].mean())}R  (net still {'NEG' if s['lad2_net'].mean()<0 else 'POS'})")


def daily():
    a = pd.read_parquet(f"{SP}/rl_daily_trades.parquet"); a["g"] = grade(a)
    s = a[a.g >= 2].copy(); n = len(s)
    thirds = {f"3rd{t}": s[s.tt == t] for t in (0, 1, 2)}
    halves = {f"h{h}": s[s.half == h] for h in (0, 1)}
    cells = {**thirds, **halves}
    print(f"\n### DAILY top tier g>=2  n={n}  syms={s.sym.nunique()}  [survivorship: trust EXCESS]")
    print(f"{'tgtR':>4} {'wins':>7} {'hit%':>6} {'net_abs':>16} {'null':>8} {'EXCESS':>16} {'costR':>6} {'BE_hit%':>8} {'beat?':>5} {'holdout_EXCESS_sign':>19}")
    for r in TGTS:
        win = s[f"lad{r}_win"]; net = s[f"lad{r}_net"]; nul = s[f"nul{r}_net"]; gr = s[f"lad{r}_gross"]
        s[f"ex{r}"] = net - nul
        mu, ci = cci(s, f"lad{r}_net"); ex, exci = cci(s, f"ex{r}")
        hit = win.mean(); cost = gr.mean() - net.mean(); be = (1 + cost) / (r + 1)
        exsign = [(c[f"lad{r}_net"] - c[f"nul{r}_net"]).mean() for c in cells.values()]
        print(f"{r:>3}R {int(win.sum()):>7} {100*hit:>5.1f} {mu:>+9.4f}±{ci:.4f} {nul.mean():>+8.4f} {ex:>+9.4f}±{exci:.4f} {cost:>6.3f} {100*be:>7.1f} "
              f"{('Y' if hit>be else 'n'):>5} {sign_str(exsign):>19}")
    s["extr"] = s.tr_net - s.null_tr_net
    mu, ci = cci(s, "tr_net"); ex, exci = cci(s, "extr"); wtr = (s.tr_net > 0).mean()
    exsign = [(c.tr_net - c.null_tr_net).mean() for c in cells.values()]
    pk = s.tr_peakR
    print(f"{'TRAIL':>4} {'-':>7} {100*wtr:>5.1f} {mu:>+9.4f}±{ci:.4f} {s.null_tr_net.mean():>+8.4f} {ex:>+9.4f}±{exci:.4f} {'-':>6} {'-':>8} {'-':>5} {sign_str(exsign):>19}")
    print(f"     trail peakR: mean={pk.mean():.2f} median={pk.median():.2f}  %>=5R={100*(pk>=5).mean():.1f}  %>=10R={100*(pk>=10).mean():.1f}")
    print(f"     argmax net  over tgtR: {max(TGTS, key=lambda r: s[f'lad{r}_net'].mean())}R")
    print(f"     argmax EXCESS over tgtR: {max(TGTS, key=lambda r: (s[f'lad{r}_net']-s[f'nul{r}_net']).mean())}R")
    # per-cell trade counts (reliability)
    print("     holdout cell trade-n:", {k: len(v) for k, v in cells.items()})


if __name__ == "__main__":
    h1(); daily()
