from __future__ import annotations
import csv
import html
import re
from pathlib import Path
import engine as E

def parse_substat_text(text):
    aliases = {"暴击伤害": "cd", "暴伤": "cd", "爆伤": "cd", "暴击率": "cr", "暴率": "cr",
               "元素充能效率": "er", "充能效率": "er", "元素精通": "em",
               "生命值": "hp", "攻击力": "atk", "防御力": "def"}
    names = "|".join(sorted(aliases, key=len, reverse=True))
    pattern = rf"({names})\s*([%％]?)\s*[:：+＋]?\s*(\d+(?:\.\d+)?)\s*([%％]?)"
    matches = re.findall(pattern, text.replace(",", "").replace("，", ""))
    if len(matches) != 4:
        raise ValueError("需要四条副属性及数值。每条一行，例如「暴击率+6.6%」；不要包含主属性。")
    rows = []
    for name, before_pct, value, after_pct in matches:
        key = aliases[name]
        if key in ("hp", "atk", "def") and (before_pct or after_pct):
            key += "_pct"
        rows.append((key, value))
    if len(set(key for key, _ in rows)) != 4:
        raise ValueError("四条副属性必须不同。百分比攻击／生命／防御请带上 %。")
    return rows

def fmt(value, digits=3):
    return f"{value:.{digits}f}"

def pc(value):
    if 0 < value < 0.00005:
        return "<0.01%"
    if 0.99995 < value < 1-1e-12:
        return ">99.99%"
    return f"{100 * value:.2f}%"

def score_details(inf):
    """Display all weighted contributions independently of guarantee targets."""
    art=inf.artifact
    counted=[]
    excluded=[]
    for row, summary in zip(art.rows, inf.row_summary):
        name=E.STAT_DATA[row.stat][0]
        if E.parse_weight(row.weight)>0:
            counted.append(f"{name} {summary['score_mean']:.3f}（权重{float(row.weight):g}）")
        else:
            excluded.append(name)
    breakdown=" ＋ ".join(counted) if counted else "全部权重为0"
    if excluded:
        breakdown+="；不计分："+"、".join(excluded)+"（权重0）"
    totals=sorted({h.n for h in inf.hypotheses})
    lo,hi=inf.effective_hits
    hits=str(lo) if lo==hi else f"{lo}～{hi}"
    total=str(totals[0]) if len(totals)==1 else f"{totals[0]}～{totals[-1]}"
    note=f"有效强化 {hits} / 总强化 {total} 次（不含基础出现）"
    if len(totals)==1 and lo==hi==totals[0]:
        note+=" · 已全部命中有效属性；仍可能通过成长档位或权重分配提升。"
    return breakdown,note

def inference_text(inf):
    art = inf.artifact
    breakdown, hit_note=score_details(inf)
    lines = [art.name, f"部位：{art.slot} · 每次消耗{art.cost}枚尘",
             "初始词条：" + " / ".join(f"{initial}条（{pc(p)}）" for initial, p in sorted(inf.initial_prob.items())),
             f"当前评分：{inf.current_mean:.6f}；合法范围 {inf.current_range[0]:.6f}～{inf.current_range[1]:.6f}",
             breakdown, hit_note,
             "所有正权重属性均计分；勾选只决定两条保底目标。", "", "逐条核查"]
    for row, summary in zip(art.rows, inf.row_summary):
        suffix = "%" if E.STAT_DATA[row.stat][2] else ""
        lines.extend([f"{E.STAT_DATA[row.stat][0]}  {row.value}{suffix}  · 权重 {row.weight}",
                      "  强化次数：" + " / ".join(map(str, sorted(summary["hits"]))) + "（不含基础出现）",
                      "  基础档位：" + " / ".join(f"{b}档 {pc(summary['base_probs'][b])}" for b in sorted(summary["bases"]))])
    lines.extend(["", "推断如何进行", "根据面板舍入后的数值，枚举合法基础档位与每次成长档位；再约束总强化次数为4或5。",
                  "条件估计假设原始随机强化、四档各25%；基础档位已知时可直接指定。",
                  "仅凭满级截图不能确定每次强化的先后，也不能总是确定基础档位。历史重塑择优或挑选偏好可能影响条件估计的先验。",
                  "合法范围不依赖把某个候选基础档位直接定死；它不是统计置信区间。",
                  "初始三/四词条均可能时暂按两种模型等先验；请尽量根据强化次数选定。",
                  "", "精度", "使用两位小数成长数据表和游戏显示精度（百分比一位小数、固定值整数）。",
                  "评分由有理数换成整数格点计算，未合并临近分数；图表分箱只用于展示。",
                  "两位小数表与游戏内部浮点值可能有微小差异，舍入边界附近需核查。"])
    return "\n".join(lines)

