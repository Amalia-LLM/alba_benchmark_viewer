import sqlite3
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
# try known filenames, fall back to first .db in repo root
for candidate in ('pt_pt_conversation_evaluation.db','pt_pt_conversation_evaluations.db','evaluations.db','model_results.db','new_results.db'):
    p = root / candidate
    if p.exists():
        DB = p
        break
else:
    # fallback: first .db file in root
    dbs = list(root.glob('*.db'))
    DB = dbs[0] if dbs else root / 'pt_pt_conversation_evaluation.db'

if not DB.exists():
    print('DB not found:', DB)
    sys.exit(1)

con = sqlite3.connect(DB)
cur = con.cursor()

print('Tables and schemas:')
for name, sql in cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    print('\n--', name)
    print(sql)

# Try common column names
print('\nDistinct model names from any table columns named model or model_name:')
seen = set()
for tbl, in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    try:
        for col in cur.execute(f"PRAGMA table_info({tbl})"):
            if col[1].lower() in ('model','model_name','modelname'):
                for r in cur.execute(f"SELECT DISTINCT {col[1]} FROM {tbl} ORDER BY {col[1]} LIMIT 200"):
                    seen.add((tbl,col[1],r[0]))
    except Exception:
        pass

if not seen:
    print('No model columns found by heuristics')
else:
    for tbl,col,val in sorted(seen):
        print(f"{tbl}.{col}: {val}")

con.close()