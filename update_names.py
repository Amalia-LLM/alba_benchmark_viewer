import sqlite3

RENAMES = {
    "47-32k-9B-carminho-with_euroblocks_safety_hermes_customst_checkpoint-2875": "AMALIA-9B 32k v49",
    "47-4k-9B-carminho-with_euroblocks_safety_hermes_customst_checkpoint-13590": "AMALIA-9B 4k v49",
    "47-32k-llama_checkpoint-700": "AMALIA-LLaMA-3.1-8B-32k",
    "49-32k-llama_instruct_checkpoint-1767": "AMALIA-LLaMA-3.1-8B-Instruct-32k",
    "47-32k-qwen3_8B_checkpoint-1482": "AMALIA-Qwen3-8B-32k",
    "49-32k-eurollm-9B_checkpoint-1928": "EuroLLM-AMALIA-9B-32k v49",
    "49-32k-gemma3-12B_checkpoint-1368": "AMALIA-Gemma3-12B-32k",
    "47-safety-dpo-mix_safety_sft_200k_checkpoint-6738_merged": "49 DPO",
    "50-carminho-big_checkpoint-3480": "AMALIA-9B-32k-big v50",
    "50-dpo-mix_safety_sft_200k_if_checkpoint-6892_merged": "AMALIA-9B-32k-big-DPO-small v50",
    "50-carminho-big-old_checkpoint-18501": "AMALIA-9B-4k-big v50",
    "50-big-4k-dpo-big_checkpoint-6155_merged": "AMALIA-9B-4k-big-DPO-big v50",
    "49-4k-eurollm-9B_checkpoint-12231": "EuroLLM AMALIA-9B 4k v49",
}

conn = sqlite3.connect('model_results.db')
cursor = conn.cursor()

models = cursor.execute('SELECT DISTINCT model_name FROM results').fetchall()
print("Current models:")
for m in models:
    print(f"  {m[0]}")

print("\nUpdating...")
for old_suffix, new_name in RENAMES.items():
    cursor.execute("UPDATE results SET model_name = ? WHERE model_name LIKE ?", (new_name, f"%{old_suffix}"))
    if cursor.rowcount > 0:
        print(f"Updated {cursor.rowcount} rows: ...{old_suffix} -> {new_name}")

conn.commit()
conn.close()
print("\nDone!")
