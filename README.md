# rater-agreement

[![tests](https://github.com/waseemwdd0165-jpg/inter-annotator-agreement/actions/workflows/ci.yml/badge.svg)](https://github.com/waseemwdd0165-jpg/inter-annotator-agreement/actions/workflows/ci.yml)

**Agreement between raters, and the label boundary they keep tripping over.**

Seven years of rating work taught me that the useful question is never *how
much did we agree*. It is *which boundary did we disagree on*.

Two raters at 60 percent who split evenly across every label have a different
problem from two raters at 60 percent who agree on everything except one pair
of labels nobody can tell apart. The first pair needs training. The second
needs the guideline rewritten. A single agreement number cannot tell you which
one you are looking at, so this prints the number and then points at the
boundary.

No dependencies. Python 3.8 and up. Standard library only.

---

## Try it

```
python3 cli.py sample/ratings.csv --gold gold
```

```
20 items, 2 raters, 4 labels
1 item(s) were not rated by everyone and are left out of the all-rater figures

asha vs rahul   n=20   agreement 50.0%   kappa 0.340 (fair)
    most confused: Moderately Meets vs Slightly Meets, 5 time(s)
    q002               asha said Slightly Meets, rahul said Moderately Meets
    q005               asha said Highly Meets, rahul said Moderately Meets
    q007               asha said Slightly Meets, rahul said Moderately Meets
    q008               asha said Slightly Meets, rahul said Fails to Meet
    q010               asha said Slightly Meets, rahul said Moderately Meets
    q011               asha said Slightly Meets, rahul said Moderately Meets
    q014               asha said Moderately Meets, rahul said Highly Meets
    q015               asha said Fails to Meet, rahul said Slightly Meets
    q016               asha said Slightly Meets, rahul said Moderately Meets
    q018               asha said Fails to Meet, rahul said Slightly Meets

Against the gold standard
  asha       57.9% over 19 items
      Fails to Meet    75.0%
      Highly Meets     80.0%
      Moderately Meets 16.7%
      Slightly Meets   75.0%
  rahul      78.9% over 19 items
      Fails to Meet    75.0%
      Highly Meets     80.0%
      Moderately Meets 83.3%
      Slightly Meets   75.0%
```

Read that bottom block again. Asha is at 75 to 80 percent on three of the four
labels and **16.7 percent on Moderately Meets** — she calls it Slightly Meets
almost every time. That is not a careless rater. That is one sentence in the
guideline that draws the line in a place she reads differently, and it is
costing five of the ten disagreements on its own.

Fix that sentence and her agreement moves more than a week of retraining would.

---

## What it reports

| | |
|---|---|
| **Percent agreement** | Per pair, over the items both of them actually rated |
| **Cohen's kappa** | Agreement above what two raters with those habits would hit by luck |
| **Fleiss' kappa** | For three or more raters, over items everyone judged |
| **Most confused pair** | The two labels a pair mixes up most, and how often |
| **The disagreements** | Named item by item, so you can go and read them |
| **Against a gold standard** | Overall accuracy and, more usefully, accuracy per label |
| **Confusion matrix** | Both directions counted separately |

---

## Three things it refuses to do

**It does not treat a missing label as a disagreement.** Rating sets are almost
never complete. Every pairwise figure is computed only over items both raters
touched, and the report says how many items were left out.

**It returns `None` instead of a wrong number.** If both raters used one label
for everything, chance agreement is 1 and kappa is undefined. Reporting `0.0`
there would read as "no better than chance", which is a different claim from
"this cannot be computed". Same for a pair with no shared items.

**It does not tell you 0.61 is good.** The `strength()` bands are the Landis and
Koch convention and they are printed as a convenience, not a verdict. A kappa of
0.61 on a two-label task is not the same news as 0.61 on a nine-label one.

---

## Input

CSV or JSONL, one judgement per row.

```csv
item,rater,label
q001,asha,Highly Meets
q001,rahul,Highly Meets
q002,asha,Slightly Meets
```

```json
{"item": "q001", "rater": "asha", "label": "Highly Meets"}
```

Column and key names are options if yours differ:

```
python3 cli.py ratings.csv --item id --rater annotator --label verdict
python3 cli.py ratings.jsonl --format jsonl --json
```

| Option | |
|---|---|
| `--gold RATER` | Treat that rater id as the gold standard and score the others against it |
| `--show N` | List at most N disagreements per pair, `0` for none |
| `--json` | Print the whole report as JSON instead of text |
| `--format` | `csv` or `jsonl`, defaults to the file extension |

---

## As a library

```python
from agreement import Judgements, format_report

j = Judgements.from_csv('ratings.csv')

j.percent_agreement('asha', 'rahul')     # 0.5
j.cohens_kappa('asha', 'rahul')          # 0.34
j.worst_boundary('asha', 'rahul')        # ('Moderately Meets', 'Slightly Meets', 5)
j.disagreements('asha', 'rahul')         # [(item, label_a, label_b), ...]
j.accuracy_against('asha', gold='gold')  # {'n':…, 'accuracy':…, 'per_label': {…}}

print(format_report(j.report(gold='gold')))
```

---

## Tests

```
python3 -m unittest -v
```

30 tests, no test framework to install. They run on every push, on Python 3.8
through 3.13 — the badge at the top is that run. The same build then runs the
command line over both sample files and fails unless the CSV reader and the
JSONL reader produce byte-identical reports, which is the one thing the unit
tests cannot check: a reader that quietly dropped a row would still pass them.

The kappa cases are **worked out by hand in the comments** and the test asserts
the hand-computed answer. That matters here: the easy way to test a statistic is
to compute it with the same code you are testing, which proves nothing except
that the code agrees with itself. So the main Cohen's case is a 50-item
confusion matrix whose arithmetic is written out line by line and lands on
exactly 0.40, and the Fleiss cases are small enough to verify on paper — perfect
agreement gives 1, an even split every time gives -1.

The rest cover the refusals above: no shared items, a single label used for
everything, partially rated items, a malformed JSONL line naming its own line
number.

---

## Why I built it

I rank model responses, rate search results against Needs Met and Page Quality,
and label spans for training data. The part of that work nobody talks about is
what happens when two careful people read the same guideline and land in
different places. The number tells you it happened. Only the breakdown tells
you where to go and fix it.

Waseem Ahmad Ansari · [portfolio](https://waseemwdd0165-jpg.github.io) ·
[LinkedIn](https://www.linkedin.com/in/waseem-ahmad-ansari-bba5771ab/)
# rater-agreement

**Agreement between raters, and the label boundary they keep tripping over.**

Seven years of rating work taught me that the useful question is never *how
much did we agree*. It is *which boundary did we disagree on*.

Two raters at 60 percent who split evenly across every label have a different
problem from two raters at 60 percent who agree on everything except one pair
of labels nobody can tell apart. The first pair needs training. The second
needs the guideline rewritten. A single agreement number cannot tell you which
one you are looking at, so this prints the number and then points at the
boundary.

No dependencies. Python 3.8 and up. Standard library only.

---

## Try it

```
python3 cli.py sample/ratings.csv --gold gold
```

```
20 items, 2 raters, 4 labels
1 item(s) were not rated by everyone and are left out of the all-rater figures

asha vs rahul   n=20   agreement 50.0%   kappa 0.340 (fair)
    most confused: Moderately Meets vs Slightly Meets, 5 time(s)
    q002               asha said Slightly Meets, rahul said Moderately Meets
    q005               asha said Highly Meets, rahul said Moderately Meets
    q007               asha said Slightly Meets, rahul said Moderately Meets
    q008               asha said Slightly Meets, rahul said Fails to Meet
    q010               asha said Slightly Meets, rahul said Moderately Meets
    q011               asha said Slightly Meets, rahul said Moderately Meets
    q014               asha said Moderately Meets, rahul said Highly Meets
    q015               asha said Fails to Meet, rahul said Slightly Meets
    q016               asha said Slightly Meets, rahul said Moderately Meets
    q018               asha said Fails to Meet, rahul said Slightly Meets

Against the gold standard
  asha       57.9% over 19 items
      Fails to Meet    75.0%
      Highly Meets     80.0%
      Moderately Meets 16.7%
      Slightly Meets   75.0%
  rahul      78.9% over 19 items
      Fails to Meet    75.0%
      Highly Meets     80.0%
      Moderately Meets 83.3%
      Slightly Meets   75.0%
```

Read that bottom block again. Asha is at 75 to 80 percent on three of the four
labels and **16.7 percent on Moderately Meets** — she calls it Slightly Meets
almost every time. That is not a careless rater. That is one sentence in the
guideline that draws the line in a place she reads differently, and it is
costing five of the ten disagreements on its own.

Fix that sentence and her agreement moves more than a week of retraining would.

---

## What it reports

| | |
|---|---|
| **Percent agreement** | Per pair, over the items both of them actually rated |
| **Cohen's kappa** | Agreement above what two raters with those habits would hit by luck |
| **Fleiss' kappa** | For three or more raters, over items everyone judged |
| **Most confused pair** | The two labels a pair mixes up most, and how often |
| **The disagreements** | Named item by item, so you can go and read them |
| **Against a gold standard** | Overall accuracy and, more usefully, accuracy per label |
| **Confusion matrix** | Both directions counted separately |

---

## Three things it refuses to do

**It does not treat a missing label as a disagreement.** Rating sets are almost
never complete. Every pairwise figure is computed only over items both raters
touched, and the report says how many items were left out.

**It returns `None` instead of a wrong number.** If both raters used one label
for everything, chance agreement is 1 and kappa is undefined. Reporting `0.0`
there would read as "no better than chance", which is a different claim from
"this cannot be computed". Same for a pair with no shared items.

**It does not tell you 0.61 is good.** The `strength()` bands are the Landis and
Koch convention and they are printed as a convenience, not a verdict. A kappa of
0.61 on a two-label task is not the same news as 0.61 on a nine-label one.

---

## Input

CSV or JSONL, one judgement per row.

```csv
item,rater,label
q001,asha,Highly Meets
q001,rahul,Highly Meets
q002,asha,Slightly Meets
```

```json
{"item": "q001", "rater": "asha", "label": "Highly Meets"}
```

Column and key names are options if yours differ:

```
python3 cli.py ratings.csv --item id --rater annotator --label verdict
python3 cli.py ratings.jsonl --format jsonl --json
```

| Option | |
|---|---|
| `--gold RATER` | Treat that rater id as the gold standard and score the others against it |
| `--show N` | List at most N disagreements per pair, `0` for none |
| `--json` | Print the whole report as JSON instead of text |
| `--format` | `csv` or `jsonl`, defaults to the file extension |

---

## As a library

```python
from agreement import Judgements, format_report

j = Judgements.from_csv('ratings.csv')

j.percent_agreement('asha', 'rahul')     # 0.5
j.cohens_kappa('asha', 'rahul')          # 0.34
j.worst_boundary('asha', 'rahul')        # ('Moderately Meets', 'Slightly Meets', 5)
j.disagreements('asha', 'rahul')         # [(item, label_a, label_b), ...]
j.accuracy_against('asha', gold='gold')  # {'n':…, 'accuracy':…, 'per_label': {…}}

print(format_report(j.report(gold='gold')))
```

---

## Tests

```
python3 -m unittest -v
```

30 tests, no test framework to install.

The kappa cases are **worked out by hand in the comments** and the test asserts
the hand-computed answer. That matters here: the easy way to test a statistic is
to compute it with the same code you are testing, which proves nothing except
that the code agrees with itself. So the main Cohen's case is a 50-item
confusion matrix whose arithmetic is written out line by line and lands on
exactly 0.40, and the Fleiss cases are small enough to verify on paper — perfect
agreement gives 1, an even split every time gives -1.

The rest cover the refusals above: no shared items, a single label used for
everything, partially rated items, a malformed JSONL line naming its own line
number.

---

## Why I built it

I rank model responses, rate search results against Needs Met and Page Quality,
and label spans for training data. The part of that work nobody talks about is
what happens when two careful people read the same guideline and land in
different places. The number tells you it happened. Only the breakdown tells
you where to go and fix it.

Waseem Ahmad Ansari · [portfolio](https://waseemwdd0165-jpg.github.io) ·
[LinkedIn](https://www.linkedin.com/in/waseem-ahmad-ansari-bba5771ab/)
