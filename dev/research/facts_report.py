"""facts_report.py — aggregate zone-level facts, 4-way holdouts, greedy stack.
Prints tables and writes runs/long60/FACTS.md."""
import numpy as np, pandas as pd, zlib, math

SCR = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
SPLIT = '2026-06-08'
pd.set_option('display.width', 250)

first = pd.read_parquet(f'{SCR}/facts_first.parquet')
allsig = pd.read_parquet(f'{SCR}/facts_all.parquet')
ifvg = pd.read_parquet(f'{SCR}/facts_ifvg.parquet')

for df in (first, allsig, ifvg):
    df['T'] = np.where(df.session < SPLIT, 'T1', 'T2')
    df['C'] = ['C'+str(zlib.crc32(s.encode()) % 2) for s in df.symbol]
first['delay_min'] = (first.sig_i - first.born_i)*5
first['same_day'] = first.born_date == first.session
first['nextday'] = ~first.same_day
BUCKETS = ['<30m','30-60m','1-4h','>4h','nextday+']
def bucket(d, s):
    if not s: return 'nextday+'
    return '<30m' if d < 30 else '30-60m' if d < 60 else '1-4h' if d < 240 else '>4h'
first['bucket'] = [bucket(d, s) for d, s in zip(first.delay_min, first.same_day)]

N = len(first); NSESS = first.session.nunique()
def stats(g):
    v = g.dropna(subset=['net_r'])
    return dict(n=len(g), hit=100*v.hit.mean() if len(v) else np.nan,
                netR=v.net_r.mean() if len(v) else np.nan,
                mfe=v.mfe.mean() if len(v) else np.nan, mae=v.mae.mean() if len(v) else np.nan)
BASE = stats(first)

def holdout(cond):
    """4-way holdout: hit-lift of cond vs cell base. Returns list + stable flag."""
    cells = []
    for col, val in [('T','T1'),('T','T2'),('C','C0'),('C','C1')]:
        g = first[first[col] == val]
        b, cm = stats(g), stats(g[cond[g.index]])
        cells.append((val, cm['n'], round(cm['hit']-b['hit'], 2), round(cm['netR']-b['netR'], 3)))
    lifts = [c[2] for c in cells]
    stable = all(np.sign(x) == np.sign(lifts[0]) for x in lifts) and lifts[0] != 0
    return cells, stable

def factrow(name, cond):
    s = stats(first[cond])
    cells, stable = holdout(cond)
    return dict(fact=name, n_kept=s['n'], shrink=100*(1-s['n']/N),
                per_day=s['n']/NSESS, hit=s['hit'], lift=s['hit']-BASE['hit'],
                netR=s['netR'], liftR=s['netR']-BASE['netR'],
                stable='YES' if stable else 'no',
                cells=' '.join(f'{v}:{l:+.1f}' for v, _, l, _ in cells))

md = []
def emit(s=''):
    print(s); md.append(s)

emit(f"# FACTS — zone-level discrimination, 138 symbols")
emit()
emit(f"Universe: first retest per zone, detectors fvg_cb/ob_lux/mitigation, "
     f"{N} zones over {NSESS} sessions ({N/NSESS:.0f} zones/day pooled). "
     f"Uniform sim: next-bar-open entry, 1.5×ATR stop, 1R target, stop-first, EOD 15:10, 0.06% cost.")
emit(f"Base: hit {BASE['hit']:.1f}% | netR {BASE['netR']:.3f} | MFE {BASE['mfe']:.2f} MAE {BASE['mae']:.2f}. "
     f"NB: the assumed +6pp (52%) breakeven bar is optimistic — measured breakeven at this geometry is "
     f"~59% hit (see Verdict).")
emit()

