from flask import Flask, render_template, request
import sqlite3
import os

app = Flask(__name__)

def get_db():
    db_name = request.args.get('db', 'new_results.db')
    if not os.path.exists(db_name):
        db_name = 'new_results.db'
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    
    # Get filter options
    models = cursor.execute('SELECT DISTINCT model_name FROM results ORDER BY model_name').fetchall()
    categories = cursor.execute('SELECT DISTINCT category FROM results ORDER BY category').fetchall()
    
    # Get filter parameters
    selected_db = request.args.get('db', 'new_results.db')
    selected_model = request.args.get('model', '')
    selected_category = request.args.get('category', '')
    min_score = request.args.get('min_score', '')
    max_score = request.args.get('max_score', '')
    page = int(request.args.get('page', 1))
    
    # Get available databases
    dbs = [f for f in os.listdir('.') if f.endswith('.db')]
    
    # Build query
    query = 'SELECT * FROM results WHERE 1=1'
    params = []
    
    if selected_model:
        query += ' AND model_name = ?'
        params.append(selected_model)
    if selected_category:
        query += ' AND category = ?'
        params.append(selected_category)
    if min_score:
        query += ' AND score >= ?'
        params.append(float(min_score))
    if max_score:
        query += ' AND score <= ?'
        params.append(float(max_score))
    
    # Get total count
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    total_count = cursor.execute(count_query, params).fetchone()[0]
    
    # Pagination
    per_page = 50
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page
    
    query += f' ORDER BY id DESC LIMIT {per_page} OFFSET {offset}'
    
    results = cursor.execute(query, params).fetchall()
    conn.close()
    
    return render_template('index.html', 
                         results=results, 
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages,
                         models=models, 
                         categories=categories,
                         dbs=dbs,
                         selected_db=selected_db,
                         selected_model=selected_model,
                         selected_category=selected_category,
                         min_score=min_score,
                         max_score=max_score)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
