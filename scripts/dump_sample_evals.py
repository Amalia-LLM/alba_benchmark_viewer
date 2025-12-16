import sqlite3
from pathlib import Path
root = Path(__file__).resolve().parents[1]
DB = root / 'pt_pt_conversation_evaluations.db'
con = sqlite3.connect(DB)
cur = con.cursor()
print('Distinct conversation_id (first 50):')
for r in cur.execute("SELECT DISTINCT conversation_id FROM evaluations ORDER BY conversation_id LIMIT 50"):
    print(' ', r[0])
print('\nSample rows for one model (allenai_olmo-2-1124-7b-instruct):')
for r in cur.execute("SELECT id, model_name, conversation_id, turn_number, context, response FROM evaluations WHERE model_name=? LIMIT 10",('allenai_olmo-2-1124-7b-instruct',)):
    print(r)
con.close()