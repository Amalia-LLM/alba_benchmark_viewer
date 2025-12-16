from flask import Flask, render_template, request
import sqlite3
import os

app = Flask(__name__)

def get_readable_model_name(model_name):
    """Convert long model names to readable short names"""
    name_map = {
        'allenai_olmo-2-1124-7b-instruct': 'Olmo-2 7B',
        'bsc-lt_salamandra-7b-instruct': 'Salamandra 7B',
        'gpfs_scratch_epor32_amsimplicio_rlvr_outputs_50-new4k-dpo-pt200k-safety_checkpoint-3089-merged': 'Amália PT 50-new4k',
        'gpfs_scratch_epor32_hub_gemma-3-12b-it': 'Gemma-3 12B',
        'gpfs_scratch_epor32_hub_gemma-3-12b-it_': 'Gemma-3 12B (v2)',
        'gpfs_scratch_epor32_hub_qwen3-8b': 'Qwen3 8B',
        'meta-llama_llama-3.1-8b-instruct': 'Llama-3.1 8B',
        'mistralai_ministral-8b-instruct-2410': 'Ministral 8B',
        'mistralai_mistral-7b-instruct-v0.3': 'Mistral 7B v0.3',
        'portulan_gervasio-8b-portuguese-ptpt-decoder': 'Gervásio 8B PT-PT',
        'qwen_qwen2.5-7b-instruct': 'Qwen2.5 7B',
        'utter-project_eurollm-9b-instruct': 'EuroLLM 9B'
    }
    return name_map.get(model_name, model_name)

def get_db():
    db_name = request.args.get('db', 'new_results.db')
    if not os.path.exists(db_name):
        db_name = 'new_results.db'
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    selected_db = request.args.get('db', 'new_results.db')
    
    # Route to evaluations view if evaluations.db is selected
    if selected_db == 'evaluations.db':
        return evaluations()
    
    # Route to conversations view if pt_pt_conversation_evaluations.db is selected
    if selected_db == 'pt_pt_conversation_evaluations.db':
        return conversations()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get filter options
    models = cursor.execute('SELECT DISTINCT model_name FROM results ORDER BY model_name').fetchall()
    categories = cursor.execute('SELECT DISTINCT category FROM results ORDER BY category').fetchall()
    
    # Get filter parameters
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
    
    # Get total count and stats
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    total_count = cursor.execute(count_query, params).fetchone()[0]
    
    stats_query = query.replace('SELECT *', 'SELECT AVG(score), MIN(score), MAX(score)')
    stats = cursor.execute(stats_query, params).fetchone()
    avg_score = round(stats[0], 2) if stats[0] else 0
    min_score_val = stats[1] if stats[1] else 0
    max_score_val = stats[2] if stats[2] else 0
    
    # Get median
    median_query = query.replace('SELECT *', 'SELECT score') + ' ORDER BY score'
    all_scores = [row[0] for row in cursor.execute(median_query, params).fetchall()]
    median_score = all_scores[len(all_scores)//2] if all_scores else 0
    
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
                         max_score=max_score,
                         avg_score=avg_score,
                         median_score=median_score,
                         min_score_val=min_score_val,
                         max_score_val=max_score_val)

