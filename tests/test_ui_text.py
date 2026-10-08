import unittest
from common import parse_substat_text


class TextInputTests(unittest.TestCase):
    def test_game_panel_text(self):
        self.assertEqual(parse_substat_text("暴击率+6.6%\n暴击伤害+20.2%\n防御力+42\n元素精通+23"),
                         [("cr","6.6"),("cd","20.2"),("def","42"),("em","23")])

    def test_percentage_and_flat_are_distinct(self):
        self.assertEqual(parse_substat_text("攻击力%：5.8\n攻击力+19\n防御力＋5.8％\n元素充能效率 18.1%"),
                         [("atk_pct","5.8"),("atk","19"),("def_pct","5.8"),("er","18.1")])

    def test_extra_main_stat_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_substat_text("生命值4780\n暴击率6.6%\n暴击伤害20.2%\n防御力42\n元素精通23")

    def test_duplicates_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_substat_text("暴击率6.6%\n暴击率3.9%\n防御力42\n元素精通23")


if __name__ == "__main__":
    unittest.main(verbosity=2)
