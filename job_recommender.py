import os
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import matplotlib.pyplot as plt


def load_data(filepath=None):
    """Load the dataset from disk using pandas."""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), 'advanced_it_jobs_dataset.csv.xls')

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset not found: {filepath}")

    try:
        if filepath.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)
    except Exception:
        # Try the alternate read method if the first attempt fails
        try:
            df = pd.read_csv(filepath)
        except Exception:
            df = pd.read_excel(filepath)

    return df


def normalize_text(text):
    """Normalize text for consistent matching: lowercase, trim, replace hyphens with spaces."""
    if not isinstance(text, str):
        return str(text).strip().lower().replace('-', ' ')
    return text.strip().lower().replace('-', ' ')


def normalize_list_column(value):
    """Convert a raw column value into a cleaned list of lowercase tokens."""
    if pd.isna(value):
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).split(',')
    cleaned = [normalize_text(item) for item in items if str(item).strip()]
    return cleaned


def preprocess_data(df):
    """Prepare the dataset for filtering, matching, and scoring."""
    df = df.copy()

    # Normalize boolean / status fields
    df['is_active'] = df['is_active'].astype(str).str.strip().str.lower().isin(['true', '1', 'yes', 'y', 'active'])

    # Prepare list fields for skill matching
    list_columns = ['skills_required', 'programming_languages', 'tools_technologies']
    for column in list_columns:
        if column not in df.columns:
            df[column] = [[] for _ in range(len(df))]
        else:
            df[column] = df[column].apply(normalize_list_column)

    # Add normalized text support for search and filtering
    df['location_norm'] = df.get('location', '').astype(str).str.strip().str.lower()
    df['remote_option_norm'] = df.get('remote_option', '').astype(str).str.strip().str.lower()

    # Convert numeric columns safely
    numeric_columns = [
        'experience_required',
        'salary_min',
        'salary_max',
        'company_rating',
        'popularity_score',
        'seniority_score',
        'job_freshness_days',
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0)
        else:
            df[column] = 0

    # Ensure salary_min and salary_max are valid pairs
    df['salary_min'] = df['salary_min'].clip(lower=0)
    df['salary_max'] = df['salary_max'].clip(lower=df['salary_min'])

    return df


def compute_skill_match(job_row, user_skills):
    """Compute a normalized skill match score between a job and the user's skills."""
    job_skills_raw = job_row['skills_required'] + job_row['programming_languages'] + job_row['tools_technologies']
    job_skills = set(normalize_text(skill) for skill in job_skills_raw if skill)
    user_skills_norm = set(normalize_text(skill) for skill in user_skills)

    if not user_skills_norm or not job_skills:
        return 0.0

    # Exact match
    matched = len(user_skills_norm.intersection(job_skills))

    # Partial match (important!)
    partial_matches = 0
    for us in user_skills_norm:
        for js in job_skills:
            if us in js or js in us:
                partial_matches += 1
                break

    score = (matched + 0.5 * partial_matches) / max(len(user_skills_norm), 1)
    return min(score, 1.0)


def compute_title_match(job_row, user_skills):
    """Compute a normalized title match score between a job title and user input."""
    job_title = normalize_text(job_row.get('job_title', ''))
    user_skills_norm = set(normalize_text(skill) for skill in user_skills)

    if not user_skills_norm or not job_title:
        return 0.0

    # Exact word match in title
    matched = 0
    for skill in user_skills_norm:
        if skill in job_title:
            matched += 1

    # Partial match (e.g., "dev" in "developer")
    partial_matches = 0
    for skill in user_skills_norm:
        for word in job_title.split():
            if skill in word or word in skill:
                partial_matches += 1
                break

    score = (matched + 0.5 * partial_matches) / max(len(user_skills_norm), 1)
    return min(score, 1.0)


def filter_jobs(df, experience, expected_salary, location='', remote_only=False):
    """Filter jobs by activity and experience only (light filtering)."""
    filtered = df[df['is_active']].copy()
    print(f"[DEBUG] active jobs: {len(filtered)}")

    filtered = filtered[filtered['experience_required'] <= experience]
    print(f"[DEBUG] after experience filter: {len(filtered)}")

    # Compute match indicators for scoring
    if location:
        clean_location = location.strip().lower()
        filtered['location_match'] = filtered['location_norm'].str.contains(clean_location, na=False).astype(int)
    else:
        filtered['location_match'] = 0

    filtered['remote_match'] = filtered['remote_option_norm'].str.contains('remote|hybrid|work from home|any', na=False).astype(int)

    return filtered


