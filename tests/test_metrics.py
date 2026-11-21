import unittest

from eval.metrics import (
    format_count,
    hit_at_k,
    mcnemar_exact,
    reciprocal_rank,
    to_one_indexed,
    wilson_interval,
)

RANKED = [("A", 3), ("B", 7), ("A", 9)]


class RetrievalMetrics(unittest.TestCase):
    def test_hit_at_k_respects_cutoff(self):
        gold = {("A", 9)}
        self.assertFalse(hit_at_k(RANKED, gold, 2))
        self.assertTrue(hit_at_k(RANKED, gold, 3))

    def test_doc_must_match_not_only_page(self):
        self.assertFalse(hit_at_k(RANKED, {("C", 3)}, 3))

    def test_multi_page_gold(self):
        self.assertTrue(hit_at_k(RANKED, {("X", 1), ("B", 7)}, 3))

    def test_reciprocal_rank(self):
        self.assertEqual(reciprocal_rank(RANKED, {("B", 7)}), 0.5)
        self.assertEqual(reciprocal_rank(RANKED, {("Z", 1)}), 0.0)

    def test_zero_indexed_conversion(self):
        self.assertEqual(to_one_indexed(0), 1)


class Statistics(unittest.TestCase):
    def test_wilson_known_value(self):
        low, high = wilson_interval(8, 10)
        self.assertAlmostEqual(low, 0.490, places=3)
        self.assertAlmostEqual(high, 0.943, places=3)

    def test_wilson_edges_and_width(self):
        self.assertEqual(wilson_interval(0, 20)[0], 0.0)
        self.assertEqual(wilson_interval(20, 20)[1], 1.0)
        small = wilson_interval(8, 10)
        large = wilson_interval(80, 100)
        self.assertGreater(small[1] - small[0], large[1] - large[0])

    def test_wilson_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            wilson_interval(1, 0)
        with self.assertRaises(ValueError):
            wilson_interval(11, 10)

    def test_mcnemar_known_values(self):
        self.assertAlmostEqual(mcnemar_exact(10, 2), 0.0386, places=4)
        self.assertEqual(mcnemar_exact(5, 5), 1.0)
        self.assertEqual(mcnemar_exact(0, 0), 1.0)

    def test_format_count(self):
        self.assertTrue(format_count(117, 150).startswith("117/150 (78.0%"))


if __name__ == "__main__":
    unittest.main()
