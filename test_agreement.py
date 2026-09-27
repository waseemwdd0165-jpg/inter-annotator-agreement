"""Checks for agreement.py.

The kappa cases are worked out by hand in the comments, so a wrong answer
here is caught by arithmetic rather than by trusting the same code twice.

    python3 -m unittest -v
"""

import json
import os
import tempfile
import unittest

from agreement import Judgements, strength, format_report


def rows(pairs, rater):
    return [(item, rater, label) for item, label in pairs]


class PercentAgreement(unittest.TestCase):

    def test_perfect(self):
        j = Judgements.from_rows(
            rows([('1', 'good'), ('2', 'bad')], 'a') +
            rows([('1', 'good'), ('2', 'bad')], 'b'))
        self.assertEqual(j.percent_agreement('a', 'b'), 1.0)

    def test_none(self):
        j = Judgements.from_rows(
            rows([('1', 'good'), ('2', 'bad')], 'a') +
            rows([('1', 'bad'), ('2', 'good')], 'b'))
        self.assertEqual(j.percent_agreement('a', 'b'), 0.0)

    def test_half(self):
        j = Judgements.from_rows(
            rows([('1', 'good'), ('2', 'bad')], 'a') +
            rows([('1', 'good'), ('2', 'good')], 'b'))
        self.assertEqual(j.percent_agreement('a', 'b'), 0.5)

    def test_no_shared_items_is_none_not_zero(self):
        j = Judgements.from_rows(
            rows([('1', 'good')], 'a') +
            rows([('2', 'good')], 'b'))
        self.assertIsNone(j.percent_agreement('a', 'b'))


class CohensKappa(unittest.TestCase):

    def test_worked_example(self):
        """Confusion matrix [[20, 5], [10, 15]] over 50 items.

        observed agreement = (20 + 15) / 50                     = 0.70
        a says yes 25/50 = 0.5,  b says yes 30/50 = 0.6
        a says no  25/50 = 0.5,  b says no  20/50 = 0.4
        chance     = 0.5*0.6 + 0.5*0.4                          = 0.50
        kappa      = (0.70 - 0.50) / (1 - 0.50)                 = 0.40
        """
        data = []
        n = 0
        for a, b, count in [('yes', 'yes', 20), ('yes', 'no', 5),
                            ('no', 'yes', 10), ('no', 'no', 15)]:
            for _ in range(count):
                n += 1
                data.append((str(n), 'a', a))
                data.append((str(n), 'b', b))
        j = Judgements.from_rows(data)

        self.assertEqual(j.percent_agreement('a', 'b'), 0.70)
        self.assertAlmostEqual(j.cohens_kappa('a', 'b'), 0.40, places=10)

    def test_perfect_agreement_is_one(self):
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'y'), ('3', 'x'), ('4', 'y')], 'a') +
            rows([('1', 'x'), ('2', 'y'), ('3', 'x'), ('4', 'y')], 'b'))
        self.assertAlmostEqual(j.cohens_kappa('a', 'b'), 1.0, places=10)

    def test_agreement_purely_by_chance_is_zero(self):
        """Both raters say x half the time, and their agreements land exactly
        where chance predicts: observed 0.5, chance 0.5, so kappa is 0."""
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'x'), ('3', 'y'), ('4', 'y')], 'a') +
            rows([('1', 'x'), ('2', 'y'), ('3', 'x'), ('4', 'y')], 'b'))
        self.assertAlmostEqual(j.cohens_kappa('a', 'b'), 0.0, places=10)

    def test_systematic_disagreement_is_negative(self):
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'y')], 'a') +
            rows([('1', 'y'), ('2', 'x')], 'b'))
        self.assertLess(j.cohens_kappa('a', 'b'), 0)

    def test_one_label_used_for_everything_is_none(self):
        """Chance agreement is 1, so kappa is undefined. Returning 0 here
        would read as 'no better than chance', which is a different claim."""
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'x')], 'a') +
            rows([('1', 'x'), ('2', 'x')], 'b'))
        self.assertEqual(j.percent_agreement('a', 'b'), 1.0)
        self.assertIsNone(j.cohens_kappa('a', 'b'))

    def test_missing_labels_are_skipped_not_counted_as_disagreement(self):
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'y'), ('3', 'x')], 'a') +
            rows([('1', 'x'), ('2', 'y')], 'b'))
        self.assertEqual(j.items_rated_by('a', 'b'), ['1', '2'])
        self.assertEqual(j.percent_agreement('a', 'b'), 1.0)