INPUT_GUIDE = """换一件圣遗物，需要填什么？

点击右上角「＋ 新建圣遗物」：清空当前值和旧结果，进入自己的圣遗物录入。
也可在已有输入上直接修改；修改后旧结果会明确标记为待更新。

必填信息
1. 部位：花、羽、沙、杯、冠，决定本次耗尘。
2. 四条副属性的类型与满级当前值。
3. 选择两条游戏保底目标，以及本次保底2/3/4次。

初始三条还是四条：知道就填写，不知道可选自动推断。
有效属性权重可设1、小数或其他正数；不需要的设0。三/四条有效都支持。
默认暴击率和暴伤各1。权重与保底目标独立，保底目标仍只能选两条。

数值怎样输入
暴击率6.6% → 选「暴击率」，当前值填6.6。
暴伤20.2% → 选「暴击伤害」，当前值填20.2。
防御力+42 → 选「防御力」，当前值填42。
防御力+5.8% → 选「防御力%」，当前值填5.8。
元素精通+23 → 当前值填23。

点击「粘贴属性文字」可一次填写四条，例如：
暴击率+6.6%
暴击伤害+20.2%
防御力+42
元素精通+23

可选信息
名称只用于区分圣遗物；套装名称与主属性数值不参与本次副词条重塑评分。
高级设置包含追加强化次数、基础档位和主属性类型校验。
不知道就全部保留自动，不需要知道每一次强化的完整历史。
追加强化次数不含基础出现的那一次，须为0～5。
高级信息已知时，可以缩小基础档位不确定性造成的收益范围。

四条副属性须来自五星+20圣遗物。输入修改后点击计算才能更新结果。
「样例对照」专门比较原先提供的两件截图，不会把它们当作当前自定义圣遗物。
"""

RULE_TEXT = """模型与收益口径

五星满级圣遗物：初始三条有4次强化，初始四条有5次强化。
四种副属性和基础成长值保留；重塑重新抽取强化落点和成长档位。
每次成长使用四档具体数值，各档25%。平均成长只用于统一评分单位。

两条保底目标合计至少命中2 / 3 / 4次。剩余次数刚好等于尚缺保底次数时，强制落入所选两条；否则四条各25%。强制阶段两条各50%。
此概率模型依据社区分析；官方保证次数，并未公布全部随机实现。

计分：S = Σ 权重 × 副属性实际值 / 该属性一次成长均值。
默认暴击率、暴击伤害各1，其他0。任意1～4条可设正权重。
主属性不计副词条评分；其类型只用来校验输入。

期望净增 = E[max(新分数－当前分数, 0)]。
提升概率 = P(新分数 > 当前分数)。相等时算无提升。
每枚尘收益 = 期望净增 / 本次消耗。
目标达成概率 = P(净增 ≥ 目标值)。目标设0时为100%。

规则：花、羽1枚；沙、杯、冠2枚。保留旧结果也消耗尘。
每6枚尘对应一次高阶机会，按高阶、高阶、谕告循环。
本版直接选择本次保底2/3/4，不自动替你推算账户进度。
祝圣之霜定义的圣遗物应锁定最初指定的两条目标。

三个或四个有效词条
未被选作保底目标的有效属性仍纳入评分和全部概率。
可以比较六种目标组合，按择优保留后的期望净增排序。
四条权重相等也可能因原成品成长品质不同而产生收益。

输入精度与未知档位
截图无法唯一确定基础档位时，显示条件估计及合法范围。
条件估计带有原始随机强化的先验假设；范围不是置信区间。
计算采用已列明的两位小数成长表，不声称复现内部浮点细节。
评分提升不是角色伤害百分比，也不包含充能阈值或暴击溢出。
所有计算离线执行，不读取游戏、不连接账号。
"""