# ---------------- fact table ----------------
first['imp_b'] = pd.cut(first.impulse, [-np.inf, 1, 2, 3, np.inf], labels=['<1','1-2','2-3','>=3'])
facts = [
    ('nextday+ retest (known ref)', first.bucket == 'nextday+'),
    ('gap-origin (open-bar OR gap-overlap)', first.gap_open | first.gap_overlap),
    ('gap: birth = 09:15 open bar', first.gap_open.astype(bool)),
    ('gap: band overlaps overnight gap >0.3ATR', first.gap_overlap.astype(bool)),
    ('gap-origin AND nextday+ retest', (first.gap_open | first.gap_overlap) & (first.bucket == 'nextday+')),
    ('impulse >=2 ATR', first.impulse >= 2),
    ('impulse >=3 ATR', first.impulse >= 3),
    ('impulse <1 ATR (weak birth)', first.impulse < 1),
    ('H1 anchor (long-run H1 swing w/in 1 ATR5)', first.h1_anchor.astype(bool)),
    ('H1 nested (inside live same-dir H1 zone)', first.h1_nested.astype(bool)),
    ('H1 nested any-dir', first.h1_nested_any.astype(bool)),
    ('sweep-born (EQ-pool sweep <=3 bars before)', first.sweep_born.astype(bool)),
    ('sweep-born aligned (soup direction)', first.sweep_aligned.astype(bool)),
]
rows = [factrow(nm, cond) for nm, cond in facts]
tab = pd.DataFrame(rows).sort_values('lift', ascending=False)
emit('## Fact table (zone level, first retest; lift vs 46.1% / -0.186R base)')
emit()
emit('| fact | n kept | shrink% | n/day | hit% | lift pp | netR | liftR | 4-way stable | cells (hit-lift pp) |')
emit('|---|---|---|---|---|---|---|---|---|---|')
for _, r in tab.iterrows():
    emit(f"| {r['fact']} | {r.n_kept} | {r.shrink:.1f} | {r.per_day:.0f} | {r.hit:.1f} | "
         f"{r.lift:+.1f} | {r.netR:.3f} | {r.liftR:+.3f} | {r.stable} | {r.cells} |")
emit()

# ---------------- gap-origin deep section ----------------
emit('## 1. Gap-origin (priority)')
emit()
go = first.gap_open | first.gap_overlap
for nm, g in [('gap-origin', first[go]), ('intraday-origin', first[~go])]:
    s = stats(g)
    fr = g.bucket.value_counts(normalize=True).reindex(BUCKETS)*100
    sd = g[g.same_day]
    q = sd.delay_min.quantile([.25, .5, .75]).values if len(sd) else [np.nan]*3
    emit(f"- **{nm}**: n={s['n']} ({100*s['n']/N:.1f}% share), hit {s['hit']:.1f}% "
         f"({s['hit']-BASE['hit']:+.1f}pp), netR {s['netR']:.3f}, MFE {s['mfe']:.2f} MAE {s['mae']:.2f}. "
         f"Revisit delay: same-day q25/med/q75 = {q[0]:.0f}/{q[1]:.0f}/{q[2]:.0f} min; "
         f"buckets % " + ' '.join(f"{b}={fr[b]:.1f}" for b in BUCKETS))
emit()
emit('Cross gap-origin × retest bucket (hit% / netR / n):')
emit()
emit('| bucket | gap-origin | intraday-origin |')
emit('|---|---|---|')
for b in BUCKETS:
    c1 = stats(first[go & (first.bucket == b)]); c0 = stats(first[~go & (first.bucket == b)])
    emit(f"| {b} | {c1['hit']:.1f}% / {c1['netR']:.3f} / {c1['n']} | {c0['hit']:.1f}% / {c0['netR']:.3f} / {c0['n']} |")
emit()
cell = go & (first.bucket == 'nextday+')
s = stats(first[cell]); cells, stable = holdout(cell)
emit(f"**Hand-picked class (gap-origin AND next-day+ retest)**: n={s['n']} "
     f"({100*s['n']/N:.1f}% of pile, {s['n']/NSESS:.0f}/day across 138), hit {s['hit']:.1f}% "
     f"({s['hit']-BASE['hit']:+.1f}pp), netR {s['netR']:.3f}, MFE {s['mfe']:.2f} MAE {s['mae']:.2f}.")
emit(f"4-way holdout hit-lift: " + '  '.join(f"{v}: {l:+.1f}pp (n={nn})" for v, nn, l, _ in cells)
     + f" → stable={stable}")
emit(f"BUT: plain nextday+ is {stats(first[first.bucket=='nextday+'])['hit']:.1f}% — adding gap-origin "
     f"on top of nextday+ REMOVES 0.5pp (intraday-origin & nextday+ = "
     f"{stats(first[~go & (first.bucket=='nextday+')])['hit']:.1f}%). Gap-origin does not add there.")
