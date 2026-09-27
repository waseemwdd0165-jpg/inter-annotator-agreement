#!/usr/bin/env python3
"""Command line front end for agreement.py.

    python cli.py sample/ratings.csv
    python cli.py sample/ratings.csv --gold gold
    python cli.py sample/ratings.jsonl --format jsonl --json
"""

import argparse
import json
import sys

from agreement import Judgements, format_report


def build_parser():
    p = argparse.ArgumentParser(
        prog='rater-agreement',
        description='Agreement between raters, and the label boundary they '
                    'disagree on most.')
    p.add_argument('path', help='CSV or JSONL of item, rater, label')
    p.add_argument('--format', choices=['csv', 'jsonl'], default=None,
                   help='defaults to the file extension')
    p.add_argument('--item', default='item', help='column or key for the item id')
    p.add_argument('--rater', default='rater', help='column or key for the rater id')
    p.add_argument('--label', default='label', help='column or key for the label')
    p.add_argument('--gold', default=None,
                   help='treat this rater id as the gold standard')
    p.add_argument('--show', type=int, default=10, metavar='N',
                   help='list at most N disagreements per pair (0 for none)')
    p.add_argument('--json', action='store_true',
                   help='print the report as JSON instead of text')
    return p


def load(args):
    fmt = args.format
    if fmt is None:
        fmt = 'jsonl' if args.path.lower().endswith(('.jsonl', '.ndjson')) else 'csv'
    if fmt == 'jsonl':
        return Judgements.from_jsonl(args.path, args.item, args.rater, args.label)
    return Judgements.from_csv(args.path, args.item, args.rater, args.label)


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        judgements = load(args)
    except (OSError, ValueError) as e:
        print('could not read %s: %s' % (args.path, e), file=sys.stderr)
        return 2

    if not judgements.items:
        print('no rows found in %s' % args.path, file=sys.stderr)
        return 2
    if len(judgements.raters) < 2:
        print('need at least two raters, found %d' % len(judgements.raters),
              file=sys.stderr)
        return 2
    if args.gold and args.gold not in judgements.raters:
        print('gold rater %r is not in the data; raters are %s'
              % (args.gold, ', '.join(judgements.raters)), file=sys.stderr)
        return 2

    report = judgements.report(gold=args.gold)
    if args.json:
        print(json.dumps(report, indent=2, default=list))
    else:
        print(format_report(report, show_disagreements=args.show))
    return 0


if __name__ == '__main__':
    sys.exit(main())