def svg_chart(result):
    dist = result["distribution"]
    bins = [0.] * 40
    xmax = max(.5, result["maximum"])
    for x, p in dist:
        if x > 0:
            bins[min(39, int(x / xmax * 40))] += p
    ymax = max(.02, max(bins)) * 1.1
    rects = []
    for i, p in enumerate(bins):
        height = p / ymax * 170
        rects.append(f'<rect x="{45+i*16}" y="{200-height:.2f}" width="14" height="{height:.2f}" fill="#69d8c2"/>')
    return '<svg viewBox="0 0 740 250" xmlns="http://www.w3.org/2000/svg">' + ''.join(rects) + \
        f'<text x="45" y="230" fill="#9daec0">0</text><text x="630" y="230" fill="#9daec0">{xmax:.2f} 等效词条</text>' \
        f'<text x="45" y="23" fill="#edc47b">保留原状：{pc(result["no_gain"])}</text></svg>'

def save_report(path, inference, results, pair):
    art = inference.artifact
    r = results[pair, art.guarantee]
    table = "".join(f"<tr><td>{g}</td><td>{pc(results[pair,g]['pwin'])}</td><td>{results[pair,g]['gain']:.6f}</td><td>{results[pair,g]['per_dust']:.6f}</td><td>{results[pair,g]['gain_range'][0]:.6f}～{results[pair,g]['gain_range'][1]:.6f}</td></tr>" for g in (2,3,4))
    targets = "＋".join(E.STAT_DATA[art.rows[i].stat][0] for i in pair)
    counted = "＋".join(E.STAT_DATA[row.stat][0] for row in art.rows if E.parse_weight(row.weight)>0) or "无"
    breakdown,hit_note=score_details(inference)
    sources = "".join(f'<li><a href="{html.escape(url)}">{html.escape(title)}</a></li>' for title,url in E.SOURCES)
    document = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>启圣之尘收益报告</title><style>body{{background:#101720;color:#edf3fa;font:16px/1.7 "Microsoft YaHei",sans-serif;margin:36px auto;max-width:1060px;padding:0 24px}}h1{{font-size:30px}}h2{{font-size:20px;color:#69d8c2}}.cards{{display:flex;gap:18px}}.card{{background:#223142;padding:20px;flex:1;border-radius:10px}}strong{{display:block;font-size:28px;color:#69d8c2}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px;border-bottom:1px solid #304255;text-align:left}}pre{{white-space:pre-wrap;font:14px/1.8 "Microsoft YaHei",sans-serif;background:#182330;padding:20px}}a{{color:#69d8c2}}.note{{color:#edc47b}}@media print{{body{{background:white;color:black}}pre,.card{{background:#eee;color:black}}}}</style>
<h1>启圣之尘 · 收益报告</h1><p>{html.escape(art.name)} · 计分：{html.escape(counted)} · 保底目标：{html.escape(targets)} · 保底{art.guarantee}次 · 消耗{art.cost}枚</p>
<h2>当前总评分 {inference.current_mean:.3f}</h2><p>{html.escape(breakdown)}<br>{html.escape(hit_note)}</p>
<div class="cards"><div class="card">提升概率<strong>{pc(r['pwin'])}</strong></div><div class="card">期望净增<strong>{r['gain']:.6f}</strong></div><div class="card">每枚尘收益<strong>{r['per_dust']:.6f}</strong></div></div>
<p class="note">基础档位条件估计；净增合法范围 {r['gain_range'][0]:.6f}～{r['gain_range'][1]:.6f}。评分单位为等效平均词条。</p>
<h2>三档保底比较</h2><table><tr><th>保底</th><th>提升概率</th><th>期望净增</th><th>每枚尘收益</th><th>净增合法范围</th></tr>{table}</table>
<h2>净提升分布</h2>{svg_chart(r)}<p>当前均分 {inference.current_mean:.6f}；新结果均分 {r['raw_mean']:.6f}；择优后均分 {r['final_mean']:.6f}。<br>至少净增{art.target_gain}条概率：{pc(r['target_probability'])}；成功时平均净增 {r['success_gain']:.6f}。</p>
<h2>输入与推断</h2><pre>{html.escape(inference_text(inference))}</pre><h2>模型</h2><pre>{html.escape(RULE_TEXT)}</pre><h2>来源</h2><ul>{sources}</ul><p>版本 {E.VERSION}。完整离散分布见同名 CSV。此报告离线生成。</p></html>'''
    path.write_text(document, encoding="utf-8")
    with path.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["净提升_等效平均词条", "概率", "至少该净提升的概率"])
        dist = r["distribution"]
        tail = 1.
        for gain, p in dist:
            writer.writerow([f"{gain:.12f}", f"{p:.15f}", f"{tail:.15f}"])
            tail -= p