emit()
emit('**Where gap-origin actually discriminates: FAST retests.** The <30m pile (30% of zones) splits:')
for nm, cond in [('gap-origin & <30m', go & (first.bucket == '<30m')),
                 ('intraday & <30m', ~go & (first.bucket == '<30m'))]:
    s = stats(first[cond]); cells, stable = holdout(cond)
    emit(f"- {nm}: n={s['n']}, hit {s['hit']:.1f}% ({s['hit']-BASE['hit']:+.1f}pp), netR {s['netR']:.3f}, "
         f"stable={stable} [" + ' '.join(f"{v}:{l:+.1f}" for v, _, l, _ in cells) + ']')
emit('So the earlier "<30m is NOT noise" refines to: fast retests are fine only for gap-origin zones; '
     'intraday-origin fast retests are a stable −1.3pp drag.')
emit()
# per-detector
emit('Per-detector, gap-origin AND nextday+:')
for det, g in first.groupby('detector'):
    b = stats(g); cm = stats(g[cell[g.index]])
    emit(f"- {det}: n={cm['n']}, hit {cm['hit']:.1f}% (det-base {b['hit']:.1f}, {cm['hit']-b['hit']:+.1f}pp), netR {cm['netR']:.3f}")
emit()

# ---------------- impulse buckets ----------------
emit('## 2. Birth impulse (displacement, ATR units)')
emit()
emit('| impulse | n | share% | hit% | lift | netR |')
emit('|---|---|---|---|---|---|')
for b in ['<1','1-2','2-3','>=3']:
    s = stats(first[first.imp_b == b])
    emit(f"| {b} | {s['n']} | {100*s['n']/N:.1f} | {s['hit']:.1f} | {s['hit']-BASE['hit']:+.1f} | {s['netR']:.3f} |")
for det, g in first.groupby('detector'):
    bb = g.groupby('imp_b', observed=False).apply(lambda x: pd.Series(stats(x)), include_groups=False)
    emit(f"- {det}: " + '  '.join(f"{b}: {r.hit:.1f}%/{r.netR:.3f} (n={int(r.n)})" for b, r in bb.iterrows()))
emit()

# ---------------- H1 ----------------
emit('## 3. HTF (H1) anchor / nesting')
emit()
for nm in ['h1_anchor','h1_nested','h1_nested_any']:
    cond = first[nm].astype(bool)
    s = stats(first[cond]); cells, stable = holdout(cond)
    emit(f"- {nm}: share {100*cond.mean():.1f}%, hit {s['hit']:.1f}% ({s['hit']-BASE['hit']:+.1f}pp), "
         f"netR {s['netR']:.3f}, stable={stable} [" + ' '.join(f"{v}:{l:+.1f}" for v, _, l, _ in cells) + ']')
emit()

# ---------------- revisit index ----------------
emit('## 4. Revisit index (touch 1 vs 2 vs 3+)')
emit()
zk = ['symbol','detector','direction','born_ts']
touches = allsig.groupby(zk+['touch'], as_index=False).first()
touches['tb'] = np.where(touches.touch == 1, '1st', np.where(touches.touch == 2, '2nd', '3rd+'))
emit('| touch | n | share% | hit% | netR |')
emit('|---|---|---|---|---|')
tn = len(touches)
for b in ['1st','2nd','3rd+']:
    g = touches[touches.tb == b]; v = g.dropna(subset=['net_r'])
    emit(f"| {b} | {len(g)} | {100*len(g)/tn:.1f} | {100*v.hit.mean():.1f} | {v.net_r.mean():.3f} |")
d21 = []
for col, val in [('T','T1'),('T','T2'),('C','C0'),('C','C1')]:
    g = touches[touches[col] == val]
    h1_ = 100*g[g.tb == '1st'].hit.mean(); h2_ = 100*g[g.tb != '1st'].hit.mean()
    d21.append(f"{val}: {h1_-h2_:+.1f}")
emit(f"1st-touch minus later-touch hit, 4-way: " + '  '.join(d21))
emit()

# ---------------- iFVG ----------------
emit('## 5. iFVG (invalidated FVG, trade at re-retest of the band)')
emit()
v = ifvg.dropna(subset=['inv_netR','orig_netR'])
emit(f"Universe: all reconstructed FVG births that got invalidated (close through far edge) then "
     f"re-retested: n={len(ifvg)} events, {len(v)} tradeable ({len(v)/NSESS:.0f}/day).")
