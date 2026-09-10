from flask import Flask, render_template, request, redirect, flash, session, jsonify
import mysql.connector
import re
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import difflib
import ai_service  # New AI Service Module

# ---------- PRIORITY LOGIC (Merged from priority_degree.py) ----------

class CareerSuggester:
    """Average base class for suggesting careers."""
    def suggest(self, query):
        """
        Base suggest method.
        """
        return []

class PriorityCareerSuggester(CareerSuggester):
    """
    Subclass that provides suggestions sorted by priority using local relevance logic.
    """
    def suggest_with_priority(self, candidates, query):
        """
        Takes a list of candidate dictionaries (from DB) and sorts them
        based on local relevance scores (Exact > StartsWith > Contains).
        
        candidates: List of dicts, e.g., [{'keyword': 'Engineer', ...}, ...]
        query: The user's search query
        """
        query = query.lower().strip()
        
        # Initialize MaxPriorityQueue
        pq = MaxPriorityQueue()
        
        for cand in candidates:
            keyword = cand.get("keyword", "").lower().strip()
            score = 0
            
            # Local Scoring Logic (Simulating API Priority for Speed)
            if keyword == query:
                score = 1000  # Exact match
            elif keyword.startswith(query):
                score = 500   # Prefix match
            elif f" {query}" in f" {keyword}": 
                score = 300   # Word match (e.g. "Software Engineer" for "Engineer")
            elif query in keyword:
                score = 100   # Substring match
            
            # Tie-breaker: Shorter keywords are usually more relevant for suggestions
            if score > 0:
                score -= len(keyword) * 0.1
            
            # Insert into Priority Queue
            pq.insert(cand, score, keyword)
            
        # Extract from Priority Queue to get sorted list
        sorted_candidates = []
        while not pq.is_empty():
            sorted_candidates.append(pq.extract_max())
        
        return sorted_candidates

def get_priority_suggestions(candidates, query):
    """
    Helper function to use the PriorityCareerSuggester.
    Now takes full candidates list from DB.
    """
    suggester = PriorityCareerSuggester()
    return suggester.suggest_with_priority(candidates, query)


# ---------- APP ----------
app = Flask(__name__)
app.secret_key = os.urandom(24)


# ---------- DATABASE ----------
def get_db():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="career_guidance"
        )
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        raise

# ---------- DECORATORS ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("is_logged_in") != 1:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# ---------- DATA STRUCTURES ----------
class MaxPriorityQueue:
    def __init__(self):
        self.heap = []

    def parent(self, i):
        return (i - 1) // 2

    def left_child(self, i):
        return 2 * i + 1

    def right_child(self, i):
        return 2 * i + 2

    def swap(self, i, j):
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]

    def _is_higher_priority(self, i, j):
        # Primary: Priority value (Higher is better)
        if self.heap[i]["priority"] != self.heap[j]["priority"]:
            return self.heap[i]["priority"] > self.heap[j]["priority"]
        # Secondary: Alphabetical order (A is "higher rank" than Z for display)
        return self.heap[i]["keyword"] < self.heap[j]["keyword"]

    def insert(self, item, priority, keyword=""):
        self.heap.append({"data": item, "priority": priority, "keyword": keyword.lower()})
        self._sift_up(len(self.heap) - 1)

    def _sift_up(self, i):
        while i > 0 and self._is_higher_priority(i, self.parent(i)):
            self.swap(i, self.parent(i))
            i = self.parent(i)

    def extract_max(self):
        if not self.heap:
            return None
        max_item = self.heap[0]
        self.heap[0] = self.heap[-1]
        self.heap.pop()
        if self.heap:
            self._sift_down(0)
        return max_item["data"]

    def _sift_down(self, i):
        max_index = i
        l = self.left_child(i)
        r = self.right_child(i)

        if l < len(self.heap) and self._is_higher_priority(l, max_index):
            max_index = l
        
        if r < len(self.heap) and self._is_higher_priority(r, max_index):
            max_index = r
            
        if i != max_index:
            self.swap(i, max_index)
            self._sift_down(max_index)

    def is_empty(self):
        return len(self.heap) == 0