class FleissKappa(unittest.TestCase):

    def test_full_agreement_is_one(self):
        """2 items, 2 raters, both agree, and the two items differ.

        P_i = (1/(n(n-1))) * (sum n_ij^2 - n) = (1/2)*(4-2) = 1 for each item
        p_x = p_y = 0.5, so chance = 0.25 + 0.25 = 0.5
        kappa = (1 - 0.5) / (1 - 0.5) = 1
        """
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'y')], 'a') +
            rows([('1', 'x'), ('2', 'y')], 'b'))
        self.assertAlmostEqual(j.fleiss_kappa(), 1.0, places=10)

    def test_total_split_is_minus_one(self):
        """Every item splits the raters evenly.

        P_i = (1/2)*(1 + 1 - 2) = 0, chance = 0.5
        kappa = (0 - 0.5) / (1 - 0.5) = -1
        """
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'x')], 'a') +
            rows([('1', 'y'), ('2', 'y')], 'b'))
        self.assertAlmostEqual(j.fleiss_kappa(), -1.0, places=10)

    def test_three_raters_runs_and_stays_in_range(self):
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'y'), ('3', 'x'), ('4', 'z')], 'a') +
            rows([('1', 'x'), ('2', 'y'), ('3', 'y'), ('4', 'z')], 'b') +
            rows([('1', 'x'), ('2', 'z'), ('3', 'x'), ('4', 'z')], 'c'))
        k = j.fleiss_kappa()
        self.assertIsNotNone(k)
        self.assertTrue(-1.0 <= k <= 1.0)

    def test_partially_rated_items_are_left_out(self):
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'y'), ('3', 'x')], 'a') +
            rows([('1', 'x'), ('2', 'y')], 'b') +
            rows([('1', 'x'), ('2', 'y')], 'c'))
        self.assertEqual(j.items_rated_by('a', 'b', 'c'), ['1', '2'])
        self.assertAlmostEqual(j.fleiss_kappa(), 1.0, places=10)


class WhereItBreaksDown(unittest.TestCase):

    def test_disagreements_name_the_items(self):
        j = Judgements.from_rows(
            rows([('a1', 'good'), ('a2', 'fair'), ('a3', 'bad')], 'r1') +
            rows([('a1', 'good'), ('a2', 'good'), ('a3', 'fair')], 'r2'))
        self.assertEqual(
            j.disagreements('r1', 'r2'),
            [('a2', 'fair', 'good'), ('a3', 'bad', 'fair')])

    def test_worst_boundary_finds_the_pair_they_cannot_split(self):
        """fair against good three times, bad against good once. The
        guideline problem is the fair/good line."""
        j = Judgements.from_rows(
            rows([('1', 'fair'), ('2', 'fair'), ('3', 'fair'), ('4', 'bad')], 'r1') +
            rows([('1', 'good'), ('2', 'good'), ('3', 'good'), ('4', 'good')], 'r2'))
        self.assertEqual(j.worst_boundary('r1', 'r2'), ('fair', 'good', 3))

    def test_worst_boundary_is_none_when_they_never_disagreed(self):
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'y')], 'a') +
            rows([('1', 'x'), ('2', 'y')], 'b'))
        self.assertIsNone(j.worst_boundary('a', 'b'))

    def test_confusion_counts_both_directions_separately(self):
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'y')], 'a') +
            rows([('1', 'y'), ('2', 'x')], 'b'))
        c = j.confusion('a', 'b')
        self.assertEqual(c[('x', 'y')], 1)
        self.assertEqual(c[('y', 'x')], 1)


class AgainstGold(unittest.TestCase):

    def test_accuracy_overall_and_per_label(self):
        j = Judgements.from_rows(
            rows([('1', 'good'), ('2', 'good'), ('3', 'bad'), ('4', 'bad')], 'gold') +
            rows([('1', 'good'), ('2', 'bad'),  ('3', 'bad'), ('4', 'bad')], 'r1'))
        res = j.accuracy_against('r1', 'gold')
        self.assertEqual(res['n'], 4)
        self.assertEqual(res['accuracy'], 0.75)
        self.assertEqual(res['per_label']['good'], 0.5)
        self.assertEqual(res['per_label']['bad'], 1.0)

    def test_gold_is_kept_out_of_the_rater_pairs(self):
        j = Judgements.from_rows(
            rows([('1', 'x')], 'gold') + rows([('1', 'x')], 'r1') +
            rows([('1', 'y')], 'r2'))
        rep = j.report(gold='gold')
        self.assertEqual(rep['raters'], ['r1', 'r2'])
        self.assertEqual([p['raters'] for p in rep['pairs']], [('r1', 'r2')])


