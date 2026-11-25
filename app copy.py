import os
import mysql.connector
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")


def get_db():
    # Opens a new connection to the MySQL database
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",          # XAMPP default is an empty password
        database="career_platform",
    )


def load_career_data():
    # Reads careers, their skills and courses from MySQL
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT C.Name, C.Quiz_Category, S.Name, S.Course "
        "FROM Careers C "
        "JOIN Career_Skills CS ON CS.Career_Id = C.Id "
        "JOIN Skills S ON S.Id = CS.Skill_Id "
        "ORDER BY C.Id, S.Id"
    )

    careers = {}
    courses = {}
    career_category = {}
    for career, category, skill, course in cursor.fetchall():
        careers.setdefault(career, []).append(skill)
        career_category[career] = category.lower()
        courses[skill] = course
    db.close()
    return careers, courses, career_category


def load_questions():
    # Reads the quiz questions from MySQL
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT question, option_a, option_b, option_c, option_d, answer, category "
        "FROM questions ORDER BY id"
    )
    questions = []
    for q, a, b, c, d, answer, category in cursor.fetchall():
        questions.append({
            "question": q,
            "options": [a, b, c, d],
            "answer": answer,
            "category": category.lower(),
        })
    db.close()
    return questions


@app.route("/")
def home():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        # Look for this user in the database
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND role = %s",
            (username, role),
        )
        user = cursor.fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session["username"] = user["username"]
            session["role"] = user["role"]

            # Admins and mentors have their own pages, students go to the dashboard
            if user["role"] == "Admin":
                return redirect("/admin")
            if user["role"] == "Mentor":
                return redirect("/mentor")
            return redirect("/student")

        return render_template("login.html", error="Incorrect username or password!")

    return render_template("login.html")


@app.route("/student", methods=["GET", "POST"])
def student():
    # Redirect to login if the user is not logged in
    if "username" not in session:
        return redirect("/login")

    careers, courses, career_category = load_career_data()

    data = {"username": session["username"]}

    if request.method == "POST":
        # When the Analyze button is clicked
        if "analyze_btn" in request.form:
            my_skills = request.form.getlist("skills")
            quiz_scores = session.get("quiz")

            # Interest ratings from the dropdowns (1, 3 or 5)
            interests = {
                "coding": int(request.form["coding"]),
                "maths": int(request.form["maths"]),
                "design": int(request.form["design"]),
            }

            results = []
            for career, needed in careers.items():
                category = career_category[career]
                have = [s for s in needed if s in my_skills]
                skill_percent = len(have) / len(needed) * 100
                interest_percent = interests[category] / 5 * 100

                if quiz_scores:
                    # The quiz page already saved a percentage per category
                    quiz_percent = quiz_scores.get(category, 0)
                    final = skill_percent * 0.5 + quiz_percent * 0.3 + interest_percent * 0.2
                else:
                    quiz_percent = None
                    final = skill_percent * 0.7 + interest_percent * 0.3

                results.append({
                    "career": career,
                    "skill": round(skill_percent),
                    "quiz": None if quiz_percent is None else round(quiz_percent),
                    "interest": round(interest_percent),
                    "final": round(final),
                })

            results.sort(key=lambda r: r["final"], reverse=True)
            best_career = results[0]["career"]

            # Best career(s) for each factor on its own
            def top_careers(key):
                scored = [r for r in results if r[key] is not None]
                if not scored:
                    return None
                best_value = max(r[key] for r in scored)
                names = [r["career"] for r in scored if r[key] == best_value]
                return {"careers": " / ".join(names), "score": best_value}

            data["by_skills"] = top_careers("skill")
            data["by_quiz"] = top_careers("quiz")
            data["by_interest"] = top_careers("interest")

            # Skills the student is missing for the best career
            gaps = [s for s in careers[best_career] if s not in my_skills]

            data["career"] = best_career
            data["results"] = results
            data["best"] = results[0]
            data["has_quiz"] = quiz_scores is not None
            data["user_skills"] = my_skills
            data["skill_gaps"] = gaps
            data["roadmap"] = {g: courses[g] for g in gaps}

        # When the Book button is clicked (a separate form from Analyze)
        if "book_btn" in request.form:
            mentor_choice = request.form["mentor"]
            date = request.form["date"]
            topic = request.form["topic"]

            # Save the booking permanently
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO bookings (username, mentor, session_date, topic) VALUES (%s, %s, %s, %s)",
                (session["username"], mentor_choice, date, topic),
            )
            db.commit()
            db.close()

            data["booking_msg"] = f"Booked! Session with {mentor_choice} on {date}."

    # Load the job market demand bars from MySQL
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT skill_area, demand FROM market_trends ORDER BY demand DESC")
    data["market"] = cursor.fetchall()
    db.close()

    return render_template("student.html", **data)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm = request.form["confirm"]
        role = request.form["role"]

        if password != confirm:
            return render_template("register.html", error="Passwords do not match.")

        db = get_db()
        cursor = db.cursor()

        # Check if the username is already taken
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            db.close()
            return render_template("register.html", error="That username is already taken.")

        # Save the new user permanently (password is stored as a hash)
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (username, password_hash, role),
        )
        db.commit()
        db.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "username" not in session:
        return redirect("/login")

    questions = load_questions()

    if request.method == "POST":
        correct = {"coding": 0, "maths": 0, "design": 0}
        total = {"coding": 0, "maths": 0, "design": 0}
        for i, q in enumerate(questions):
            total[q["category"]] += 1
            # Compare the chosen answer with the correct one
            if request.form.get(f"q{i}") == q["answer"]:
                correct[q["category"]] += 1

        # Save a percentage (0-100) for each category
        session["quiz"] = {
            c: round(correct[c] / total[c] * 100) if total[c] else 0
            for c in correct
        }
        return redirect("/student")

    return render_template("quiz.html", questions=questions)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    # Only logged-in admins can open this page
    if session.get("role") != "Admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    msg = None

    # When the Add Question form is submitted
    if request.method == "POST" and "add_question" in request.form:
        cursor.execute(
            "INSERT INTO questions (question, option_a, option_b, option_c, option_d, answer, category) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                request.form["question"],
                request.form["option_a"],
                request.form["option_b"],
                request.form["option_c"],
                request.form["option_d"],
                request.form["answer"],
                request.form["category"],
            ),
        )
        db.commit()
        msg = "Question added."

    cursor.execute(
        "SELECT id AS id, question AS question, answer AS answer, category AS category "
        "FROM questions ORDER BY id"
    )
    all_questions = cursor.fetchall()
    db.close()

    return render_template(
        "admin.html", username=session["username"], questions=all_questions, msg=msg
    )


