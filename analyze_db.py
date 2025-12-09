import sqlite3

conn = sqlite3.connect('evaluations.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]
    print(f"\n{'='*60}")
    print(f"Table: {table_name}")
    print('='*60)
    
    # Get columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print("\nColumns:")
    for col in columns:
        print(f"  {col[1]:20} {col[2]:10} {'NOT NULL' if col[3] else ''}")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"\nTotal rows: {count}")
    
    # Sample data
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
    rows = cursor.fetchall()
    if rows:
        print("\nSample data (first 3 rows):")
        for i, row in enumerate(rows, 1):
            print(f"\n  Row {i}:")
            for j, col in enumerate(columns):
                value = str(row[j])[:100]
                print(f"    {col[1]}: {value}")

conn.close()
