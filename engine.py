"""Deterministic artifact reshaping model; no Monte Carlo or score binning.

Four equally likely upgrade tiers, uniform existing-substat selection, terminal
guarantee enforcement. Base rolls are retained; upgrading rolls are resampled.
Unknown bases are conditioned on visible values and optional upgrade counts.
The posterior assumes an unselected, randomly upgraded original artifact.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, product
from math import factorial, isfinite, lcm, sqrt
from typing import Callable

VERSION = "2.1.0"
STAT_DATA = {
    "hp": ("生命值", (20913, 23900, 26888, 29875), False),
    "atk": ("攻击力", (1362, 1556, 1751, 1945), False),
    "def": ("防御力", (1620, 1852, 2083, 2315), False),
    "hp_pct": ("生命值%", (408, 466, 525, 583), True),
    "atk_pct": ("攻击力%", (408, 466, 525, 583), True),
    "def_pct": ("防御力%", (510, 583, 656, 729), True),
    "em": ("元素精通", (1632, 1865, 2098, 2331), False),
    "er": ("元素充能效率", (453, 518, 583, 648), True),
    "cr": ("暴击率", (272, 311, 350, 389), True),
    "cd": ("暴击伤害", (544, 622, 699, 777), True),
}
STAT_KEYS = tuple(STAT_DATA)
SLOTS = ("生之花", "死之羽", "时之沙", "空之杯", "理之冠")
SOURCES = [
    ("官方公告：重塑对象、保底与消耗", "https://bbs.4399.cn/thread-view-tid-49304493"),
    ("KQM：副属性成长档位与随机强化", "https://keqingmains.com/misc/artifacts/"),
    ("Genshin Optimizer：成长数值数据", "https://github.com/frzyc/genshin-optimizer/blob/master/libs/gi/stats/Data/Artifacts/artifact_sub.json"),
    ("社区原始分析：末尾补足保底", "https://tooflesswulf.github.io/genshin-reshape-dumpstat/"),
    ("独立社区实现：保留基础值并卷积强化", "https://github.com/Mreak233/Genshin-Artifact-Reroll"),
]


@dataclass(frozen=True)
class Row:
    stat: str
    value: str
    weight: str = "0"
    hits: int | None = None
    base: int | None = None  # 0..3 (lowest..highest)


@dataclass(frozen=True)
class Artifact:
    name: str
    slot: str
    initial: int | None
    rows: tuple[Row, ...]
    selected: tuple[int, int]
    guarantee: int = 2
    target_gain: float = 1.0
    defined: bool = False
    main_stat: str = ""

    @property
    def cost(self):
        return 1 if self.slot in SLOTS[:2] else 2


@dataclass
class Hypothesis:
    n: int
    base_score: int
    current_score: int
    probability: float


@dataclass
class Inference:
    artifact: Artifact
    coeff: tuple[int, ...]
    scale: int
    hypotheses: list[Hypothesis]
    row_summary: list[dict]
    initial_prob: dict[int, float]
    current_mean: float
    current_range: tuple[float, float]
    uncertain: bool
    combination_count: int
    effective_hits: tuple[int, int]


def parse_weight(text):
    try:
        value = Decimal(str(text))
    except InvalidOperation:
        raise ValueError("权重须为非负数字。") from None
    if not value.is_finite() or not 0 <= value <= 1000:
        raise ValueError("权重须在 0～1000 之间。")
    if value != value.quantize(Decimal("0.001")):
        raise ValueError("权重最多保留三位小数。")
    return Fraction(value)


@lru_cache(maxsize=256)
def roll_sums(stat, count):
    dist = Counter({0: 1})
    for _ in range(count):
        nxt = Counter()
        for total, ways in dist.items():
            for roll in STAT_DATA[stat][1]:
                nxt[total + roll] += ways
        dist = nxt
    return dict(dist)


def visible_value(stat, total):
    """Half-up to game display precision from two-decimal table sums."""
    quantum = 10 if STAT_DATA[stat][2] else 100
    return (total + quantum // 2) // quantum * quantum


def row_candidates(row, n):
    if row.stat not in STAT_DATA:
        raise ValueError("请选择四条副属性。")
    try:
        entered = Decimal(str(row.value).strip().replace("%", "").replace(",", ""))
    except InvalidOperation:
        raise ValueError(f"{STAT_DATA[row.stat][0]}的数值格式不正确。") from None
    if not entered.is_finite() or entered <= 0:
        raise ValueError("副属性数值须大于 0。")
    quantum = Decimal("0.1") if STAT_DATA[row.stat][2] else Decimal("1")
    if entered != entered.quantize(quantum):
        raise ValueError("请输入游戏显示值：百分比一位小数，固定值为整数。")
    units = int(entered * 100)
    if row.hits is not None and not 0 <= row.hits <= n:
        raise ValueError("强化次数须为 0～5，且不超过总强化次数。")
    if row.base is not None and row.base not in range(4):
        raise ValueError("基础档位须为 1～4 档。")
    bases = range(4) if row.base is None else [row.base]
    counts = range(n + 1) if row.hits is None else [row.hits]
    out = []
    for hit in counts:
        for b in bases:
            base_value = STAT_DATA[row.stat][1][b]
            for increment, ways in roll_sums(row.stat, hit).items():
                total = base_value + increment
                if visible_value(row.stat, total) == units:
                    # Initial tier has a uniform prior when it is unknown.
                    likelihood = ways / 4 ** (hit + (row.base is None))
                    out.append((hit, b, base_value, total, likelihood))
    return out


def validate(artifact):
    if len(artifact.rows) != 4 or len(set(r.stat for r in artifact.rows)) != 4:
        raise ValueError("必须填写四条不同的副属性。")
    if artifact.slot not in SLOTS:
        raise ValueError("圣遗物部位不正确。")
    if artifact.initial not in (None, 3, 4):
        raise ValueError("初始词条须为 3、4 或自动推断。")
    if len(set(artifact.selected)) != 2 or any(i not in range(4) for i in artifact.selected):
        raise ValueError("保底目标必须且只能选两条；有效词条可为 1～4 条。")
    if artifact.guarantee not in (2, 3, 4):
        raise ValueError("保底次数须为 2、3 或4。")
    if not isfinite(artifact.target_gain) or artifact.target_gain < 0:
        raise ValueError("目标净提升须为非负数。")
    main = artifact.main_stat
    if artifact.slot == "生之花":
        main = "hp"
    if artifact.slot == "死之羽":
        main = "atk"
    if main in STAT_DATA and main in [r.stat for r in artifact.rows]:
        raise ValueError("主属性不能与副属性同类型（固定值与百分比是不同类型）。")


def infer(artifact):
    validate(artifact)
    fractions = [4 * parse_weight(r.weight) / sum(STAT_DATA[r.stat][1]) for r in artifact.rows]
    scale = lcm(*(f.denominator for f in fractions))
    coeff = tuple(int(f * scale) for f in fractions)
    ns = [artifact.initial + 1] if artifact.initial else [4, 5]
    joint = []
    for n in ns:
        candidates = [row_candidates(row, n) for row in artifact.rows]
        if any(not c for c in candidates):
            continue
        for combo in product(*candidates):
            if sum(c[0] for c in combo) != n:
                continue
            count_prior = factorial(n) / (4 ** n)
            for c in combo:
                count_prior /= factorial(c[0])
            likelihood = count_prior
            for c in combo:
                likelihood *= c[4]
            if likelihood:
                joint.append((n, combo, likelihood))
    if not joint:
        raise ValueError("数值、强化次数或初始词条数不一致。请核查输入；次数不包含基础出现一次。")
    z = sum(x[2] for x in joint)
    # Unknown initial-line count has no source-independent prior. Use equal
    # model prior and explicitly report each possibility in the UI.
    hypotheses = defaultdict(float)
    summaries = [dict(hits=set(), bases=set(), totals=set(), base_probs=defaultdict(float),
                      score_mean=0.0) for _ in range(4)]
    effective_hits = set()
    initial_prob = defaultdict(float)
    for n, combo, mass in joint:
        p = mass / z
        base = sum(coeff[i] * combo[i][2] for i in range(4))
        current = sum(coeff[i] * combo[i][3] for i in range(4))
        hypotheses[n, base, current] += p
        initial_prob[n - 1] += p
        effective_hits.add(sum(c[0] for i, c in enumerate(combo) if coeff[i] > 0))
        for i, c in enumerate(combo):
            summaries[i]["hits"].add(c[0])
            summaries[i]["bases"].add(c[1] + 1)
            summaries[i]["totals"].add(c[3])
            summaries[i]["base_probs"][c[1] + 1] += p
            summaries[i]["score_mean"] += coeff[i] * c[3] * p / scale
    hs = [Hypothesis(n, b, c, p) for (n, b, c), p in hypotheses.items()]
    current_mean = sum(h.current_score * h.probability for h in hs) / scale
    current_range = (min(h.current_score for h in hs) / scale, max(h.current_score for h in hs) / scale)
    return Inference(artifact, coeff, scale, hs, summaries, dict(initial_prob), current_mean, current_range,
                     len(hs) > 1 or any(len(s["bases"]) > 1 for s in summaries), len(joint),
                     (min(effective_hits), max(effective_hits)))


@lru_cache(maxsize=64)
def upgrade_distribution(stats, coeff, n, selected, g):
    """Integer-score DP. Probabilities are exact binary fractions until summing."""
    states = {(0, 0): 1.0}
    chosen = set(selected)
    for step in range(n):
        remaining = n - step
        next_states = defaultdict(float)
        for (picked, score), p in states.items():
            forced = g - picked >= remaining
            choices = selected if forced else range(4)
            prob = 1 / (len(choices) * 4)
            for i in choices:
                k = picked + (i in chosen)
                for roll in STAT_DATA[stats[i]][1]:
                    next_states[k, score + coeff[i] * roll] += p * prob
        states = next_states
    pmf = defaultdict(float)
    for (picked, score), p in states.items():
        if picked < g:
            raise AssertionError("Guarantee not enforced")
        pmf[score] += p
    return dict(pmf)


def quantile(dist, q):
    cumulative = 0.0
    for score, p in sorted(dist.items()):
        cumulative += p
        if cumulative + 1e-12 >= q:
            return score
    return max(dist)


def analyze(inference, selected=None, guarantee=None):
    art = inference.artifact
    selected = tuple(sorted(selected or art.selected))
    g = guarantee or art.guarantee
    scale = inference.scale
    stats = tuple(row.stat for row in art.rows)
    delta_pmf = defaultdict(float)
    raw_pmf = defaultdict(float)
    final_pmf = defaultdict(float)
    conditional = []
    threshold = art.target_gain * scale
    for h in inference.hypotheses:
        upgrade = upgrade_distribution(stats, inference.coeff, h.n, selected, g)
        pwin = gain = 0.0
        for addition, prob in upgrade.items():
            new_score = h.base_score + addition
            diff = new_score - h.current_score
            delta = max(diff, 0)
            p = prob * h.probability
            raw_pmf[new_score] += p
            final_pmf[max(new_score, h.current_score)] += p
            delta_pmf[delta] += p
            if diff > 0:
                pwin += prob
                gain += prob * diff / scale
        conditional.append((pwin, gain))
    z = sum(delta_pmf.values())
    for pmf in (delta_pmf, raw_pmf, final_pmf):
        for score in pmf:
            pmf[score] /= z
    pwin = sum(p for score, p in delta_pmf.items() if score > 0)
    gain = sum(s * p for s, p in delta_pmf.items()) / scale
    expected_raw = sum(s * p for s, p in raw_pmf.items()) / scale
    expected_final = sum(s * p for s, p in final_pmf.items()) / scale
    variance = sum((s / scale - gain) ** 2 * p for s, p in delta_pmf.items())
    ptarget = sum(p for s, p in delta_pmf.items() if s >= threshold - 1e-9)
    return dict(
        selected=selected, guarantee=g, pwin=max(0, min(1, pwin)), no_gain=delta_pmf.get(0, 0),
        gain=gain, per_dust=gain / art.cost, raw_mean=expected_raw, final_mean=expected_final,
        success_gain=gain / pwin if pwin > 1e-14 else 0, target_probability=ptarget,
        gain_range=(min(c[1] for c in conditional), max(c[1] for c in conditional)),
        pwin_range=(min(c[0] for c in conditional), max(c[0] for c in conditional)),
        median=quantile(delta_pmf, .5) / scale, p90=quantile(delta_pmf, .9) / scale,
        maximum=max(delta_pmf) / scale, stddev=sqrt(max(0, variance)),
        distribution=sorted((s / scale, p) for s, p in delta_pmf.items()),
        raw_distribution=sorted((s / scale, p) for s, p in raw_pmf.items()),
        final_distribution=sorted((s / scale, p) for s, p in final_pmf.items()),
    )


def analyze_all(artifact, progress: Callable | None = None):
    inference = infer(artifact)
    pairs = [tuple(sorted(artifact.selected))] if artifact.defined else list(combinations(range(4), 2))
    results = {}
    total = len(pairs) * 3
    done = 0
    for pair in pairs:
        for g in (2, 3, 4):
            results[pair, g] = analyze(inference, pair, g)
            done += 1
            if progress:
                progress(done, total)
    return inference, results


SAMPLES = (
    Artifact("染血骑士之杯 · 截图1", "空之杯", 4,
             (Row("er", "18.1", "0", 2), Row("def_pct", "5.8", "0", 0),
              Row("cd", "20.2", "1", 2), Row("cr", "5.4", "1", 1)), (2, 3), main_stat="atk_pct"),
    Artifact("生之花 · 截图2", "生之花", 3,
             (Row("cr", "6.6", "1", 1), Row("cd", "20.2", "1", 2),
              Row("def", "42", "0", 1), Row("em", "23", "0", 0)), (0, 1), main_stat="hp"),
)


def artifact_to_dict(artifact):
    from dataclasses import asdict
    return asdict(artifact)


def artifact_from_dict(data):
    data = dict(data)
    data["rows"] = tuple(Row(**row) for row in data["rows"])
    data["selected"] = tuple(data["selected"])
    return Artifact(**data)