@app.route("/admin/delete_question/<int:question_id>", methods=["POST"])
def delete_question(question_id):
    if session.get("role") != "Admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
    db.commit()
    db.close()
    return redirect("/admin")


@app.route("/mentor")
def mentor():
    # Only logged-in mentors can open this page
    if session.get("role") != "Mentor":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Find which mentor name belongs to this account
    cursor.execute("SELECT mentor_name FROM users WHERE username = %s", (session["username"],))
    row = cursor.fetchone()
    mentor_name = row["mentor_name"] if row else None

    bookings = []
    if mentor_name:
        cursor.execute(
            "SELECT username AS student, session_date AS date, topic AS topic "
            "FROM bookings WHERE mentor = %s ORDER BY session_date",
            (mentor_name,),
        )
        bookings = cursor.fetchall()
    db.close()

    return render_template(
        "mentor.html",
        username=session["username"],
        mentor_name=mentor_name,
        bookings=bookings,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/admin/careers", methods=["GET", "POST"])
def admin_careers():
    if session.get("role") != "Admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    msg = None
    error = None

    try:
        # Add a new skill
        if request.method == "POST" and "add_skill" in request.form:
            cursor.execute(
                "INSERT INTO skills (name, course) VALUES (%s, %s)",
                (request.form["skill_name"].strip(), request.form["course"].strip()),
            )
            db.commit()
            msg = "Skill added."

        # Add a new career with its required skills
        if request.method == "POST" and "add_career" in request.form:
            skill_ids = request.form.getlist("skill_ids")
            if not skill_ids:
                error = "Pick at least one skill for the career."
            else:
                cursor.execute(
                    "INSERT INTO careers (name, quiz_category) VALUES (%s, %s)",
                    (request.form["career_name"].strip(), request.form["category"]),
                )
                career_id = cursor.lastrowid
                for skill_id in skill_ids:
                    cursor.execute(
                        "INSERT INTO career_skills (career_id, skill_id) VALUES (%s, %s)",
                        (career_id, skill_id),
                    )
                db.commit()
                msg = "Career added."
    except mysql.connector.IntegrityError:
        db.rollback()
        error = "That name already exists."

    # Load all skills
    cursor.execute("SELECT id, name, course FROM skills ORDER BY name")
    all_skills = cursor.fetchall()

    # Load all careers with their skills
    cursor.execute(
        "SELECT c.id, c.name, c.quiz_category, s.name AS skill "
        "FROM careers c "
        "LEFT JOIN career_skills cs ON cs.career_id = c.id "
        "LEFT JOIN skills s ON s.id = cs.skill_id "
        "ORDER BY c.id, s.name"
    )
    careers_map = {}
    for row in cursor.fetchall():
        entry = careers_map.setdefault(
            row["id"],
            {"id": row["id"], "name": row["name"], "category": row["quiz_category"], "skills": []},
        )
        if row["skill"]:
            entry["skills"].append(row["skill"])
    db.close()

    return render_template(
        "admin_careers.html",
        username=session["username"],
        skills=all_skills,
        careers=list(careers_map.values()),
        msg=msg,
        error=error,
    )


@app.route("/admin/delete_career/<int:career_id>", methods=["POST"])
def delete_career(career_id):
    if session.get("role") != "Admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()
    # Remove the links first, then the career itself
    cursor.execute("DELETE FROM career_skills WHERE career_id = %s", (career_id,))
    cursor.execute("DELETE FROM careers WHERE id = %s", (career_id,))
    db.commit()
    db.close()
    return redirect("/admin/careers")


@app.route("/admin/delete_skill/<int:skill_id>", methods=["POST"])
def delete_skill(skill_id):
    if session.get("role") != "Admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM career_skills WHERE skill_id = %s", (skill_id,))
    cursor.execute("DELETE FROM skills WHERE id = %s", (skill_id,))
    db.commit()
    db.close()
    return redirect("/admin/careers")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
