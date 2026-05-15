from flask import Flask, request, jsonify, render_template
import pandas as pd
from job_recommender import load_data, preprocess_data, recommend_jobs
import os

app = Flask(__name__)

# Load data at startup
try:
    print("Loading dataset...")
    raw_data = load_data()
    df = preprocess_data(raw_data)
    print(f"Dataset loaded successfully with {len(df)} records.")
except Exception as e:
    print(f"Error loading data: {e}")
    df = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/recommend', methods=['POST'])
def get_recommendations():
    if df is None:
        return jsonify({"error": "Data could not be loaded on the server."}), 500
        
    data = request.json
    skills = data.get('skills', '')
    experience = float(data.get('experience', 0))
    salary = float(data.get('salary', 0))
    location = data.get('location', '')
    remote_only = data.get('remote_only', False)
    
    if not skills:
        return jsonify({"error": "Skills are required."}), 400
        
    recommendations = recommend_jobs(
        df,
        skills_text=skills,
        experience=experience,
        expected_salary=salary,
        location=location,
        remote_only=remote_only,
        top_n=10
    )
    
    # Format the output for JSON response
    results = []
    for _, row in recommendations.iterrows():
        salary_min = int(row['salary_min']) if pd.notna(row['salary_min']) else 0
        salary_max = int(row['salary_max']) if pd.notna(row['salary_max']) else 0
        
        # safely handle list concatenation
        skills_list = []
        if isinstance(row.get('skills_required'), list):
            skills_list.extend(row['skills_required'])
        if isinstance(row.get('programming_languages'), list):
            skills_list.extend(row['programming_languages'])
        if isinstance(row.get('tools_technologies'), list):
            skills_list.extend(row['tools_technologies'])
            
        results.append({
            "title": row.get('job_title', 'N/A'),
            "company": row.get('company_name', 'N/A'),
            "location": row.get('location', 'N/A'),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "currency": row.get('currency', ''),
            "score": float(row['final_score']),
            "remote_option": row.get('remote_option', 'On-site'),
            "skills_required": skills_list
        })
        
    return jsonify({"recommendations": results})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