def calculate_score(df):
    """Normalize features and compute a combined final score."""
    df = df.copy()

    def min_max(series):
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return np.zeros(len(series), dtype=float)
        return (series - min_val) / (max_val - min_val)

    df['company_rating_norm'] = min_max(df['company_rating'])
    df['popularity_norm'] = min_max(df['popularity_score'])
    df['seniority_norm'] = min_max(df['seniority_score'])
    df['freshness_norm'] = min_max(df['job_freshness_days'])
    df['salary_score_norm'] = min_max(df.get('salary_score', 0.0))
    df['location_score_norm'] = min_max(df.get('location_score', 0.0))
    df['remote_score_norm'] = min_max(df.get('remote_score', 0.0))

    # More recent jobs should score higher
    df['freshness_score'] = 1.0 - df['freshness_norm']

    # Normalize title_match_score (already in 0-1 range)
    df['title_match_score_norm'] = df.get('title_match_score', 0.0)

    weights = {
        'skill': 0.35,
        'title': 0.30,
        'location': 0.12,
        'remote': 0.08,
        'salary': 0.08,
        'company': 0.04,
        'popularity': 0.02,
        'seniority': 0.01,
    }

    df['final_score'] = (
        df['skill_match_score'] * weights['skill']
        + df['title_match_score_norm'] * weights['title']
        + df['location_score_norm'] * weights['location']
        + df['remote_score_norm'] * weights['remote']
        + df['salary_score_norm'] * weights['salary']
        + df['company_rating_norm'] * weights['company']
        + df['popularity_norm'] * weights['popularity']
        + df['seniority_norm'] * weights['seniority']
    )

    # Boost jobs with title match
    df.loc[df['title_match_score_norm'] > 0, 'final_score'] *= 1.15

    return df


def recommend_jobs(df, skills_text, experience, expected_salary, location='', remote_only=False, top_n=10):
    """Return the top recommended jobs for the current user preferences."""
    # Normalize user skills the same way as dataset skills (lowercase, strip, replace hyphens)
    user_skills = [normalize_text(skill) for skill in skills_text.split(',') if skill.strip()]
    user_skills_set = set(user_skills)
    print(f"[DEBUG] recommend_jobs called with: experience={experience}, salary={expected_salary}, location='{location}', remote_only={remote_only}")
    print(f"[DEBUG] normalized user_skills: {user_skills}")

    filtered = filter_jobs(df, experience, expected_salary, location, remote_only)
    if filtered.empty:
        print('[DEBUG] filtered result empty after all filters')
        return pd.DataFrame()

    # Compute skill matching with normalized user skills
    filtered['skill_match_score'] = filtered.apply(lambda row: compute_skill_match(row, user_skills_set), axis=1)
    top_scores = filtered['skill_match_score'].nlargest(5).tolist()
    print(f"[DEBUG] top skill_match_scores: {top_scores}")
    print(f"[DEBUG] total jobs after skill matching: {len(filtered)}")

    # Compute title matching with normalized user input
    filtered['title_match_score'] = filtered.apply(lambda row: compute_title_match(row, user_skills_set), axis=1)
    top_title_scores = filtered['title_match_score'].nlargest(5).tolist()
    print(f"[DEBUG] top title_match_scores: {top_title_scores}")

    # Compute additional scores for hybrid approach
    filtered['location_score'] = filtered['location_match'] if location else 0.0
    filtered['remote_score'] = filtered['remote_match'] if remote_only else 0.0

    filtered['salary_score'] = 0.0
    if expected_salary > 0:
        min_salary = filtered['salary_min'].fillna(expected_salary)
        max_salary = filtered['salary_max'].replace(0, expected_salary).fillna(expected_salary)
        salary_gap = np.minimum(np.abs(min_salary - expected_salary), np.abs(max_salary - expected_salary))
        filtered['salary_score'] = 1.0 - np.minimum(salary_gap / max(expected_salary, 1), 1.0)

    scored = calculate_score(filtered)
    scored = scored.sort_values(by='final_score', ascending=False)

    return scored.head(top_n)