# ---------- SEARCH SYSTEM (OOP CONCEPT) ----------
class SearchManager:
    def __init__(self):
        self.table_name = "degrees"

    def get_suggestions(self, query):
        results = []
        conn = None
        cursor = None
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)

            # Fetch specific columns: keyword, source, page_name, div_id, target_type
            sql = f"SELECT keyword, source, page_name, div_id, target_type FROM {self.table_name} WHERE LOWER(keyword) LIKE %s LIMIT 100"
            search_val = f"{query.lower()}%"
            cursor.execute(sql, (search_val,))
            db_results = cursor.fetchall()

            # Convert to list of dicts if not already
            candidates = [dict(row) for row in db_results]

            # Use the new API-based priority logic
            # This replaces the local MaxPriorityQueue implementation
            results = get_priority_suggestions(candidates, query)
            
            results = results[:10]

        except Exception as e:
            print(f"Error fetching suggestions: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return results

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("is_logged_in") == 1:
        return redirect("/home")

    if request.method == "POST":
        name = request.form.get("user_name", "").strip()
        email = request.form.get("user_email", "").strip()
        password = request.form.get("user_password", "")
        confirm_pass = request.form.get("confirm_password", "")
        mobile = request.form.get("user_mobile", "").strip()
        education = request.form.get("education", "")


        if not password:
            flash("Password cannot be empty", "danger")
            return redirect("/signup")
        if password!=confirm_pass:
            flash("Password and Confirm Password do not match", "danger")
            return redirect("/signup")
        if not re.match(r'^[6-9]\d{9}$', mobile):
            flash("Invalid mobile number", "danger")
            return redirect("/signup")
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            flash("Invalid email address", "danger")
            return redirect("/signup")
        
        hashed_password = generate_password_hash(password)

        conn=get_db()
        cursor=conn.cursor()

        cursor.execute(
            "SELECT id FROM user_sign_in WHERE email = %s",(email,)
        )
        existing_user=cursor.fetchone()

        if existing_user:
            flash("Email already exists", "danger")
            cursor.close()
            conn.close()
            return redirect("/login")

    
        cursor.execute(
            """
            INSERT INTO user_sign_in 
            (name, email, password, mobile, education) 
            VALUES (%s, %s, %s, %s, %s)
            """,
            (name, email, hashed_password, mobile, education)
        )
        conn.commit()

        cursor.close()
        conn.close()

        flash("Signup successful! Please login.", "success")
        return redirect("/login")

    return render_template("Signup.html")
# ====================================================================================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("is_logged_in") == 1:
        return redirect("/home")

    if request.method == "POST":
        email = request.form.get("user_email", "").strip()
        password = request.form.get("user_password", "")

        # Empty field check
        if not email or not password:
            flash("Email and password are required", "danger")
            return redirect("/login")

        conn = get_db()
        cursor = conn.cursor()

        # Fetch user by email
        cursor.execute(
            "SELECT id, name, password FROM user_sign_in WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()

        # User not found
        if not user:
            cursor.close()
            conn.close()
            flash("First You Need To Sign Up", "danger")
            return redirect("/signup")

        # Password check
        if not check_password_hash(user[2], password):
            cursor.close()
            conn.close()
            flash("Invalid email or password", "danger")
            return redirect("/login")
        
        cursor.execute(
            "INSERT INTO user_login (user_id, email, login_date, login_time) VALUES (%s,%s,CURDATE(),CURTIME())",(user[0],email)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Login success → create session
        session["is_logged_in"] = 1
        session["u_id"]=user[0]

        flash("Login successful", "success")
        return redirect("/")

    return render_template("Login.html")


@app.route("/search-suggest")
def search_suggest():
    query = request.args.get("q", "").lower()

    if query == "":
        return jsonify([])

    search_engine = SearchManager()
    suggestions = search_engine.get_suggestions(query)

    # Clean up page_name to ensure valid URLs in suggestions
    for s in suggestions:
        page = s.get("page_name")
        if page:
            page = page.strip()
            if page.startswith("/"):
                page = page[1:]
            if page.endswith(".html"):
                page = page[:-5]
            s["page_name"] = page.lower()

    return jsonify(suggestions)

@app.route("/search-redirect")
@login_required
def search_redirect():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return redirect("/")

    # Redirect directly to the AI-powered Path page
    # This ensures the 'get_career_path' API is called, which prioritizes Gemini AI
    return redirect(f"/path?career={q}")

@app.route("/add_favourite", methods=["POST"])
@login_required
def add_favourite():
    data = request.json
    if not data:
        return jsonify({"message": "Invalid request data", "status": "error"}), 400

    user_id = session.get("u_id") # Fixed: session key is 'u_id'
    career_name = data.get("career")

    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check validation
        cursor.execute("SELECT favourite_career FROM favourite_careers WHERE user_id=%s", (user_id,))
        rows = cursor.fetchall()
        for r in rows:
            try:
                fav = json.loads(r[0])
                if fav.get("career") == career_name:
                    return jsonify({"message": "Already in favourites!", "status": "exists"})
            except:
                continue

        # Fetch user_name since it is not in session
        cursor.execute("SELECT name FROM user_sign_in WHERE id = %s", (user_id,))
        res = cursor.fetchone()
        user_name = res[0] if res else "Unknown"

        cursor.execute(
            "INSERT INTO favourite_careers (user_id, user_name, favourite_career) VALUES (%s,%s,%s)",
            (user_id, user_name, json.dumps(data))
        )

        conn.commit()
        return jsonify({"message": "Added to favourites ⭐", "status": "added"})
    except Exception as e:
        print(f"Error in add_favourite: {e}")
        return jsonify({"message": "Database error", "status": "error"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route("/remove_favourite", methods=["POST"])
@login_required
def remove_favourite():
    data = request.json
    if not data:
        return jsonify({"message": "Invalid request data"}), 400

    career_name = data.get("career")
    user_id = session.get("u_id")
    
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, favourite_career FROM favourite_careers WHERE user_id=%s", (user_id,))
        rows = cursor.fetchall()
        
        row_to_delete = None
        for r in rows:
            try:
                fav_obj = json.loads(r[1])
                if fav_obj.get("career") == career_name:
                    row_to_delete = r[0]
                    break
            except:
                continue
                
        if row_to_delete:
            cursor.execute("DELETE FROM favourite_careers WHERE id=%s", (row_to_delete,))
            conn.commit()
            msg = "Removed from favourites"
        else:
            msg = "Item not found"
        return jsonify({"message": msg})
    except Exception as e:
        print(f"Error in remove_favourite: {e}")
        return jsonify({"message": "Database error"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route("/get_favourites")
@login_required
def get_favourites():
    user_id = session.get("u_id") # Fixed: session key is 'u_id'

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT favourite_career FROM favourite_careers WHERE user_id=%s",
        (user_id,)
    )

    data = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(data)

# ---------- PAGES ----------
@app.route("/")
@app.route("/home")
def home():
    return render_template("Home.html")

@app.route("/about")
def about():
    return render_template("About.html")

@app.route("/10th")
@login_required
def tenth():
    return render_template("10th.html")

@app.route("/12th")
@login_required
def twelfth():
    return render_template("12th.html")

@app.route("/graduation")
@login_required
def graduation():
    return render_template("Graduation.html")

@app.route("/unique_career")
@login_required
def unique_career():
    return render_template("Unique_Career.html")

@app.route("/contact")
def contact():
    return render_template("Contact.html")

@app.route("/profile")
@login_required
def profile():
    
    conn=get_db()
    cursor=conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT name, email, mobile, education FROM user_sign_in WHERE id=%s",
        (session.get("u_id"),)
    )
    detail=cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("Profile.html",detail=detail)


@app.route("/comparison")
@login_required
def comparison():
    return render_template("comparison.html")

@app.route("/path")
def career_path_page():
    return render_template("Path.html")

@app.route("/api/career-path")
def get_career_path():
    user_query = request.args.get("career", "").strip()
    
    if not user_query:
        return jsonify({"error": "Please provide a career name"}), 400

    # 1. Conversational "Chit-Chat" Handling
    greetings = {
        "hi": "Hello! 👋 How can I help you explore your career today?",
        "hello": "Hi there! Ready to find your perfect career path?",
        "hey": "Hey! What career are you interested in?",
        "how are you": "I'm just a bot, but I'm functioning perfectly! 🚀 How can I help you?",
        "who are you": "I'm your AI Career Guide. I can help you find details about different careers.",
        "what can you do": "I can give you a roadmap for careers like Doctor, Engineer, Police, and more! Just type a career name.",
        "bye": "Goodbye! 👋 Best of luck with your future!",
        "thank you": "You're welcome! 😊 Let me know if you need anything else.",
        "thanks": "Happy to help! 🌟"
    }

    lower_query = user_query.lower()
    
    # Check for exact greeting match or if query contains greeting
    if lower_query in greetings:
         return jsonify({
            "status": "greeting",
            "message": greetings[lower_query]
        })

    # Special logic for Engineering prompt (Keep this as it's useful)
    # Only trigger for generic queries like "engineer" or "engineering"
    if lower_query in ["engineer", "engineering", "engineers"]:
         return jsonify({
            "status": "follow_up",
            "message": "Which engineering branch are you interested in? (Computer, Civil, Mechanical, Electrical, etc.)"
        })

    # --- AI INTEGRATION (Gemini) ---
    try:
        ai_data = ai_service.get_gemini_details(user_query, mode="career")
        
        # Check if response contains error information
        if isinstance(ai_data, dict) and "error" in ai_data:
            error_type = ai_data.get("error", "UNKNOWN_ERROR")
            error_message = ai_data.get("message", "An error occurred.")
            
            return jsonify({
                "status": "error",
                "error_type": error_type,
                "message": error_message
            })
        elif ai_data:
            return jsonify({"status": "success", "data": ai_data})
        else:
            return jsonify({
                "status": "error",
                "error_type": "UNKNOWN_ERROR",
                "message": "I couldn't fetch details from the AI. Please try again later."
            })
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({
            "status": "error",
            "error_type": "EXCEPTION",
            "message": f"An error occurred while connecting to the AI: {str(e)}"
        })

@app.route("/api/exam-info")
def get_exam_info():
    query = request.args.get("exam", "").strip()
    
    if not query:
        return jsonify({"error": "Please provide an exam name"}), 400

    # --- AI Integration for Exams ---
    try:
        ai_data = ai_service.get_gemini_details(query, mode="exam")
        
        # Check if response contains error information
        if isinstance(ai_data, dict) and "error" in ai_data:
            error_type = ai_data.get("error", "UNKNOWN_ERROR")
            error_message = ai_data.get("message", "An error occurred.")
            
            return jsonify({
                "status": "error",
                "error_type": error_type,
                "message": error_message
            })
        elif ai_data:
            return jsonify({
                "status": "success", 
                "data": [ai_data] 
            })
        else:
            return jsonify({
                "status": "error",
                "error_type": "UNKNOWN_ERROR",
                "message": "I couldn't fetch exam details from the AI."
            })
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({"status": "error", "message": "An error occurred while connecting to the AI."})

# Hardcoded Data for Enrichment (Backend Source of Truth)
# Hardcoded Data for Enrichment (Backend Source of Truth)
CAREER_DATA_10TH = {
    "PCM": {
        "Course Name": "PCM",
        "Eligibility": "10th Pass (Science & Maths)",
        "Duration": "2 Years",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹25,000–50,000",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "PCB": {
        "Course Name": "PCB",
        "Eligibility": "10th Pass (Science)",
        "Duration": "2 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹30,000–60,000",
        "Growth Potential": "High",
        "Job Stability": "Very High"
    },
    "PCMB": {
        "Course Name": "PCMB",
        "Eligibility": "10th Pass (Science & Maths)",
        "Duration": "2 Years",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹25,000–60,000",
        "Growth Potential": "Very High",
        "Job Stability": "High"
    },
    "Commerce": {
        "Course Name": "Commerce",
        "Eligibility": "10th Pass",
        "Duration": "2 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹20,000–40,000",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Arts": {
        "Course Name": "Arts",
        "Eligibility": "10th Pass",
        "Duration": "2 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹15,000–30,000",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Diploma": {
        "Course Name": "Diploma",
        "Eligibility": "10th Pass",
        "Duration": "3 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹12,000–25,000",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "ITI": {
        "Course Name": "ITI",
        "Eligibility": "8th/10th Pass",
        "Duration": "1 – 2 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹8,000–18,000",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Vocational": {
        "Course Name": "Vocational",
        "Eligibility": "8th/10th Pass",
        "Duration": "6 Months – 2 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹8,000–15,000",
        "Growth Potential": "Low",
        "Job Stability": "Medium"
    },
    "Apprenticeship": {
        "Course Name": "Apprenticeship",
        "Eligibility": "10th Pass / ITI",
        "Duration": "6 Months – 2 Years",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹10,000–20,000",
        "Growth Potential": "High",
        "Job Stability": "High"
    }
}

CAREER_DATA_12TH = {
    # PCM Careers
    "Bachelor of Design (B.Des)": {
        "Course Name": "Bachelor of Design (B.Des)",
        "Eligibility": "12th Pass",
        "Duration": "4 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹3–6 LPA",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "B.Tech / B.Des in Design Engineering": {
        "Course Name": "B.Tech / B.Des in Design Engineering",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹4–7 LPA",
        "Growth Potential": "Very High",
        "Job Stability": "High"
    },
    "Interaction Design (UI/UX)": {
        "Course Name": "Interaction Design (UI/UX)",
        "Eligibility": "12th Pass",
        "Duration": "3–4 Years",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹4–7 LPA",
        "Growth Potential": "Very High",
        "Job Stability": "Medium"
    },
    "Industrial / Product Design": {
        "Course Name": "Industrial / Product Design",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹4–6 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Physics": {
        "Course Name": "Physics",
        "Eligibility": "12th PCM",
        "Duration": "3 Years (B.Sc)",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3–5 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Chemistry": {
        "Course Name": "Chemistry",
        "Eligibility": "12th Science",
        "Duration": "3 Years (B.Sc)",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3–5 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "Mathematics": {
        "Course Name": "Mathematics",
        "Eligibility": "12th PCM",
        "Duration": "3 Years (B.Sc)",
        "Job Opportunities": "High",
        "Starting Salary": "₹3–6 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Statistics": {
        "Course Name": "Statistics",
        "Eligibility": "12th Maths",
        "Duration": "3 Years (B.Sc)",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹4–8 LPA",
        "Growth Potential": "Very High",
        "Job Stability": "High"
    },
    "Data Science (Science Route)": {
        "Course Name": "Data Science (Science Route)",
        "Eligibility": "12th Maths/Stats",
        "Duration": "3–4 Years",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹5–10 LPA",
        "Growth Potential": "Very High",
        "Job Stability": "High"
    },
    "Computer Science (CSE)": {
        "Course Name": "Computer Science (CSE)",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹4–12 LPA",
        "Growth Potential": "Very High",
        "Job Stability": "High"
    },
    "Mechanical Engineering": {
        "Course Name": "Mechanical Engineering",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹3.5–6 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Civil Engineering": {
        "Course Name": "Civil Engineering",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3–5 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "Electrical Engineering": {
        "Course Name": "Electrical Engineering",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹3.5–6 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Electronics (ECE)": {
        "Course Name": "Electronics (ECE)",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹3.5–7 LPA",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "Chemical Engineering": {
        "Course Name": "Chemical Engineering",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹4–7 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Aerospace Engineering": {
        "Course Name": "Aerospace Engineering",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹5–10 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Automobile Engineering": {
        "Course Name": "Automobile Engineering",
        "Eligibility": "12th PCM",
        "Duration": "4 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3.5–6 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },

    # PCB Careers
    "Doctor (MBBS / BDS / BAMS)": {
        "Course Name": "Doctor (MBBS / BDS / BAMS)",
        "Eligibility": "12th PCB + NEET",
        "Duration": "5.5 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹6–10 LPA",
        "Growth Potential": "Very High",
        "Job Stability": "Very High"
    },
    "Nursing (B.Sc Nursing)": {
        "Course Name": "Nursing (B.Sc Nursing)",
        "Eligibility": "12th PCB",
        "Duration": "4 Years",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹3–4.5 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "BPT (Physiotherapy)": {
        "Course Name": "BPT (Physiotherapy)",
        "Eligibility": "12th PCB",
        "Duration": "4.5 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹2.5–4 LPA",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "B.Sc MLT (Lab Tech)": {
        "Course Name": "B.Sc MLT (Lab Tech)",
        "Eligibility": "12th PCB",
        "Duration": "3 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹2–3.5 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "B.Sc Radiology": {
        "Course Name": "B.Sc Radiology",
        "Eligibility": "12th PCB",
        "Duration": "3 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹2.5–4 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "B.Sc OTT (Operation Theatre)": {
        "Course Name": "B.Sc OTT (Operation Theatre)",
        "Eligibility": "12th PCB",
        "Duration": "3 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹2–3.5 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "B.Pharm (Bachelor of Pharmacy)": {
        "Course Name": "B.Pharm (Bachelor of Pharmacy)",
        "Eligibility": "12th PCB",
        "Duration": "4 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹3–5 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "D.Pharm (Diploma)": {
        "Course Name": "D.Pharm (Diploma)",
        "Eligibility": "12th PCB",
        "Duration": "2 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹2–3 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "B.Sc Biotechnology": {
        "Course Name": "B.Sc Biotechnology",
        "Eligibility": "12th PCB",
        "Duration": "3 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3–5 LPA",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "B.Sc Microbiology": {
        "Course Name": "B.Sc Microbiology",
        "Eligibility": "12th PCB/CB",
        "Duration": "3 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3–5 LPA",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "B.Sc Psychology": {
        "Course Name": "B.Sc Psychology",
        "Eligibility": "12th Pass",
        "Duration": "3 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3–5 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "B.Sc Agriculture": {
        "Course Name": "B.Sc Agriculture",
        "Eligibility": "12th Science",
        "Duration": "4 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹3–6 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "B.Sc Horticulture": {
        "Course Name": "B.Sc Horticulture",
        "Eligibility": "12th Science",
        "Duration": "4 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3–5 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "B.Sc Life Sciences": {
        "Course Name": "B.Sc Life Sciences",
        "Eligibility": "12th Science",
        "Duration": "3 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3–4 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },

    # PCMB (General)
    "PCMB Stream": {
        "Eligibility": "12th PCMB",
        "Duration": "Varies",
        "Job Opportunities": "Very High",
        "Starting Salary": "Varies",
        "Growth Potential": "Very High",
        "Job Stability": "High"
    },

    # Commerce Careers
    "Core Commerce": {
        "Eligibility": "12th Commerce",
        "Duration": "3 Years (B.Com)",
        "Job Opportunities": "High",
        "Starting Salary": "₹2.5–5 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Management": {
        "Eligibility": "12th Pass",
        "Duration": "3 Years (BBA)",
        "Job Opportunities": "High",
        "Starting Salary": "₹3–6 LPA",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "Professional Courses": {
        "Eligibility": "12th Pass",
        "Duration": "3–5 Years",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹6–10 LPA",
        "Growth Potential": "Very High",
        "Job Stability": "High"
    },
    "Law & Legal Studies": {
        "Eligibility": "12th Pass",
        "Duration": "5 Years (Integrated)",
        "Job Opportunities": "High",
        "Starting Salary": "₹4–8 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Banking & Financial Markets": {
        "Eligibility": "12th Commerce",
        "Duration": "3 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹3–5 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "Modern Commerce": {
        "Eligibility": "12th Commerce",
        "Duration": "3 Years",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹4–7 LPA",
        "Growth Potential": "Very High",
        "Job Stability": "Medium"
    },

    # Arts Careers
    "Core Arts": {
        "Eligibility": "12th Pass",
        "Duration": "3 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹2–4 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Humanities & Social Sciences": {
        "Eligibility": "12th Pass",
        "Duration": "3 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹2–4 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Fine & Performing Arts": {
        "Eligibility": "12th Pass",
        "Duration": "3–4 Years",
        "Job Opportunities": "Low to Medium",
        "Starting Salary": "₹2–5 LPA",
        "Growth Potential": "High (Skill based)",
        "Job Stability": "Low"
    },
    "Media & Design": {
        "Eligibility": "12th Pass",
        "Duration": "3 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹3–6 LPA",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "Languages & Literature": {
        "Eligibility": "12th Pass",
        "Duration": "3 Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹3-6 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Law & Public Service": {
        "Eligibility": "12th Pass",
        "Duration": "3-5 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹3-8 LPA",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Specialized Arts": {
        "Eligibility": "12th Pass",
        "Duration": "3 Years",
        "Job Opportunities": "Low to Medium",
        "Starting Salary": "₹2-4 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Low"
    },

    # Diploma
    "Diploma Courses": {
        "Eligibility": "10th/12th Pass",
        "Duration": "1–3 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹1.5–3 LPA",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    }
}

CAREER_DATA_UNIQUE = {
    # Skill-Based
    "Graphic Designer": {
        "Course Name": "Graphic Designer",
        "Eligibility": "No Degree / 10th Pass",
        "Learning Duration": "3–6 Months",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹15,000–30,000",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "Video Editor": {
        "Course Name": "Video Editor",
        "Eligibility": "No Degree / 10th Pass",
        "Learning Duration": "3–6 Months",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹18,000–35,000",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "Digital Marketer": {
        "Course Name": "Digital Marketer",
        "Eligibility": "No Degree / 10th Pass",
        "Learning Duration": "3–5 Months",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹18,000–40,000",
        "Growth Potential": "Very High",
        "Job Stability": "Medium"
    },
    "Web Designer": {
        "Course Name": "Web Designer",
        "Eligibility": "No Degree / 10th Pass",
        "Learning Duration": "4–8 Months",
        "Job Opportunities": "High",
        "Starting Salary": "₹20,000–45,000",
        "Growth Potential": "High",
        "Job Stability": "High"
    },
    "Social Media Manager": {
        "Course Name": "Social Media Manager",
        "Eligibility": "No Degree / 10th Pass",
        "Learning Duration": "2–4 Months",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹15,000–35,000",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "Mobile Repair Technician": {
        "Course Name": "Mobile Repair Technician",
        "Eligibility": "8th Pass / 10th Pass",
        "Learning Duration": "2–4 Months",
        "Job Opportunities": "High",
        "Starting Salary": "₹12,000–25,000",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },

    # Passion-Based
    "Vlogger / YouTuber": {
        "Course Name": "Vlogger / YouTuber",
        "Eligibility": "No degree required",
        "Learning Duration": "Self-paced",
        "Job Opportunities": "High",
        "Starting Salary": "₹0–50,000+ (Variable)",
        "Growth Potential": "Very High",
        "Job Stability": "Low"
    },
    "Gaming / Streamer": {
        "Course Name": "Gaming / Streamer",
        "Eligibility": "No degree required",
        "Learning Duration": "Self-paced",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹0–40,000+ (Variable)",
        "Growth Potential": "High",
        "Job Stability": "Low"
    },
    "Photography": {
        "Course Name": "Photography",
        "Eligibility": "No degree required",
        "Learning Duration": "3–6 Months",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹15,000–40,000",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "Music Creator": {
        "Course Name": "Music Creator",
        "Eligibility": "No degree required",
        "Learning Duration": "6–12 Months",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹10,000–30,000",
        "Growth Potential": "High",
        "Job Stability": "Low"
    },
    "Dance / Choreography": {
        "Course Name": "Dance / Choreography",
        "Eligibility": "No degree required",
        "Learning Duration": "6–12 Months",
        "Job Opportunities": "Medium",
        "Starting Salary": "₹15,000–35,000",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Acting / Content Acting": {
        "Course Name": "Acting / Content Acting",
        "Eligibility": "No degree required",
        "Learning Duration": "6–12 Months",
        "Job Opportunities": "Medium",
        "Starting Salary": "Variable",
        "Growth Potential": "High",
        "Job Stability": "Low"
    },

    # Practical & Local
    "Electrician": {
        "Course Name": "Electrician",
        "Eligibility": "8th Pass / ITI",
        "Learning Duration": "6–12 Months",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹12,000–25,000",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "Plumber": {
        "Course Name": "Plumber",
        "Eligibility": "8th Pass / ITI",
        "Learning Duration": "3–6 Months",
        "Job Opportunities": "High",
        "Starting Salary": "₹12,000–22,000",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "AC Technician": {
        "Course Name": "AC Technician",
        "Eligibility": "8th Pass / ITI",
        "Learning Duration": "3–6 Months",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹15,000–25,000",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "CCTV Technician": {
        "Course Name": "CCTV Technician",
        "Eligibility": "8th Pass / 10th Pass",
        "Learning Duration": "1–2 Months",
        "Job Opportunities": "High",
        "Starting Salary": "₹12,000–20,000",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Solar Panel Technician": {
        "Course Name": "Solar Panel Technician",
        "Eligibility": "10th Pass / ITI",
        "Learning Duration": "2–4 Months",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹15,000–25,000",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "Automobile Mechanic": {
        "Course Name": "Automobile Mechanic",
        "Eligibility": "8th Pass / ITI",
        "Learning Duration": "6–12 Months",
        "Job Opportunities": "High",
        "Starting Salary": "₹12,000–25,000",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },

    # Online & Modern
    "Freelancer": {
        "Course Name": "Freelancer",
        "Eligibility": "Skill-based",
        "Learning Duration": "1–3 Months",
        "Job Opportunities": "Very High",
        "Starting Salary": "Variable",
        "Growth Potential": "High",
        "Job Stability": "Low"
    },
    "Social Media Influencer": {
        "Course Name": "Social Media Influencer",
        "Eligibility": "No degree required",
        "Learning Duration": "Self-paced",
        "Job Opportunities": "High",
        "Starting Salary": "Variable",
        "Growth Potential": "Very High",
        "Job Stability": "Low"
    },
    "Dropshipping Business": {
        "Course Name": "Dropshipping Business",
        "Eligibility": "No degree required",
        "Learning Duration": "1–3 Months",
        "Job Opportunities": "High",
        "Starting Salary": "Variable",
        "Growth Potential": "High",
        "Job Stability": "Low"
    },
    "Virtual Assistant": {
        "Course Name": "Virtual Assistant",
        "Eligibility": "12th Pass / Graduate",
        "Learning Duration": "1–2 Months",
        "Job Opportunities": "High",
        "Starting Salary": "₹15,000–30,000",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Online Tutor": {
        "Course Name": "Online Tutor",
        "Eligibility": "Subject Expert / Degree",
        "Learning Duration": "None",
        "Job Opportunities": "High",
        "Starting Salary": "₹10,000–30,000",
        "Growth Potential": "Medium",
        "Job Stability": "Medium"
    },
    "Affiliate Marketer": {
        "Course Name": "Affiliate Marketer",
        "Eligibility": "No degree required",
        "Learning Duration": "1–2 Months",
        "Job Opportunities": "High",
        "Starting Salary": "Commission Based",
        "Growth Potential": "High",
        "Job Stability": "Low"
    },

    # Sports
    "Professional Athlete": {
        "Course Name": "Professional Athlete",
        "Eligibility": "Talent & Training",
        "Learning Duration": "5+ Years",
        "Job Opportunities": "Medium",
        "Starting Salary": "Variable",
        "Growth Potential": "Very High",
        "Job Stability": "Low"
    },
    "Cricket / Football Player": {
        "Course Name": "Cricket / Football Player",
        "Eligibility": "Talent & Training",
        "Learning Duration": "5+ Years",
        "Job Opportunities": "High",
        "Starting Salary": "Variable",
        "Growth Potential": "Very High",
        "Job Stability": "Low"
    },
    "Fitness Trainer": {
        "Course Name": "Fitness Trainer",
        "Eligibility": "12th Pass + Certification",
        "Learning Duration": "3–6 Months",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹15,000–40,000",
        "Growth Potential": "High",
        "Job Stability": "Medium"
    },
    "Sports Coach": {
        "Course Name": "Sports Coach",
        "Eligibility": "Experience / Certification",
        "Learning Duration": "1–2 Years",
        "Job Opportunities": "High",
        "Starting Salary": "₹20,000–50,000",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "Sports Referee": {
        "Course Name": "Sports Referee",
        "Eligibility": "Certification",
        "Learning Duration": "6–12 Months",
        "Job Opportunities": "Medium",
        "Starting Salary": "Per Match Basis",
        "Growth Potential": "Medium",
        "Job Stability": "Low"
    },
    "Sports Content Creator": {
        "Course Name": "Sports Content Creator",
        "Eligibility": "No degree required",
        "Learning Duration": "Self-paced",
        "Job Opportunities": "High",
        "Starting Salary": "Variable",
        "Growth Potential": "High",
        "Job Stability": "Low"
    }
}

CAREER_DATA_GRADUATION = {
    # Private Sector
    "Clerical & Assistant": {
        "Course Name": "Clerical & Assistant",
        "Eligibility": "Graduation (Any Stream)",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹25,000–40,000/month",
        "Growth Potential": "Medium",
        "Job Stability": "High"
    },
    "Banking & Insurance": {
        "Course Name": "Banking & Insurance",
        "Eligibility": "Graduation (Any Stream)",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹30,000–80,000/month",
        "Growth Potential": "High",
        "Job Stability": "Very High"
    },
    "Technical & Professional": {
        "Course Name": "Technical & Professional",
        "Eligibility": "Graduation (Relevant Degree)",
        "Job Opportunities": "High",
        "Starting Salary": "₹40,000–1,00,000+/month",
        "Growth Potential": "High",
        "Job Stability": "Very High"
    },
    "Defence & Uniform": {
        "Course Name": "Defence & Uniform",
        "Eligibility": "Graduation + Physical Fitness",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹40,000–1,20,000+/month",
        "Growth Potential": "High",
        "Job Stability": "Very High"
    },
    "Civil Services": {
        "Course Name": "Civil Services",
        "Eligibility": "Graduation (Any Stream)",
        "Job Opportunities": "Very High",
        "Starting Salary": "₹56,100–2,50,000+/month",
        "Growth Potential": "Very High",
        "Job Stability": "Very High"
    }
}

@app.route("/api/compare", methods=["POST"])
@login_required
def api_compare():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request data"}), 400

    selected_careers = data.get("careers", [])
    
    if not selected_careers or len(selected_careers) < 2:
        return jsonify({"error": "Please select at least 2 careers to compare"}), 400
        
    user_id = session.get("u_id")
    conn = None
    cursor = None
    user_favorites = []
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT favourite_career FROM favourite_careers WHERE user_id=%s", (user_id,))
        rows = cursor.fetchall()
        
        for r in rows:
            try:
                # Load the JSON object
                user_favorites.append(json.loads(r[0]))
            except:
                continue
    except Exception as e:
        print(f"Error in api_compare: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Filter for selected items
    selected_items = []
    source_check = None
    
    for selected_name in selected_careers:
        target = next((f for f in user_favorites if f.get("career") == selected_name), None)
        if not target:
            continue 
            
        current_source = target.get("source_page", "Unknown")
        
        # Enforce same-category comparison
        if source_check is None:
            source_check = current_source
        elif source_check != current_source:
             return jsonify({
                 "error": "Comparison Mismatch", 
                 "message": f"Cannot compare '{current_source}' careers with '{source_check}' careers. Please select from the same category."
             }), 400
        
        # --- DATA ENRICHMENT START ---
        # 10th Grade
        if current_source == "10th.html" or selected_name in CAREER_DATA_10TH:
             enrichment = CAREER_DATA_10TH.get(selected_name)
             if enrichment:
                 target.update(enrichment)
        
        # 12th Grade
        if current_source == "12th.html" or selected_name in CAREER_DATA_12TH:
             enrichment = CAREER_DATA_12TH.get(selected_name)
             if enrichment:
                 target.update(enrichment)
                 
        # Unique Careers
        if current_source == "Unique_Career.html" or selected_name in CAREER_DATA_UNIQUE:
             enrichment = CAREER_DATA_UNIQUE.get(selected_name)
             if enrichment:
                 target.update(enrichment)
                 
        # Graduation Careers
        if current_source == "Graduation.html" or selected_name in CAREER_DATA_GRADUATION:
             enrichment = CAREER_DATA_GRADUATION.get(selected_name)
             if enrichment:
                 target.update(enrichment)
        # --- DATA ENRICHMENT END ---

        selected_items.append(target)

    if not selected_items:
        return jsonify({"error": "No valid data found"}), 400

    # Dynamic Attribute Intersection Logic
    # 1. Start with keys from the first item
    # Exclude metadata keys that shouldn't be compared
    metadata_keys = {'career', 'source_page', 'icon_class', 'description', 'link', 'name', 'title', 'header_class'} 
    
    # Initialize common_keys with the first item's non-empty keys
    first_item = selected_items[0]
    common_keys = set()
    
    for k, v in first_item.items():
        if k not in metadata_keys and v and str(v).strip(): # Check key is not metadata AND value is truthy/non-empty
            common_keys.add(k)
            
    # 2. Intersect with all other items
    for item in selected_items[1:]:
        current_item_valid_keys = set()
        for k, v in item.items():
            # Check existence and non-empty value
            if k in common_keys and v and str(v).strip():
                current_item_valid_keys.add(k)
        
        # Intersection: Keep only keys present in both
        common_keys = common_keys.intersection(current_item_valid_keys)

    # Convert to list
    common_keys_list = list(common_keys)
    
    # Optional: Sort keys to ensure specific order if desired (e.g. Eligibility first)
    # But for now, we leave it dynamic or simple sort
    # custom_order = ["Eligibility", "Duration", "Job Opportunities", "Starting Salary", "Growth Potential", "Job Stability"]
    # common_keys_list.sort(key=lambda x: custom_order.index(x) if x in custom_order else 999)

    # 3. Construct Response Data
    final_data = []
    for item in selected_items:
        # Build object with name + common keys only
        obj = { "name": item.get("career") }
        for k in common_keys_list:
            obj[k] = item.get(k)
        final_data.append(obj)
        
    return jsonify({
        "common_keys": common_keys_list,
        "data": final_data
    })







@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- RUN ----------
# ---------- DEBUGGING ROUTE (Consolidated from debug_db.py & debug_keys.py) ----------
@app.route("/debug/db-check")
def debug_db_check():
    """
    Consolidated logic from previous debug strings.
    Checks table existence, schema, and column keys.
    """
    log = []
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Check Tables
        log.append("--- Checking Tables ---")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        log.append(f"Tables Found: {tables}")

        # 2. Check career_paths Columns
        log.append("\n--- Checking career_paths Columns ---")
        try:
            cursor.execute("DESCRIBE career_paths")
            columns = cursor.fetchall()
            for col in columns:
                log.append(f"Column: {col['Field']}")
        except Exception as e:
            log.append(f"Error describing table: {e}")

        # 3. Check Row Keys & Data
        log.append("\n--- Checking First Row & Keys ---")
        try:
            cursor.execute("SELECT * FROM career_paths LIMIT 1")
            row = cursor.fetchone()
            if row:
                log.append(f"Row Keys: {list(row.keys())}")
                # Clean keys demonstration
                clean_row = {k.strip(): v for k, v in row.items()}
                log.append(f"Cleaned Row Keys: {list(clean_row.keys())}")
            else:
                log.append("Table is empty")
        except Exception as e:
            log.append(f"Error fetching row: {e}")

        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "log": log})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
