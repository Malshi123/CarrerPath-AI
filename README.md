# CareerPath AI

AI-Powered Career Path Recommendation & Skills-Gap Analysis Platform developed for the **Institute of Technology, University of Moratuwa**.

## Overview

**CareerPath AI** helps students discover suitable career paths based on their existing skills, aptitude quiz performance, and personal interests (`coding`, `maths`, and `design`). The platform highlights skill gaps, recommends learning courses, displays Sri Lankan job market demand insights, and allows students to book one-on-one mentor consultation sessions.

## Key Features

* **Role-Based Authentication & Accounts**: Register and log in as a **Student**, **Industry Mentor**, or **Admin**, with hashed passwords (`werkzeug.security`).
* **Aptitude Quiz (`/quiz`)**: Category-based quiz (`coding`, `maths`, `design`) that calculates percentage scores per category.
* **Skill & Interest Assessment (`/assessment`)**: Combine existing skills with interest ratings (`1–5`) and quiz scores to generate weighted career matches (`50% skills + 30% quiz + 20% interest` when a quiz is completed, or `70% skills + 30% interest` otherwise).
* **Career Match & Skills-Gap Roadmap (`/results` & `/student`)**: View top career recommendations, missing required skills, step-by-step learning courses, and Sri Lanka job market demand bars.
* **Mentor Consultation (`/mentors` & `/mentor`)**: Book one-on-one guidance sessions with industry mentors or career counselors and manage booked sessions.
* **Admin Panel (`/admin` & `/admin/careers`)**: Add or delete quiz questions, careers, and required skills with linked courses.

## Tech Stack

* **Backend**: Python, Flask, Werkzeug
* **Database**: MySQL (`mysql-connector-python`)
* **Frontend**: HTML5, CSS3, Jinja2 Templates

## Project Structure

```text
CareerPath-AI/
├── app.py
├── README.md
├── .gitignore
├── static/
│   └── hero-bg.jpg
└── templates/
    ├── base.html
    ├── home.html
    ├── login.html
    ├── register.html
    ├── student.html
    ├── assessment.html
    ├── quiz.html
    ├── results.html
    ├── mentors.html
    ├── mentor.html
    ├── admin.html
    └── admin_careers.html