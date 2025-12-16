"""Update DB `evaluations.model_name` using `model_name` inside JSON files in `pt-pt-eval/`.

Usage:
    python scripts/update_db_model_names.py [--apply] [--db PATH] [--evals-dir PATH]

By default this does a dry-run and prints proposed updates. Use --apply to actually modify the DB.
"""
import argparse
import json
import shutil
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / 'pt_pt_conversation_evaluations.db'
DEFAULT_EVALS = ROOT / 'pt-pt-eval'


def find_db(path=None):
    if path:
        p = Path(path)
        if p.exists():
            return p
        raise FileNotFoundError(p)
    for candidate in (DEFAULT_DB, ROOT / 'evaluations.db', ROOT / 'model_results.db', ROOT / 'new_results.db'):
        if candidate.exists():
            return candidate
    # fallback to first .db
    dbs = list(ROOT.glob('*.db'))
    if dbs:
        return dbs[0]
    raise FileNotFoundError('No .db file found in repo root')


def slug_from_filename(name: str) -> str:
    # match prefix until first underscore, capture rest before .json
    # e.g. 2025-12-15T20-46-37+0100_allenai_olmo-2-1124-7b-instruct.json
    import re
    m = re.match(r"^[^_]+_(.+?)\.json$", name)
    if not m:
        return name.rsplit('.', 1)[0]
    slug = m.group(1)
    # remove trailing _pt-pt or multiple underscores + pt-pt
    slug = re.sub(r"_+pt-pt$", "", slug)
    return slug


def build_mapping(evals_dir: Path):
    mapping = defaultdict(Counter)  # slug -> Counter(display_name)
    for p in sorted(evals_dir.glob('*.json')):
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Skipping {p.name}: can't parse JSON ({e})")
            continue
        if not data:
            print(f"Skipping {p.name}: empty JSON array")
            continue
        # try to read model_name from first object, fallback search
        model_names = set()
        for obj in data:
            if isinstance(obj, dict) and 'model_name' in obj:
                model_names.add(obj['model_name'])
        if not model_names:
            print(f"Skipping {p.name}: no 'model_name' key found")
            continue
        # pick the most common model_name among entries
        display = Counter(model_names).most_common(1)[0][0]
        slug = slug_from_filename(p.name)
        mapping[slug][display] += 1
    # resolve counters to single display names where unambiguous
    resolved = {}
    ambiguous = {}
    for slug, counter in mapping.items():
        if not counter:
            continue
        if len(counter) == 1:
            resolved[slug] = next(iter(counter))
        else:
            # multiple different model_name values in same file set
            ambiguous[slug] = dict(counter)
    return resolved, ambiguous


def get_distinct_db_model_names(conn):
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT model_name FROM evaluations ORDER BY model_name")
    return [r[0] for r in cur.fetchall()]


def plan_updates(conn, mapping):
    cur = conn.cursor()
    updates = []  # (old, new, count)
    for slug, new_name in mapping.items():
        cur.execute("SELECT COUNT(*) FROM evaluations WHERE model_name = ?", (slug,))
        count = cur.fetchone()[0]
        if count > 0 and slug != new_name:
            updates.append((slug, new_name, count))
    return updates


def backup_db(db_path: Path):
    stamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    dest = db_path.with_suffix(db_path.suffix + f'.bak.{stamp}')
    shutil.copy2(db_path, dest)
    return dest


def apply_updates(conn, updates):
    cur = conn.cursor()
    for old, new, count in updates:
        cur.execute("UPDATE evaluations SET model_name = ? WHERE model_name = ?", (new, old))
    conn.commit()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Apply updates to DB (default: dry-run)')
    ap.add_argument('--db', type=str, help='Path to DB file')
    ap.add_argument('--evals-dir', type=str, help='Path to JSON files dir', default=str(DEFAULT_EVALS))
    args = ap.parse_args()

    db_path = find_db(args.db)
    evals_dir = Path(args.evals_dir)
    if not evals_dir.exists():
        raise SystemExit(f"Evaluations dir not found: {evals_dir}")

    print(f"Using DB: {db_path}")
    print(f"Scanning JSON files in: {evals_dir}")
    mapping, ambiguous = build_mapping(evals_dir)

    if ambiguous:
        print('\nWARNING: Ambiguous model_name values found for the following slugs:')
        for slug, cnts in ambiguous.items():
            print(f"  {slug}: {cnts}")
        print('These slugs will be skipped. Resolve duplicates in JSON files if needed.')

    print('\nResolved mapping (slug -> model_name):')
    for k, v in sorted(mapping.items()):
        print(f"  {k} -> {v}")

    conn = sqlite3.connect(db_path)
    db_model_names = get_distinct_db_model_names(conn)
    print('\nDistinct model names currently in DB (sample):')
    for m in db_model_names:
        print('  ', m)

    updates = plan_updates(conn, mapping)
    if not updates:
        print('\nNo updates to perform.')
        conn.close()
        raise SystemExit(0)

    print('\nPlanned updates (old_slug -> new_display_name) and row counts:')
    for old, new, count in updates:
        print(f"  {old} -> {new}   ({count} rows)")

    if not args.apply:
        print('\nDry-run: no changes have been made. Rerun with --apply to make changes.')
        conn.close()
        raise SystemExit(0)

    # apply
    bak = backup_db(db_path)
    print(f"\nBackup created at: {bak}")
    apply_updates(conn, updates)
    print('\nUpdates applied successfully. Verifying...')
    for old, new, _ in updates:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM evaluations WHERE model_name = ?", (new,))
        print(f"  Now {new}: {cur.fetchone()[0]} rows")
    conn.close()
    print('\nDone.')