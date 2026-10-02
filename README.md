# 🎓 Career Guidance Platform

> An AI-powered, comprehensive educational and career counseling web application designed to help students discover, compare, and navigate career paths after 10th, 12th, and Graduation.

---

## 📌 Table of Contents
- [Overview](#-overview)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Architecture & Directory Structure](#-project-architecture--directory-structure)
- [Search Algorithm & Priority Queue](#-search-algorithm--priority-queue)
- [AI Service Integration](#-ai-service-integration)
- [Database Schema](#-database-schema)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation & Setup](#installation--setup)
  - [Environment Variables Configuration](#environment-variables-configuration)
- [API Endpoints](#-api-endpoints)
- [Future Enhancements](#-future-enhancements)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

Choosing the right career path is one of the most critical decisions in a student's life. The **Career Guidance Platform** simplifies this journey by providing personalized career counseling, step-by-step educational roadmaps, entrance exam insights, top college listings, and a side-by-side career comparison tool.

Powered by **Google Gemini AI** and a custom **Max-Priority Queue search algorithm**, the platform dynamically generates real-time, detailed career roadmaps tailored to user queries ranging from traditional fields (Doctor, Engineer, Civil Services) to modern offbeat careers (AI/ML Engineer, Game Developer, Cyber Security Analyst, UX Designer).

---

## ⚡ Key Features

- 🤖 **AI-Powered Career & Exam Roadmap Generator**:
  - Dynamically generates multi-stage career roadmaps using **Google Gemini AI**.
  - Provides course durations, required entrance exams, eligibility, top colleges, estimated salary ranges, and job roles.
  - Multi-model automatic fallback mechanism (`gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`) for maximum reliability.

- 🔍 **Smart Priority Search System**:
  - Instant autocomplete search for career options and degrees.
  - Custom `MaxPriorityQueue` data structure in Python that ranks search results based on match relevance (Exact > Prefix > Word > Substring).

- ⚖️ **Side-by-Side Career Comparison**:
  - Compare multiple career choices across parameters like course duration, difficulty, qualification requirements, top entrance exams, scope, and salary outlook.

- 🎓 **Tailored Education Level Guidance**:
  - **After 10th Grade**: Stream selection guide (Science PCM/PCB, Commerce, Arts/Humanities), Polytechnic Diplomas, ITI, and skill development courses.
  - **After 12th Grade**: Comprehensive stream-wise breakdown with direct degree choices and competitive exam paths.
  - **Post-Graduation**: Higher education opportunities (Master's degrees, Ph.D.), government exams (UPSC, GATE, CAT, GRE), and industry career progression.

- 🚀 **Unique & Futuristic Careers**:
  - Specialized section showcasing emerging fields like Artificial Intelligence, Data Science, Game Development, Content Creation, Sound Engineering, Cyber Security, and Digital Marketing.

- ⭐ **Personalized Favorites & User Profile**:
  - Registered users can save career paths to their personal profile for quick reference and tracking.

- 🔐 **Secure User Authentication**:
  - User registration and authentication powered by Flask sessions and secure password hashing using `werkzeug.security`.

---

## 💻 Tech Stack

### **Backend**
- **Language**: Python 3.8+
- **Framework**: Flask (Web Framework)
- **AI Integration**: Google Gen AI SDK (`google-generativeai`)
- **Authentication & Security**: `werkzeug.security` (SHA-256 Hashing)
- **Environment Management**: `python-dotenv`

### **Frontend**
- **Structure & Logic**: HTML5, JavaScript (ES6+), Jinja2 Templating
- **Styling**: Custom Modern Glassmorphic CSS3 with responsive layouts

### **Database & Storage**
- **Database Management**: MySQL / MariaDB
- **Driver**: `mysql-connector-python`

---

## 📁 Project Architecture & Directory Structure

```text
Career_Guidance/
│
├── app.py                     # Main Flask Application & Route Handlers
├── ai_service.py              # Google Gemini AI Integration & Model Fallback Service
├── priority_degree.py         # Custom MaxPriorityQueue Search Algorithm Implementation
├── test_api.py                # Gemini API Integration Verification Test Script
├── career_guidance.sql        # MySQL Database Schema Dump & Seed Data
├── requirements.txt           # Python Package Dependencies
├── .env                       # Environment Variables (API Keys, DB Credentials)
│
├── templates/                 # Jinja2 HTML Templates
│   ├── Home.html              # Landing Page with Search & AI Career Generator
│   ├── 10th.html              # Post-10th Guidance Page
│   ├── 12th.html              # Post-12th Guidance Page
│   ├── Graduation.html        # Post-Graduation & Competitive Exams Page
│   ├── Path.html              # AI Roadmap Visualization Page
│   ├── Unique_Career.html     # Offbeat & Emerging Careers Overview Page
│   ├── comparison.html        # Multi-Career Side-by-Side Comparison Tool
│   ├── Profile.html           # User Profile & Saved Favorites Dashboard
│   ├── Login.html             # User Login Page
│   ├── SignUp.html            # User Registration Page
│   ├── About.html             # About Project & Mission Page
│   ├── Contact.html           # Contact & Feedback Form Page
│   └── streams/               # Specific Academic Stream Templates
│       ├── pcm.html           # Science (Physics, Chemistry, Maths)
│       ├── pcb.html           # Science (Physics, Chemistry, Biology)
│       ├── pcmb.html          # Science (PCM + Biology)
│       ├── commerce.html       # Commerce Stream Careers
│       ├── arts.html           # Arts & Humanities Stream Careers
│       ├── diploma.html        # Polytechnic & Vocational Diplomas
│       ├── government.html     # Government Job Exams (UPSC, SSC, Banking)
│       └── unique.html         # Specialized Unique Careers List
│
└── static/                    # Static Assets (Images, Branding, Styles)
    ├── Logo.png               # Platform Logo
    └── Back2.png              # Background Visuals
```

---

## 🧮 Search Algorithm & Priority Queue

The platform uses a custom Object-Oriented **Max Priority Queue** (`MaxPriorityQueue`) data structure to order career suggestions dynamically when users type in the search bar:

$$\text{Relevance Score} = \begin{cases} 
1000 & \text{Exact Match} \\
500 & \text{Prefix Match} \\
300 & \text{Word Match} \\
100 & \text{Substring Match} 
\end{cases} - (\text{Length of Keyword} \times 0.1)$$

```python
class PriorityCareerSuggester(CareerSuggester):
    def suggest_with_priority(self, candidates, query):
        pq = MaxPriorityQueue()
        for cand in candidates:
            # Score candidate based on match type
            score = self.calculate_score(cand["keyword"], query)
            pq.insert(cand, score, cand["keyword"])
        return pq.get_sorted_results()
```

---

## 🤖 AI Service Integration

The application leverages **Google Gemini AI** to produce structured, up-to-date roadmaps for any search term. 

### **Model Priority Queue**
To avoid quota downtime and ensure robust availability, `ai_service.py` executes a priority fallback strategy:
1. `gemini-2.5-flash` *(Primary - Optimal speed & intelligence)*
2. `gemini-2.5-pro` *(Backup - Complex queries)*
3. `gemini-2.0-flash` *(Secondary fallback)*
4. `gemini-2.0-flash-lite` *(Fast lightweight fallback)*

---

## 🗄️ Database Schema

The platform utilizes a MySQL database named `career_guidance` containing key tables:

- **`user_sign_in`**: Stores user profiles (`id`, `name`, `email`, `password`, `mobile`, `education`).
- **`user_login`**: Tracks user login sessions (`id`, `user_id`, `email`, `login_date`, `login_time`).
- **`favourite_careers`**: Stores user-bookmarked career paths (`id`, `user_id`, `user_name`, `favourite_career`).
- **`career_paths`**: Contains structured database records for static fallback career paths (`career_name`, `after_10th`, `after_12th`, `exams`, `course`, `college_type`, `duration`, `degree`).
- **`degrees`**: Stores keywords, page mappings, and DOM targets for quick search indexing (`id`, `keyword`, `source`, `page_name`, `div_id`, `target_type`).

---

## 🚀 Getting Started

Follow these instructions to get a local copy up and running on your system.

### **Prerequisites**

Ensure you have the following installed on your machine:
- **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
- **MySQL Server** (via XAMPP, WAMP, or standalone MySQL Server)
- **Google Gemini API Key**: [Get API Key from Google AI Studio](https://aistudio.google.com/app/apikey)

---

### **Installation & Setup**

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/YourUsername/Career_Guidance.git
   cd Career_Guidance/Career_Guidance
   ```

2. **Create and Activate a Virtual Environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Import Database Schema**:
   - Open phpMyAdmin or your MySQL client.
   - Create a database named `career_guidance`:
     ```sql
     CREATE DATABASE career_guidance;
     ```
   - Import `career_guidance.sql` into the `career_guidance` database:
     ```bash
     mysql -u root -p career_guidance < career_guidance.sql
     ```

5. **Configure Environment Variables**:
   Create a `.env` file in the root project directory (where `app.py` resides):
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=
   DB_NAME=career_guidance
   ```

6. **Run the Flask Application**:
   ```bash
   python app.py
   ```

7. **Access the Application**:
   Open your browser and navigate to:
   `http://127.0.0.1:5000/`

---

## 📡 API Endpoints

| Endpoint | Method | Authentication | Description |
| :--- | :---: | :---: | :--- |
| `/` or `/home` | `GET` | Public | Home landing page with career search & AI generator |
| `/signup` | `GET / POST` | Public | User registration endpoint |
| `/login` | `GET / POST` | Public | User authentication endpoint |
| `/search-suggest` | `GET` | Public | Real-time autocomplete suggestions powered by `MaxPriorityQueue` |
| `/api/career-path` | `GET` | Public | Fetches detailed AI-generated career roadmap (`?career=Doctor`) |
| `/api/exam-info` | `GET` | Public | Fetches entrance exam syllabus, timeline, and structure (`?exam=NEET`) |
| `/comparison` | `GET` | Login Required | Side-by-side career comparison tool page |
| `/add_favourite` | `POST` | Login Required | Saves a career roadmap to user's favorites |
| `/remove_favourite` | `POST` | Login Required | Removes a saved career roadmap from favorites |
| `/get_favourites` | `GET` | Login Required | Retrieves all saved favorite careers for logged-in user |
| `/profile` | `GET` | Login Required | Displays user profile information and saved favorites |

---

## 🔮 Future Enhancements

- 📊 **Psychometric & Interest Quiz**: Interactive career assessment test to calculate personalized stream suitability scores.
- 🎓 **Scholarship & Financial Aid Finder**: Automated engine listing active state/national scholarships for students.
- 💬 **Real-Time AI Chatbot Counselor**: Conversational assistant for instant Q&A on career choices.
- 📱 **Mobile Application**: Flutter-based mobile app for iOS & Android.

---

## 🤝 Contributing

Contributions are welcome! If you would like to contribute:
1. Fork the project repository.
2. Create your Feature Branch (`git checkout -b feature/AwesomeFeature`).
3. Commit your changes (`git commit -m 'Add some AwesomeFeature'`).
4. Push to the Branch (`git push origin feature/AwesomeFeature`).
5. Open a Pull Request.

---

## 📝 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<p align="center">
  Crafted with ❤️ for students navigating their future careers.
</p>
