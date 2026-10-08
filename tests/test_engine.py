import itertools
import math
import unittest
from collections import defaultdict
from dataclasses import replace

import engine as E


def independent_distribution(stats, coefficients, n, pair, g):
    """Different derivation: clipped Binomial K, then two fair splits.

    Does not use the production terminal-pity DP.
    """
    selected, other = tuple(pair), tuple(i for i in range(4) if i not in pair)
    k_dist = defaultdict(float)
    for k in range(n + 1):
        k_dist[max(k, g)] += math.comb(n, k) / 2 ** n
    result = defaultdict(float)
    for k, pk in k_dist.items():
        for a in range(k + 1):
            for b in range(n - k + 1):
                counts = [0] * 4
                counts[selected[0]], counts[selected[1]] = a, k - a
                counts[other[0]], counts[other[1]] = b, n - k - b
                mass = pk * math.comb(k, a) / 2 ** k * math.comb(n - k, b) / 2 ** (n - k)
                choices = [[coefficients[i] * v for v in E.STAT_DATA[stats[i]][1]]
                           for i, count in enumerate(counts) for _ in range(count)]
                for sequence in itertools.product(*choices):
                    result[sum(sequence)] += mass / 4 ** n
    return result


class ModelTests(unittest.TestCase):
    def test_count_probabilities_all_guarantees(self):
        # Selected rows have contribution 1; unselected 0 in each tier.
        # Derive selected-count probabilities via fractional selected rolls.
        for n in (4, 5):
            for g in (2, 3, 4):
                dp = {(0, 0): 1.0}
                for step in range(n):
                    nxt = defaultdict(float)
                    for (k, s), p in dp.items():
                        forced = g - k >= n - step
                        options = [(1, 1.)] if forced else [(0, .5), (1, .5)]
                        for hit, q in options:
                            nxt[k + hit, s + hit] += p * q
                    dp = nxt
                observed = {k: p for (k, _), p in dp.items()}
                expected = defaultdict(float)
                for k in range(n + 1):
                    expected[max(k, g)] += math.comb(n, k) / 2 ** n
                self.assertEqual(observed, dict(expected))
                self.assertAlmostEqual(sum(observed.values()), 1.)

    def test_general_weights_against_independent_derivation(self):
        stats = ("er", "def_pct", "cd", "cr")
        # Distinct integer coefficients ensure all four rows contribute.
        coeff = (3, 5, 7, 11)
        for g in (2, 3, 4):
            actual = E.upgrade_distribution(stats, coeff, 4, (0, 3), g)
            expected = independent_distribution(stats, coeff, 4, (0, 3), g)
            self.assertEqual(set(actual), set(expected))
            for score in actual:
                self.assertAlmostEqual(actual[score], expected[score], places=13)

    def test_screenshot_inference(self):
        first = replace(E.SAMPLES[0], initial=None, rows=tuple(replace(r, hits=None) for r in E.SAMPLES[0].rows))
        inf = E.infer(first)
        self.assertEqual(set(inf.initial_prob), {4})
        self.assertEqual([s["hits"] for s in inf.row_summary], [{2}, {0}, {2}, {1}])
        second = E.infer(E.SAMPLES[1])
        self.assertEqual(set(second.initial_prob), {3})
        self.assertEqual([s["hits"] for s in second.row_summary], [{1}, {2}, {1}, {0}])
        self.assertTrue(first.rows[2].base is None)
        self.assertAlmostEqual(second.row_summary[0]["base_probs"][1], .25)

    def test_regression_two_screenshots(self):
        expected = [
            [(0.41078694661458326, .3026935841469563), (.7680460611979167, .3956354924093183), (1., 1.1691427545758935)],
            [(.17405414581298717, .08427242752997972), (.48098977406819665, .15086549573697844), (.9990590413411459, .9609082618207737)],
        ]
        for sample, values in zip(E.SAMPLES, expected):
            inf = E.infer(sample)
            for g, (win, gain) in zip((2,3,4), values):
                r = E.analyze(inf, guarantee=g)
                self.assertAlmostEqual(r["pwin"], win, places=12)
                self.assertAlmostEqual(r["gain"], gain, places=12)
                self.assertAlmostEqual(sum(p for _,p in r["distribution"]), 1., places=12)
                self.assertAlmostEqual(r["final_mean"] - inf.current_mean, r["gain"], places=12)
                self.assertAlmostEqual(r["per_dust"], r["gain"] / sample.cost)

    def test_growth_tiers_survive_four_effective_stats(self):
        a = replace(E.SAMPLES[1], rows=tuple(replace(r, weight="1") for r in E.SAMPLES[1].rows))
        inf = E.infer(a)
        r = E.analyze(inf)
        self.assertGreater(len(r["distribution"]), 10)
        self.assertGreater(r["gain"], 0)
        self.assertTrue(0 < r["pwin"] < 1)
        self.assertAlmostEqual(r["raw_mean"],
                               sum(h.base_score*h.probability for h in inf.hypotheses)/inf.scale + 4, places=10)

    def test_third_effective_unselected_stat(self):
        a = E.SAMPLES[1]
        b = replace(a, rows=tuple(replace(r, weight="1") if r.stat == "em" else r for r in a.rows))
        ra, rb = E.analyze(E.infer(a)), E.analyze(E.infer(b))
        self.assertGreater(rb["gain"], ra["gain"])
        self.assertGreater(rb["pwin"], ra["pwin"])

    def test_five_effective_upgrades_and_unselected_er(self):
        from verification import manual_three_effective as manual
        art=replace(E.SAMPLES[0], rows=tuple(replace(r,weight="1") if r.stat=="er" else r for r in E.SAMPLES[0].rows))
        inf=E.infer(art)
        self.assertEqual(inf.effective_hits,(5,5))
        self.assertGreater(inf.row_summary[0]["score_mean"],3)
        self.assertEqual(inf.row_summary[1]["score_mean"],0)
        self.assertAlmostEqual(sum(s["score_mean"] for s in inf.row_summary),inf.current_mean,places=12)
        self.assertAlmostEqual(inf.current_mean,manual.current,places=12)
        for pair in ((2,3),(0,2),(0,3)):
            self.assertAlmostEqual(E.infer(replace(art,selected=pair)).current_mean,inf.current_mean,places=12)
        for g in (2,3,4):
            actual=E.analyze(inf,guarantee=g)
            for key in ("pwin","gain","raw_mean","final_mean"):
                self.assertAlmostEqual(actual[key],manual.results[g][key],places=11)

    def test_known_base_narrows_range(self):
        a = E.SAMPLES[0]
        b = replace(a, rows=tuple(replace(r, base=2) if r.stat == "cd" else r for r in a.rows))
        rr = E.analyze(E.infer(b))
        self.assertAlmostEqual(rr["gain_range"][0], rr["gain_range"][1], places=12)

    def test_no_weight_no_gain(self):
        a = replace(E.SAMPLES[1], rows=tuple(replace(r,weight="0") for r in E.SAMPLES[1].rows))
        r = E.analyze(E.infer(a))
        self.assertEqual(r["pwin"], 0)
        self.assertEqual(r["gain"], 0)
        self.assertEqual(r["distribution"], [(0.,1.)])

    def test_validation(self):
        a = E.SAMPLES[0]
        for invalid in (replace(a,selected=(0,1,2)), replace(a,initial=3),
                        replace(a,rows=tuple(replace(r,weight="nan") for r in a.rows)),
                        replace(a,rows=tuple(replace(r,weight="-1") for r in a.rows)),
                        replace(a,main_stat="cr")):
            with self.assertRaises(ValueError):
                E.infer(invalid)

    def test_portable_config_round_trip(self):
        self.assertEqual(E.artifact_from_dict(E.artifact_to_dict(E.SAMPLES[0])), E.SAMPLES[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
