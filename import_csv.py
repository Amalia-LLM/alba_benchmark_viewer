import sqlite3
import csv

conn = sqlite3.connect('new_results.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT,
    doc_id INTEGER,
    doc_internal_id INTEGER,
    category TEXT,
    prompt TEXT,
    response TEXT,
    score REAL,
    explanation TEXT
)''')

with open('test-log.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute('''INSERT INTO results 
            (doc_internal_id, model_name, category, prompt, response, score, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (int(row['prompt_id'].replace("p", "")), row['model_name'], row['category'], row['prompt'], 
             row['model_response'], float(row['score']), row['explanation']))

conn.commit()
conn.close()
print("Importação concluída!")
