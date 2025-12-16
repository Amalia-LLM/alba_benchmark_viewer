"""Populate `evaluations.raw_output` from JSON files in `pt-pt-eval/`.

Usage:
    python scripts/add_raw_output.py [--apply] [--db PATH] [--evals-dir PATH]

Dry-run by default; use --apply to modify DB. Creates DB backup before applying.
"""
import argparse
import json
import shutil
import sqlite3
from collections import defaultdict, Counter
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
    dbs = list(ROOT.glob('*.db'))
    if dbs:
        return dbs[0]
    raise FileNotFoundError('No .db file found in repo root')


def slug_from_filename(name: str) -> str:
    import re
    m = re.match(r"^[^_]+_(.+?)\.json$", name)
    if not m:
        return name.rsplit('.', 1)[0]
    slug = m.group(1)
    slug = re.sub(r"_+pt-pt$", "", slug)
    return slug


def build_raw_mapping(evals_dir: Path):
    # mapping: (slug, prompt_id) -> raw_output
    mapping = {}
    slug_to_display = {}
    for p in sorted(evals_dir.glob('*.json')):
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Skipping {p.name}: can't parse JSON ({e})")
            continue
        if not data:
            continue
        slug = slug_from_filename(p.name)
        # determine model_name inside if present
        inside_names = Counter()
        for obj in data:
            if isinstance(obj, dict) and 'model_name' in obj:
                inside_names[obj['model_name']] += 1
        if inside_names:
            slug_to_display[slug] = inside_names.most_common(1)[0][0]
        # collect raw_output per prompt_id
        for obj in data:
            if not isinstance(obj, dict):
                continue
            prompt_id = obj.get('prompt_id') or obj.get('conversation_id')
            raw = obj.get('raw_output')
            if prompt_id and raw:
                # use first non-empty raw_output
                key = (slug, prompt_id)
                if key not in mapping:
                    mapping[key] = raw
    return mapping, slug_to_display


def column_exists(conn, table, column):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == column for r in cur.fetchall())


def backup_db(db_path: Path):
    stamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    dest = db_path.with_suffix(db_path.suffix + f'.bak.{stamp}')
    shutil.copy2(db_path, dest)
    return dest


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

    mapping, slug_to_display = build_raw_mapping(evals_dir)
    print(f"Found {len(mapping)} (slug,prompt) raw outputs from JSON files.")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    has_column = column_exists(conn, 'evaluations', 'raw_output')
    print('\nDB has raw_output column:', has_column)

    # plan updates: for each (slug,prompt) try to match rows by model_name == slug OR model_name == display_name
    planned = []  # list of dicts
    no_match = []
    total_rows = 0
    for (slug, prompt), raw in mapping.items():
        # try slug
        cur.execute("SELECT COUNT(*) FROM evaluations WHERE model_name = ? AND conversation_id = ?", (slug, prompt))
        cnt_slug = cur.fetchone()[0]
        cnt_display = 0
        display = slug_to_display.get(slug)
        if display:
            cur.execute("SELECT COUNT(*) FROM evaluations WHERE model_name = ? AND conversation_id = ?", (display, prompt))
            cnt_display = cur.fetchone()[0]
        if cnt_slug + cnt_display == 0:
            no_match.append((slug, display, prompt))
            continue
        planned.append({'slug': slug, 'display': display, 'prompt': prompt, 'raw': raw, 'cnt_slug': cnt_slug, 'cnt_display': cnt_display})
        total_rows += cnt_slug + cnt_display

    print(f"\nPlanned pairs with matches: {len(planned)} (affects approx {total_rows} rows)")
    if no_match:
        print(f"Pairs with no matching DB rows: {len(no_match)}")
        if len(no_match) <= 20:
            for s,d,p in no_match:
                print('  ', s, '->', d, p)

    # show a sample of planned updates
    print('\nSample planned updates (truncated raw_output):')
    for item in planned[:10]:
        print(f"  {item['slug']} / {item['prompt']}  -> rows slug:{item['cnt_slug']} display:{item['cnt_display']}")
        print('    raw (truncated):', repr(item['raw'][:200]))

    if not args.apply:
        print('\nDry-run: no changes made. Rerun with --apply to perform changes.')
        conn.close()
        raise SystemExit(0)

    # apply changes
    bak = backup_db(db_path)
    print(f"\nBackup created at: {bak}")

    if not has_column:
        print('Adding raw_output column to evaluations...')
        cur.execute("ALTER TABLE evaluations ADD COLUMN raw_output TEXT")
        conn.commit()

    updated_rows = 0
    for item in planned:
        raw = item['raw']
        # update rows where model_name matches slug
        if item['cnt_slug']:
            cur.execute("UPDATE evaluations SET raw_output = ? WHERE model_name = ? AND conversation_id = ? AND (raw_output IS NULL OR raw_output = '')", (raw, item['slug'], item['prompt']))
            updated_rows += cur.rowcount
        # update rows where model_name matches display (if present)
        if item['cnt_display'] and item['display']:
            cur.execute("UPDATE evaluations SET raw_output = ? WHERE model_name = ? AND conversation_id = ? AND (raw_output IS NULL OR raw_output = '')", (raw, item['display'], item['prompt']))
            updated_rows += cur.rowcount
    conn.commit()

    print(f"\nApplied updates: {updated_rows} rows updated")
    # verification sample
    print('\nVerification sample (first 10 rows with non-empty raw_output):')
    for r in cur.execute("SELECT model_name, conversation_id, substr(raw_output,1,200) FROM evaluations WHERE raw_output IS NOT NULL LIMIT 10"):
        print(' ', r)
    conn.close()
    print('\nDone.')