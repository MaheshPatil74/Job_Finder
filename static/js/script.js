document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-form');
    const searchBtn = document.getElementById('search-btn');
    const resultsContainer = document.getElementById('results-container');
    const jobsList = document.getElementById('jobs-list');
    const loadingSpinner = document.getElementById('loading');
    
    // Tabs logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(`${btn.dataset.tab}-tab`).classList.add('active');
        });
    });

    let currentCharts = {};

    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const skills = document.getElementById('skills').value;
        const experience = document.getElementById('experience').value;
        const salary = document.getElementById('salary').value;
        const location = document.getElementById('location').value;
        const remote_only = document.getElementById('remote_only').checked;

        // Show loading
        resultsContainer.style.display = 'block';
        jobsList.innerHTML = '';
        loadingSpinner.style.display = 'block';
        searchBtn.disabled = true;
        searchBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Searching...';

        try {
            const response = await fetch('/api/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    skills,
                    experience,
                    salary,
                    location,
                    remote_only
                })
            });

            const data = await response.json();
            
            loadingSpinner.style.display = 'none';
            searchBtn.disabled = false;
            searchBtn.innerHTML = '<span>Find Dream Jobs</span> <i class="fa-solid fa-arrow-right"></i>';

            if (data.error) {
                jobsList.innerHTML = `<div class="job-card"><p style="color: #ef4444;">Error: ${data.error}</p></div>`;
                return;
            }

            renderJobs(data.recommendations);
            renderCharts(data.recommendations);
            
            // Switch to jobs tab
            document.querySelector('[data-tab="jobs"]').click();

        } catch (err) {
            loadingSpinner.style.display = 'none';
            searchBtn.disabled = false;
            searchBtn.innerHTML = '<span>Find Dream Jobs</span> <i class="fa-solid fa-arrow-right"></i>';
            jobsList.innerHTML = `<div class="job-card"><p style="color: #ef4444;">Connection error. Make sure the server is running.</p></div>`;
        }
    });

    function renderJobs(jobs) {
        if (!jobs || jobs.length === 0) {
            jobsList.innerHTML = `<div class="job-card" style="text-align: center; padding: 3rem;">
                <i class="fa-solid fa-folder-open" style="font-size: 3rem; color: #475569; margin-bottom: 1rem;"></i>
                <h3>No exact matches found</h3>
                <p style="color: #94a3b8;">Try adjusting your filters or adding more skills.</p>
            </div>`;
            return;
        }

        jobsList.innerHTML = jobs.map((job, index) => {
            const salaryText = (job.salary_min || job.salary_max) 
                ? `${job.salary_min} - ${job.salary_max} ${job.currency || 'LPA'}`
                : 'Not specified';
            
            const matchPercentage = Math.round(job.score * 100);
            
            // Limit skills to top 6 to prevent overflow
            const skillsHtml = (job.skills_required || [])
                .slice(0, 6)
                .map(skill => `<span class="skill-tag">${skill}</span>`)
                .join('');

            return `
                <div class="job-card" style="animation-delay: ${index * 0.1}s">
                    <div class="job-header">
                        <div>
                            <h3 class="job-title">${job.title}</h3>
                            <div class="job-company">
                                <i class="fa-solid fa-building"></i> ${job.company}
                            </div>
                        </div>
                        <div class="job-score">
                            ${matchPercentage}% Match
                        </div>
                    </div>
                    
                    <div class="job-details">
                        <div class="detail-item">
                            <i class="fa-solid fa-location-dot"></i> ${job.location || 'N/A'}
                        </div>
                        <div class="detail-item">
                            <i class="fa-solid fa-indian-rupee-sign"></i> ${salaryText}
                        </div>
                        <div class="detail-item">
                            <i class="fa-solid fa-laptop-house"></i> ${job.remote_option}
                        </div>
                    </div>
                    
                    <div class="skills-tags">
                        ${skillsHtml}
                    </div>
                </div>
            `;
        }).join('');
    }

    function renderCharts(jobs) {
        if (!jobs || jobs.length === 0) return;

        // Destroy previous charts
        if (currentCharts.location) currentCharts.location.destroy();
        if (currentCharts.salary) currentCharts.salary.destroy();

        // Chart defaults for light theme
        Chart.defaults.color = '#475569';
        Chart.defaults.borderColor = '#e2e8f0';

        // 1. Location/Remote Distribution Chart
        const locations = {};
        jobs.forEach(job => {
            let locType = job.remote_option.toLowerCase();
            if (locType.includes('remote')) locType = 'Remote';
            else if (locType.includes('hybrid')) locType = 'Hybrid';
            else locType = job.location || 'On-site';
            
            locations[locType] = (locations[locType] || 0) + 1;
        });

        const locCtx = document.getElementById('locationChart').getContext('2d');
        currentCharts.location = new Chart(locCtx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(locations),
                datasets: [{
                    data: Object.values(locations),
                    backgroundColor: ['#2563eb', '#0ea5e9', '#6366f1', '#8b5cf6', '#10b981'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' },
                    title: { display: true, text: 'Job Distribution', color: '#1e293b', font: { size: 16 } }
                }
            }
        });

        // 2. Companies Chart
        const companies = {};
        jobs.forEach(job => {
            if (job.company && job.company !== 'N/A') {
                companies[job.company] = (companies[job.company] || 0) + 1;
            }
        });
        
        // Sort and get top 5
        const sortedCompanies = Object.entries(companies)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);

        const compCtx = document.getElementById('salaryChart').getContext('2d');
        currentCharts.salary = new Chart(compCtx, {
            type: 'bar',
            data: {
                labels: sortedCompanies.map(c => c[0]),
                datasets: [{
                    label: 'Number of Jobs',
                    data: sortedCompanies.map(c => c[1]),
                    backgroundColor: '#2563eb',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } }
                },
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: 'Top Companies Hiring', color: '#1e293b', font: { size: 16 } }
                }
            }
        });
    }
});