def format_job_row(job_row):
    """Build a readable string for a job recommendation entry."""
    salary_min = int(job_row['salary_min']) if pd.notna(job_row['salary_min']) else 0
    salary_max = int(job_row['salary_max']) if pd.notna(job_row['salary_max']) else 0
    salary_text = f"{salary_min:,} - {salary_max:,}" if salary_min or salary_max else 'N/A'

    return (
        f"Title: {job_row.get('job_title', 'N/A')}\n"
        f"Company: {job_row.get('company_name', 'N/A')}\n"
        f"Location: {job_row.get('location', 'N/A')}\n"
        f"Salary: {salary_text} {job_row.get('currency', '')}\n"
        f"Score: {job_row['final_score']:.3f}\n"
        "-------------------------------\n"
    )


# Global variable to store latest recommendations
latest_recommendations = None


def show_site_distribution():
    """Pie chart: Job distribution by location and remote type."""
    global latest_recommendations
    
    if latest_recommendations is None or latest_recommendations.empty:
        messagebox.showwarning('No Results', 'Please search for jobs first to see insights.')
        return
    
    plt.close('all')
    
    results = latest_recommendations.copy()
    
    # Combine location and remote_option for labels
    labels_list = []
    for idx, row in results.iterrows():
        location = str(row.get('location', 'Unknown')).strip()
        remote = str(row.get('remote_option', 'On-site')).strip().lower()
        
        if 'remote' in remote:
            labels_list.append('Remote')
        elif 'hybrid' in remote:
            labels_list.append('Hybrid')
        else:
            labels_list.append(location)
    
    # Count occurrences and get top 6-8
    from collections import Counter
    label_counts = Counter(labels_list)
    top_labels = label_counts.most_common(8)
    
    labels = [label[0] for label in top_labels]
    counts = [label[1] for label in top_labels]
    
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.set_title('Job Distribution by Location & Remote Type', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.show()


def show_top_companies():
    """Bar chart: Top 10 hiring companies."""
    global latest_recommendations
    
    if latest_recommendations is None or latest_recommendations.empty:
        messagebox.showwarning('No Results', 'Please search for jobs first to see insights.')
        return
    
    plt.close('all')
    
    results = latest_recommendations.copy()
    
    # Count jobs per company and get top 10
    company_counts = results['company_name'].value_counts().head(10)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(company_counts)), company_counts.values, color='steelblue')
    ax.set_xticks(range(len(company_counts)))
    ax.set_xticklabels(company_counts.index, rotation=45, ha='right')
    ax.set_xlabel('Company Name', fontsize=12)
    ax.set_ylabel('Number of Jobs', fontsize=12)
    ax.set_title('Top Hiring Companies', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.show()


def show_top_skills():
    """Bar chart: Top 10 most common skills."""
    global latest_recommendations
    
    if latest_recommendations is None or latest_recommendations.empty:
        messagebox.showwarning('No Results', 'Please search for jobs first to see insights.')
        return
    
    plt.close('all')
    
    results = latest_recommendations.copy()
    
    # Flatten all skills from three columns
    all_skills = []
    for idx, row in results.iterrows():
        skills = row.get('skills_required', [])
        languages = row.get('programming_languages', [])
        tools = row.get('tools_technologies', [])
        
        all_skills.extend(skills)
        all_skills.extend(languages)
        all_skills.extend(tools)
    
    # Count frequency and get top 10
    from collections import Counter
    skill_counts = Counter(all_skills)
    top_skills = skill_counts.most_common(10)
    
    skills_names = [skill[0] for skill in top_skills]
    skills_freq = [skill[1] for skill in top_skills]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(skills_names)), skills_freq, color='coral')
    ax.set_xticks(range(len(skills_names)))
    ax.set_xticklabels(skills_names, rotation=45, ha='right')
    ax.set_xlabel('Skill Name', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Top Skills in Recommended Jobs', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.show()


def run_app():
    """Create and run the Tkinter UI for the recommender."""
    root = tk.Tk()
    root.title('Job Recommendation System')
    root.geometry('760x600')
    root.resizable(False, False)

    try:
        data = preprocess_data(load_data())
    except Exception as exc:
        messagebox.showerror('Data Load Error', str(exc))
        root.destroy()
        return

    frame = ttk.Frame(root, padding='16')
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text='Skills (comma-separated):').grid(row=0, column=0, sticky=tk.W, pady=(0, 6))
    skills_entry = ttk.Entry(frame, width=70)
    skills_entry.grid(row=0, column=1, pady=(0, 6), sticky=tk.W)

    ttk.Label(frame, text='Experience (years):').grid(row=1, column=0, sticky=tk.W, pady=6)
    experience_entry = ttk.Entry(frame, width=20)
    experience_entry.grid(row=1, column=1, sticky=tk.W, pady=6)

    ttk.Label(frame, text='Expected salary (Lpa):').grid(row=2, column=0, sticky=tk.W, pady=6)
    salary_entry = ttk.Entry(frame, width=20)
    salary_entry.grid(row=2, column=1, sticky=tk.W, pady=6)

    ttk.Label(frame, text='Location (optional):').grid(row=3, column=0, sticky=tk.W, pady=6)
    location_entry = ttk.Entry(frame, width=40)
    location_entry.grid(row=3, column=1, sticky=tk.W, pady=6)

    remote_var = tk.BooleanVar(value=False)
    remote_checkbox = ttk.Checkbutton(frame, text='Allow remote or hybrid jobs', variable=remote_var)
    remote_checkbox.grid(row=4, column=1, sticky=tk.W, pady=6)

    results_text = tk.Text(frame, width=90, height=22, wrap='word', padx=10, pady=10)
    results_text.grid(row=6, column=0, columnspan=2, pady=(12, 0))
    results_text.configure(state='disabled')

    def search_jobs():
        skills = skills_entry.get().strip()
        experience_text = experience_entry.get().strip()
        salary_text = salary_entry.get().strip()
        location_text = location_entry.get().strip()
        remote_pref = remote_var.get()

        print(f"\n[DEBUG] ============ SEARCH TRIGGERED ============")
        print(f"[DEBUG] UI inputs - skills: '{skills}', exp: '{experience_text}', sal: '{salary_text}', loc: '{location_text}', remote: {remote_pref}")

        if not skills:
            messagebox.showwarning('Input Required', 'Please enter at least one skill.')
            return

        try:
            experience_val = float(experience_text) if experience_text else 0.0
        except ValueError:
            messagebox.showwarning('Input Error', 'Experience must be a number.')
            return

        try:
            expected_salary_val = float(salary_text) if salary_text else 0.0
        except ValueError:
            messagebox.showwarning('Input Error', 'Salary must be a number.')
            return

        results_text.configure(state='normal')
        results_text.delete('1.0', tk.END)
        print(f"[DEBUG] results_text cleared")

        recommendations = recommend_jobs(
            data,
            skills_text=skills,
            experience=experience_val,
            expected_salary=expected_salary_val,
            location=location_text,
            remote_only=remote_pref,
            top_n=10,
        )

        # Store recommendations for visualization
        global latest_recommendations
        latest_recommendations = recommendations

        print(f"[DEBUG] recommend_jobs returned {len(recommendations)} results")

        if recommendations.empty:
            results_text.insert(tk.END, 'No matching jobs were found with the current filters.\n')
            print(f"[DEBUG] displayed no results message")
        else:
            for idx, (_, row) in enumerate(recommendations.iterrows()):
                results_text.insert(tk.END, format_job_row(row))
                if idx == 0:
                    print(f"[DEBUG] top result: {row.get('job_title', 'N/A')} | score: {row['final_score']:.3f}")

        results_text.configure(state='disabled')
        print(f"[DEBUG] ============ SEARCH COMPLETE ============\n")

    find_button = ttk.Button(frame, text='Find Jobs', command=search_jobs)
    find_button.grid(row=5, column=1, sticky=tk.W, pady=10)

    # Create a button frame for visualizations
    button_frame = ttk.Frame(frame)
    button_frame.grid(row=5, column=1, sticky=tk.E, pady=10, padx=(0, 10))
    
    site_dist_button = ttk.Button(button_frame, text='Site Distribution', command=show_site_distribution)
    site_dist_button.pack(side=tk.LEFT, padx=2)
    
    companies_button = ttk.Button(button_frame, text='Top Companies', command=show_top_companies)
    companies_button.pack(side=tk.LEFT, padx=2)
    
    skills_button = ttk.Button(button_frame, text='Top Skills', command=show_top_skills)
    skills_button.pack(side=tk.LEFT, padx=2)

    root.mainloop()


if __name__ == '__main__':
    run_app()