class Loading(unittest.TestCase):

    def _write(self, name, text):
        path = os.path.join(self.dir.name, name)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        return path

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.dir.cleanup()

    def test_csv(self):
        path = self._write('r.csv',
                           'item,rater,label\n1,a,good\n1,b,good\n2,a,bad\n2,b,good\n')
        j = Judgements.from_csv(path)
        self.assertEqual(j.raters, ['a', 'b'])
        self.assertEqual(j.percent_agreement('a', 'b'), 0.5)

    def test_csv_with_other_column_names(self):
        path = self._write('r.csv', 'id,who,verdict\n1,a,good\n1,b,good\n')
        j = Judgements.from_csv(path, item_col='id', rater_col='who',
                                label_col='verdict')
        self.assertEqual(j.labels, ['good'])

    def test_csv_missing_column_says_which(self):
        path = self._write('r.csv', 'item,rater\n1,a\n')
        with self.assertRaises(ValueError) as cm:
            Judgements.from_csv(path)
        self.assertIn('label', str(cm.exception))

    def test_jsonl(self):
        path = self._write('r.jsonl', '\n'.join(
            json.dumps(o) for o in [
                {'item': '1', 'rater': 'a', 'label': 'good'},
                {'item': '1', 'rater': 'b', 'label': 'bad'},
            ]) + '\n')
        j = Judgements.from_jsonl(path)
        self.assertEqual(j.percent_agreement('a', 'b'), 0.0)

    def test_jsonl_bad_line_names_the_line_number(self):
        path = self._write('r.jsonl',
                           '{"item":"1","rater":"a","label":"good"}\nnot json\n')
        with self.assertRaises(ValueError) as cm:
            Judgements.from_jsonl(path)
        self.assertIn('line 2', str(cm.exception))

    def test_blank_lines_in_jsonl_are_ignored(self):
        path = self._write('r.jsonl',
                           '{"item":"1","rater":"a","label":"x"}\n\n'
                           '{"item":"1","rater":"b","label":"x"}\n')
        j = Judgements.from_jsonl(path)
        self.assertEqual(j.raters, ['a', 'b'])


class Reporting(unittest.TestCase):

    def test_report_counts_partial_items(self):
        j = Judgements.from_rows(
            rows([('1', 'x'), ('2', 'x'), ('3', 'x')], 'a') +
            rows([('1', 'x'), ('2', 'y')], 'b'))
        rep = j.report()
        self.assertEqual(rep['items'], 3)
        self.assertEqual(rep['items_rated_by_everyone'], 2)
        self.assertEqual(rep['items_partially_rated'], 1)

    def test_fleiss_only_reported_for_three_or_more(self):
        two = Judgements.from_rows(
            rows([('1', 'x')], 'a') + rows([('1', 'y')], 'b'))
        self.assertIsNone(two.report()['fleiss_kappa'])

    def test_format_report_mentions_the_worst_boundary(self):
        j = Judgements.from_rows(
            rows([('1', 'fair'), ('2', 'fair'), ('3', 'bad')], 'r1') +
            rows([('1', 'good'), ('2', 'good'), ('3', 'bad')], 'r2'))
        text = format_report(j.report())
        self.assertIn('most confused', text)
        self.assertIn('fair', text)
        self.assertIn('good', text)

    def test_strength_bands(self):
        self.assertEqual(strength(None), 'not computable')
        self.assertEqual(strength(-0.2), 'worse than chance')
        self.assertEqual(strength(0.10), 'slight')
        self.assertEqual(strength(0.30), 'fair')
        self.assertEqual(strength(0.50), 'moderate')
        self.assertEqual(strength(0.70), 'substantial')
        self.assertEqual(strength(0.90), 'almost perfect')


if __name__ == '__main__':
    unittest.main()