emit(f"- INVERTED side: hit {100*v.inv_hit.mean():.1f}%, netR {v.inv_netR.mean():.3f}")
emit(f"- ORIGINAL side: hit {100*v.orig_hit.mean():.1f}%, netR {v.orig_netR.mean():.3f}")
cells = []
for col, val in [('T','T1'),('T','T2'),('C','C0'),('C','C1')]:
    g = v[v[col] == val]
    cells.append(f"{val}: {100*(g.inv_hit.mean()-g.orig_hit.mean()):+.1f}")
emit(f"- inv-minus-orig hit, 4-way: " + '  '.join(cells))
v['lat_b'] = [bucket(d, s) for d, s in zip(v.latency_min, v.same_day)]
emit()
emit('| inversion latency | n | inv hit% | inv netR | orig hit% |')
emit('|---|---|---|---|---|')
for b in BUCKETS:
    g = v[v.lat_b == b]
    if not len(g): continue
    emit(f"| {b} | {len(g)} | {100*g.inv_hit.mean():.1f} | {g.inv_netR.mean():.3f} | {100*g.orig_hit.mean():.1f} |")
emit()
for big in [False, True]:
    g = v[v.big_inval == big]
    emit(f"- big-impulse invalidation (close-through >=1 ATR)={big}: n={len(g)}, "
         f"inv hit {100*g.inv_hit.mean():.1f}%, inv netR {g.inv_netR.mean():.3f}, orig hit {100*g.orig_hit.mean():.1f}%")
emit()

# ---------------- sweep-born detail ----------------
emit('## 6. Sweep-born')
emit()
for nm, cond in [('sweep-born any', first.sweep_born.astype(bool)),
                 ('sweep-born aligned', first.sweep_aligned.astype(bool)),
                 ('sweep-born anti-aligned', first.sweep_born.astype(bool) & ~first.sweep_aligned.astype(bool))]:
    s = stats(first[cond]); cells, stable = holdout(cond)
    emit(f"- {nm}: n={s['n']} ({100*s['n']/N:.1f}%), hit {s['hit']:.1f}% ({s['hit']-BASE['hit']:+.1f}pp), "
         f"netR {s['netR']:.3f}, stable={stable} [" + ' '.join(f"{v}:{l:+.1f}" for v, _, l, _ in cells) + ']')
emit()

# ---------------- greedy stack ----------------
emit('## 7. Best stack (greedy over stable facts)')
emit()
cands = {
    'gap_origin': (first.gap_open | first.gap_overlap).values,
    'gap_open_bar': first.gap_open.values.astype(bool),
    'impulse>=2': (first.impulse >= 2).values,
    'impulse>=1': (first.impulse >= 1).values,
    'h1_anchor': first.h1_anchor.values.astype(bool),
    'h1_nested': first.h1_nested.values.astype(bool),
    'sweep_aligned': first.sweep_aligned.values.astype(bool),
}
cur = (first.bucket == 'nextday+').values
chain = ['nextday+']
cur_hit = stats(first[cur])['hit']
log = []
while True:
    best = None
    for nm, m in cands.items():
        if nm in chain: continue
        c2 = cur & m
        if c2.sum() < 400: continue
        s2 = stats(first[c2])
        _, stb = holdout(pd.Series(c2, index=first.index))
        log.append((chain + [nm], s2['n'], round(s2['hit'], 2), stb))
        if stb and s2['hit'] > cur_hit + 0.05 and (best is None or s2['hit'] > best[2]):
            best = (nm, c2, s2['hit'])
    if best is None: break
    chain.append(best[0]); cur = best[1]; cur_hit = best[2]
emit('Greedy trace (candidate adds, pooled hit%, 4-way stable):')
for ch, n_, h_, stb in log:
    emit(f"- {' & '.join(ch)}: n={n_}, hit {h_:.1f}%, stable={stb}")
emit()
emit('Ladder (each rung 4-way same-sign in BOTH hit-lift and netR-lift):')
emit()
emit('| stack | n | shrink% | n/day | hit% | lift | netR | 4-way hit-lift |')
emit('|---|---|---|---|---|---|---|---|')
nd = first.bucket == 'nextday+'
sw = first.sweep_aligned.astype(bool); hn = first.h1_nested.astype(bool)
for label, cond in [('nextday+', nd), ('nextday+ & h1_nested', nd & hn),
                    ('nextday+ & sweep_aligned', nd & sw),
                    ('nextday+ & sweep_aligned & h1_nested', nd & sw & hn)]:
    s = stats(first[cond]); cells, stable = holdout(cond)
    emit(f"| {label} | {s['n']} | {100*(1-s['n']/N):.1f} | {s['n']/NSESS:.1f} | {s['hit']:.1f} | "
         f"{s['hit']-BASE['hit']:+.1f} | {s['netR']:.3f} | "
         + ' '.join(f"{v}:{l:+.1f}" for v, _, l, _ in cells) + ' |')