@app.route('/evaluations')
def evaluations():
    conn = sqlite3.connect('evaluations.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get filter options
    models = cursor.execute('SELECT DISTINCT model_name FROM evaluations ORDER BY model_name').fetchall()
    groups = cursor.execute('SELECT DISTINCT group_name FROM evaluations ORDER BY group_name').fetchall()
    
    # Get filter parameters
    selected_db = 'evaluations.db'
    selected_model = request.args.get('model', '')
    selected_group = request.args.get('group', '')
    min_score = request.args.get('min_score', '')
    max_score = request.args.get('max_score', '')
    page = int(request.args.get('page', 1))
    
    dbs = [f for f in os.listdir('.') if f.endswith('.db')]
    
    # Build query
    query = 'SELECT * FROM evaluations WHERE 1=1'
    params = []
    
    if selected_model:
        query += ' AND model_name = ?'
        params.append(selected_model)
    if selected_group:
        query += ' AND group_name = ?'
        params.append(selected_group)
    if min_score:
        query += ' AND score >= ?'
        params.append(float(min_score))
    if max_score:
        query += ' AND score <= ?'
        params.append(float(max_score))
    
    # Get total count and stats
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    total_count = cursor.execute(count_query, params).fetchone()[0]
    
    stats_query = query.replace('SELECT *', 'SELECT AVG(score), MIN(score), MAX(score)')
    stats = cursor.execute(stats_query, params).fetchone()
    avg_score = round(stats[0], 2) if stats[0] else 0
    min_score_val = stats[1] if stats[1] else 0
    max_score_val = stats[2] if stats[2] else 0
    
    # Get median
    median_query = query.replace('SELECT *', 'SELECT score') + ' ORDER BY score'
    all_scores = [row[0] for row in cursor.execute(median_query, params).fetchall()]
    median_score = all_scores[len(all_scores)//2] if all_scores else 0
    
    # Pagination
    per_page = 50
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page
    
    query += f' ORDER BY id DESC LIMIT {per_page} OFFSET {offset}'
    
    results = cursor.execute(query, params).fetchall()
    conn.close()
    
    return render_template('evaluations.html',
                         results=results,
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages,
                         models=models,
                         groups=groups,
                         dbs=dbs,
                         selected_db=selected_db,
                         selected_model=selected_model,
                         selected_group=selected_group,
                         min_score=min_score,
                         max_score=max_score,
                         avg_score=avg_score,
                         median_score=median_score,
                         min_score_val=min_score_val,
                         max_score_val=max_score_val)

@app.route('/conversations')
def conversations():
    conn = sqlite3.connect('pt_pt_conversation_evaluations.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get filter options
    models_raw = cursor.execute('SELECT DISTINCT model_name FROM evaluations ORDER BY model_name').fetchall()
    models = [{'model_name': m[0], 'readable_name': get_readable_model_name(m[0])} for m in models_raw]
    conversations_list = cursor.execute('SELECT DISTINCT conversation_id FROM evaluations ORDER BY conversation_id').fetchall()
    conversations_list = [dict(row) for row in conversations_list]
    for conversation in conversations_list:
        conversation['conversation_id'] = int(conversation['conversation_id'].replace('p', '').replace('t', ' '))
    conversations_list.sort(key=lambda x: x['conversation_id'])
    # Delete duplicates
    seen = set()
    unique_conversations = []
    for conv in conversations_list:
        if conv['conversation_id'] not in seen:
            unique_conversations.append(conv)
            seen.add(conv['conversation_id'])
    conversations_list = unique_conversations
    # Tranform the number in string format
    for conversation in conversations_list:
        conversation['conversation_id'] = f"{conversation['conversation_id']}"


    # Get filter parameters
    selected_db = 'pt_pt_conversation_evaluations.db'
    selected_model = request.args.get('model', '')
    selected_conversation = request.args.get('conversation', '')
    selected_pt_pt = request.args.get('pt_pt_prompt', '')
    min_score = request.args.get('min_score', '')
    max_score = request.args.get('max_score', '')
    page = int(request.args.get('page', 1))
    
    dbs = [f for f in os.listdir('.') if f.endswith('.db')]
    
    # Build query
    query = 'SELECT * FROM evaluations WHERE 1=1'
    params = []
    
    if selected_model:
        query += ' AND model_name = ?'
        params.append(selected_model)
    if selected_conversation:
        query += ' AND conversation_id = ?'
        params.append(f"p{selected_conversation}{"t" if selected_pt_pt else ""}")
    if selected_pt_pt:
        query += ' AND used_pt_pt_prompt = ?'
        params.append(int(selected_pt_pt))
    if min_score:
        query += ' AND score >= ?'
        params.append(float(min_score))
    if max_score:
        query += ' AND score <= ?'
        params.append(float(max_score))
    
    # Get total count and stats
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    total_count = cursor.execute(count_query, params).fetchone()[0]
    
    stats_query = query.replace('SELECT *', 'SELECT AVG(score), MIN(score), MAX(score)')
    stats = cursor.execute(stats_query, params).fetchone()
    avg_score = round(stats[0], 2) if stats[0] else 0
    min_score_val = stats[1] if stats[1] else 0
    max_score_val = stats[2] if stats[2] else 0
    
    # Get median
    median_query = query.replace('SELECT *', 'SELECT score') + ' ORDER BY score'
    all_scores = [row[0] for row in cursor.execute(median_query, params).fetchall()]
    median_score = all_scores[len(all_scores)//2] if all_scores else 0
    
    # Pagination
    per_page = 20
    offset = (page - 1) * per_page
    total_pages = (total_count + per_page - 1) // per_page
    
    query += f' ORDER BY conversation_id, turn_number LIMIT {per_page} OFFSET {offset}'
    
    results = cursor.execute(query, params).fetchall()
    
    # Convert results to dict and add readable names
    results_with_names = []
    for row in results:
        row_dict = dict(row)
        row_dict['readable_model_name'] = get_readable_model_name(row['model_name'])
        row_dict['conversation_id'] = int(row_dict['conversation_id'].replace('p', '').replace('t', ' '))
        results_with_names.append(row_dict)
    results_with_names.sort(key=lambda x: (x['conversation_id'], x['turn_number']))
    
    conn.close()
    return render_template('conversations.html',
                         results=results_with_names,
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages,
                         models=models,
                         conversations_list=conversations_list,
                         dbs=dbs,
                         selected_db=selected_db,
                         selected_model=selected_model,
                         selected_conversation=selected_conversation,
                         selected_pt_pt=selected_pt_pt,
                         min_score=min_score,
                         max_score=max_score,
                         avg_score=avg_score,
                         median_score=median_score,
                         min_score_val=min_score_val,
                         max_score_val=max_score_val)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
