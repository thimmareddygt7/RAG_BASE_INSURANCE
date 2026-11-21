import unittest

from app.ingest.layout import order_blocks, strip_repeated_lines
from app.text import content_words, count_tokens, numbers, token_spans


class TextHelpers(unittest.TestCase):
    def test_token_counting_and_spans(self):
        self.assertEqual(count_tokens("Room rent: 6,000 per day."), 9)
        text = "a bc"
        self.assertEqual([text[s:e] for s, e in token_spans(text)], ["a", "bc"])

    def test_numbers_normalise_indian_and_western_grouping(self):
        self.assertEqual(numbers("limit 5,00,000 and 6,000 at 9%"), {"500000", "6000", "9"})

    def test_content_words_drop_stopwords_digits_and_plurals(self):
        self.assertEqual(content_words("What are the waiting periods in 2024?"),
                         ["waiting", "period"])


class Layout(unittest.TestCase):
    def test_two_columns_read_left_then_right(self):
        blocks = [(300, 100, 500, 120, "R1"), (50, 100, 250, 120, "L1"),
                  (300, 200, 500, 220, "R2"), (50, 200, 250, 220, "L2")]
        order = [b[4] for b in order_blocks(blocks, 600)]
        self.assertEqual(order, ["L1", "L2", "R1", "R2"])

    def test_full_width_heading_splits_segments(self):
        blocks = [(50, 50, 550, 70, "TITLE"), (50, 100, 250, 120, "L1"),
                  (300, 100, 500, 120, "R1")]
        self.assertEqual([b[4] for b in order_blocks(blocks, 600)], ["TITLE", "L1", "R1"])

    def test_single_column_is_top_to_bottom(self):
        blocks = [(50, 300, 400, 320, "B"), (50, 100, 400, 120, "A")]
        self.assertEqual([b[4] for b in order_blocks(blocks, 600)], ["A", "B"])

    def test_repeated_headers_footers_and_page_numbers_removed(self):
        pages = [f"ACME HEALTH POLICY\nreal content {i}\nPage {i} of 9" for i in range(1, 6)]
        cleaned = strip_repeated_lines(pages)
        for i, text in enumerate(cleaned, start=1):
            self.assertEqual(text.strip(), f"real content {i}")

    def test_too_few_pages_left_untouched(self):
        pages = ["H\nx\nPage 1", "H\ny\nPage 2"]
        self.assertEqual(strip_repeated_lines(pages), pages)


if __name__ == "__main__":
    unittest.main()
