# Job Recommendation System (Web App Enhanced)

A modern, web-based Job Recommendation System that uses `pandas` and `numpy` for intelligent matching and `Flask` with an interactive, glassmorphic UI for a stunning user experience.

## Features

- **Smart Matching**: Evaluates skills, experience, expected salary, and location.
- **Modern UI**: A premium dark-mode interface with glassmorphism and subtle animations.
- **Interactive Analytics**: Visualizes job distributions and top hiring companies via `Chart.js`.
- **Remote Filters**: Option to specifically search for remote or hybrid positions.

## Files

- `app.py` - Flask web server and API.
- `job_recommender.py` - Core recommendation engine with data loading, filtering, and scoring.
- `advanced_it_jobs_dataset.csv.xls` - Dataset file.
- `templates/` & `static/` - Frontend HTML, CSS, and JS files.

## Requirements

- Python 3.9+
- pandas
- numpy
- flask

## Install dependencies

```powershell
python -m pip install pandas numpy flask
```

## Run the Web App

```powershell
python app.py
```
After running, open your web browser to `http://127.0.0.1:5000`

## Legacy Tkinter App
If you still want to run the old desktop UI:
```powershell
python job_recommender.py
```
