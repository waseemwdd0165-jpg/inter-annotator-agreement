"""
Agreement between raters, and where it breaks down.

Seven years of rating work taught me that the useful question is never "how
much did we agree". It is "which boundary did we disagree on". Two raters at
82 percent agreement who split evenly across every label have a different
problem from two raters at 82 percent who agree on everything except one pair
of labels that nobody can tell apart. The first pair needs training. The
second needs the guideline rewritten.

So this computes the usual numbers, and then it points at the boundary.

No dependencies. Python 3.8 and up.
"""

from collections import Counter, defaultdict
from itertools import combinations


class Judgements:
    """Labels from several raters over the same items.

    Stored as {item_id: {rater_id: label}}, because that is the shape every
    question here needs: who said what about which item.
    """

    def __init__(self):
        self._by_item = defaultdict(dict)

    # ---------- loading ----------

    def add(self, item, rater, label):
        self._by_item[str(item)][str(rater)] = str(label)
        return self

    @classmethod
    def from_rows(cls, rows):
        """rows of (item, rater, label)."""
        j = cls()
        for item, rater, label in rows:
            j.add(item, rater, label)
        return j

    @classmethod
    def from_csv(cls, path, item_col='item', rater_col='rater', label_col='label'):
        import csv
        with open(path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            missing = [c for c in (item_col, rater_col, label_col)
                       if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(
                    'missing column(s) %s; found %s'
                    % (', '.join(missing), ', '.join(reader.fieldnames or [])))
            return cls.from_rows(
                (r[item_col], r[rater_col], r[label_col]) for r in reader)

    @classmethod
    def from_jsonl(cls, path, item_key='item', rater_key='rater', label_key='label'):
        import json
        j = cls()
        with open(path, encoding='utf-8') as fh:
            for n, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError as e:
                    raise ValueError('line %d is not valid JSON: %s' % (n, e))
                j.add(o[item_key], o[rater_key], o[label_key])
        return j

    # ---------- what is in here ----------

    @property
    def raters(self):
        seen = set()
        for labels in self._by_item.values():
            seen.update(labels)
        return sorted(seen)

    @property
    def items(self):
        return sorted(self._by_item)

    @property
    def labels(self):
        seen = set()
        for labels in self._by_item.values():
            seen.update(labels.values())
        return sorted(seen)

    def label_of(self, item, rater):
        return self._by_item[str(item)].get(str(rater))

    def items_rated_by(self, *raters):
        """Only the items every one of these raters actually judged.

        Rating sets are almost never complete. Quietly treating a missing
        label as a disagreement is how agreement numbers end up wrong.
        """
        raters = [str(r) for r in raters]
        return [i for i in self.items
                if all(r in self._by_item[i] for r in raters)]

    # ---------- the numbers ----------

    def confusion(self, rater_a, rater_b):
        """{(label_a, label_b): count} over items both of them rated."""
        out = Counter()
        for i in self.items_rated_by(rater_a, rater_b):
            out[(self._by_item[i][str(rater_a)], self._by_item[i][str(rater_b)])] += 1
        return out

    def percent_agreement(self, rater_a, rater_b):
        shared = self.items_rated_by(rater_a, rater_b)
        if not shared:
            return None
        same = sum(1 for i in shared
                   if self._by_item[i][str(rater_a)] == self._by_item[i][str(rater_b)])
        return same / len(shared)

    def cohens_kappa(self, rater_a, rater_b):
        """Agreement above what two raters with these habits would hit by luck.

        Returns None when it cannot be computed rather than a misleading
        number: no shared items, or both raters used exactly one label for
        everything, which makes chance agreement 1 and the formula undefined.
        """
        shared = self.items_rated_by(rater_a, rater_b)
        n = len(shared)
        if n == 0:
            return None

        po = self.percent_agreement(rater_a, rater_b)
        count_a = Counter(self._by_item[i][str(rater_a)] for i in shared)
        count_b = Counter(self._by_item[i][str(rater_b)] for i in shared)
        pe = sum((count_a[l] / n) * (count_b[l] / n)
                 for l in set(count_a) | set(count_b))
        if abs(1 - pe) < 1e-12:
            return None
        return (po - pe) / (1 - pe)

    def fleiss_kappa(self):
        """For three or more raters, over items every rater judged.

        Fleiss' kappa needs the same number of judgements on every item, so
        anything partially rated is left out and reported separately by
        report().
        """
        raters = self.raters
        n = len(raters)
        if n < 2:
            return None
        complete = self.items_rated_by(*raters)
        N = len(complete)
        if N == 0:
            return None

        labels = self.labels
        counts = []
        for i in complete:
            row = Counter(self._by_item[i][r] for r in raters)
            counts.append([row[l] for l in labels])

        p_i = [(sum(c * c for c in row) - n) / (n * (n - 1)) for row in counts]
        p_bar = sum(p_i) / N
        p_j = [sum(row[j] for row in counts) / (N * n) for j in range(len(labels))]
        pe = sum(p * p for p in p_j)
        if abs(1 - pe) < 1e-12:
            return None
        return (p_bar - pe) / (1 - pe)

    # ---------- where it breaks down ----------

    def disagreements(self, rater_a, rater_b):
        """Every item the two of them called differently, so you can go read them."""
        out = []
        for i in self.items_rated_by(rater_a, rater_b):
            a = self._by_item[i][str(rater_a)]
            b = self._by_item[i][str(rater_b)]
            if a != b:
                out.append((i, a, b))
        return out

    def worst_boundary(self, rater_a, rater_b):
        """The pair of labels these two mix up most, and how often.

        This is the line in the guideline that needs rewriting. Returns
        (label_x, label_y, count) with the pair in a stable order, or None
        when they never disagreed.
        """
        pairs = Counter()
        for _, a, b in self.disagreements(rater_a, rater_b):
            pairs[tuple(sorted((a, b)))] += 1
        if not pairs:
            return None
        (x, y), count = pairs.most_common(1)[0]
        return (x, y, count)

    def accuracy_against(self, rater, gold):
        """How often one rater matched the gold standard, overall and per label."""
        shared = self.items_rated_by(rater, gold)
        if not shared:
            return None
        hits = 0
        per_label = defaultdict(lambda: [0, 0])   # label -> [hits, total]
        for i in shared:
            g = self._by_item[i][str(gold)]
            r = self._by_item[i][str(rater)]
            per_label[g][1] += 1
            if g == r:
                hits += 1
                per_label[g][0] += 1
        return {
            'n': len(shared),
            'accuracy': hits / len(shared),
            'per_label': {l: (h / t if t else None) for l, (h, t) in per_label.items()},
        }

    # ---------- putting it together ----------

    def report(self, gold=None):
        raters = [r for r in self.raters if r != str(gold)] if gold else self.raters
        pairs = []
        for a, b in combinations(raters, 2):
            pairs.append({
                'raters': (a, b),
                'n': len(self.items_rated_by(a, b)),
                'percent_agreement': self.percent_agreement(a, b),
                'cohens_kappa': self.cohens_kappa(a, b),
                'worst_boundary': self.worst_boundary(a, b),
                'disagreements': self.disagreements(a, b),
            })

        complete = self.items_rated_by(*self.raters) if len(self.raters) > 1 else []
        return {
            'raters': raters,
            'labels': self.labels,
            'items': len(self.items),
            'items_rated_by_everyone': len(complete),
            'items_partially_rated': len(self.items) - len(complete),
            'pairs': pairs,
            'fleiss_kappa': self.fleiss_kappa() if len(raters) > 2 else None,
            'against_gold': (
                {r: self.accuracy_against(r, gold) for r in raters} if gold else None
            ),
        }


# ---------- reading the numbers out loud ----------

def strength(kappa):
    """Landis and Koch, with the caveat that these bands are a convention,
    not a law. A kappa of 0.61 on a two-label task is not the same news as
    0.61 on a nine-label one."""
    if kappa is None:
        return 'not computable'
    if kappa < 0:     return 'worse than chance'
    if kappa < 0.21:  return 'slight'
    if kappa < 0.41:  return 'fair'
    if kappa < 0.61:  return 'moderate'
    if kappa < 0.81:  return 'substantial'
    return 'almost perfect'


def pct(x):
    return '-' if x is None else '%.1f%%' % (100 * x)


def num(x):
    return '-' if x is None else '%.3f' % x


def format_report(rep, show_disagreements=10):
    out = []
    w = out.append
    w('%d items, %d raters, %d labels'
      % (rep['items'], len(rep['raters']), len(rep['labels'])))
    if rep['items_partially_rated']:
        w('%d item(s) were not rated by everyone and are left out of the '
          'all-rater figures' % rep['items_partially_rated'])
    w('')

    for p in rep['pairs']:
        a, b = p['raters']
        k = p['cohens_kappa']
        w('%s vs %s   n=%d   agreement %s   kappa %s (%s)'
          % (a, b, p['n'], pct(p['percent_agreement']), num(k), strength(k)))
        wb = p['worst_boundary']
        if wb:
            w('    most confused: %s vs %s, %d time(s)' % wb)
        if show_disagreements and p['disagreements']:
            for item, la, lb in p['disagreements'][:show_disagreements]:
                w('    %-18s %s said %s, %s said %s' % (item, a, la, b, lb))
            extra = len(p['disagreements']) - show_disagreements
            if extra > 0:
                w('    ... and %d more' % extra)
        w('')

    if rep['fleiss_kappa'] is not None:
        k = rep['fleiss_kappa']
        w('Fleiss kappa across all raters: %s (%s)' % (num(k), strength(k)))
        w('')

    if rep['against_gold']:
        w('Against the gold standard')
        for r, res in sorted(rep['against_gold'].items()):
            if not res:
                w('  %-10s no shared items' % r)
                continue
            w('  %-10s %s over %d items' % (r, pct(res['accuracy']), res['n']))
            for label, acc in sorted(res['per_label'].items()):
                w('      %-16s %s' % (label, pct(acc)))
    return '\n'.join(out).rstrip()