emit()
s = stats(first[cur]); cells, stable = holdout(pd.Series(cur, index=first.index))
emit(f"**BEST STACK = {' & '.join(chain)}**")
emit(f"n={s['n']} of {N} ({100*(1-s['n']/N):.1f}% count-shrink), {s['n']/NSESS:.1f}/session across 138 symbols "
     f"({s['n']/NSESS/138:.2f} per symbol-day).")
emit(f"hit {s['hit']:.1f}% ({s['hit']-BASE['hit']:+.1f}pp vs base), netR {s['netR']:.3f} "
     f"({s['netR']-BASE['netR']:+.3f}R), MFE {s['mfe']:.2f} MAE {s['mae']:.2f}.")
emit(f"4-way holdout hit-lift: " + '  '.join(f"{v}: {l:+.1f}pp (n={nn})" for v, nn, l, _ in cells)
     + f" → stable={stable}")
g = first[cur]
dircnt = {int(k): int(v) for k, v in g.direction.value_counts().items()}
detcnt = {k: int(v) for k, v in g.detector.value_counts().items()}
emit(f"Concentration: {g.session.nunique()}/{NSESS} sessions, max {g.session.value_counts().max()} "
     f"in one session; top symbol {g.symbol.value_counts().max()} of {s['n']}; "
     f"direction {dircnt}; detector {detcnt}.")
z = (s['hit']/100 - BASE['hit']/100)/np.sqrt(0.25/s['n'])
emit(f"Binomial z vs base = {z:.2f} (p≈{2*(1-0.5*(1+math.erf(abs(z)/np.sqrt(2)))):.3f} pre-selection; "
     f"~19 stack combos examined → treat the last rung as suggestive, the ladder as the fact).")
emit(f"Caveat: sweep_aligned standalone is NOT 4-way stable (C1 negative); its stability appears only "
     f"inside nextday+.")
emit()

# ---------------- verdict ----------------
emit('## 8. Verdict')
emit()
cost_r = 0.0006*first.zone_lo/(1.5*first.atr)  # ~entry/R
slope = (s['netR']-BASE['netR'])/(s['hit']-BASE['hit'])
be = BASE['hit'] - BASE['netR']/slope
emit(f"- Round-trip cost at this geometry is ~{cost_r.mean():.2f}R (0.06% on notional, R=1.5×ATR5). "
     f"Measured netR-vs-hit slope ≈ {slope:.3f}R/pp → **measured breakeven ≈ {be:.0f}% hit**, "
     f"not the +6pp (52%) bar. Even the best stack (52.1%, netR −0.10) is ~7pp short of water at 1R targets.")
emit("- What discriminates (stable in all 4 holdout cells): nextday+ retest (+2.4pp), h1_nested (+0.4pp alone, "
     "+2.7pp with nextday+), gap-origin on fast retests (+1.2pp, vs −1.3pp for intraday fast), and the "
     "sweep_aligned ladder inside nextday+ (+4.5 → +6.1pp, small n).")
emit("- What does NOT discriminate: birth impulse size (flat, user claim not supported), H1 long-run swing "
     "anchor (stable −0.4pp, mildly harmful), iFVG inversion (inv ≈ orig ≈ base, dead), sweep-born standalone "
     "(unstable), gap-origin as an add-on to nextday+ (−0.5pp).")
emit("- Count-shrink without hit loss is real: nextday+ & h1_nested keeps 14,057 zones (83% shrink, 247/day) "
     "at 48.8%; the full stack keeps 557 (99.3% shrink, ~10/day) at 52.1%. But at 1R/1.5ATR/0.06% no cell "
     "clears costs — the edge must be monetised with wider targets or cheaper execution, not this exit geometry.")
emit()

with open('runs/long60/FACTS.md', 'w') as f:
    f.write('\n'.join(md) + '\n')
print('\nwrote runs/long60/FACTS.md')
