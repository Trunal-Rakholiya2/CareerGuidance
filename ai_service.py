"""
AI Service using Google Gemini (New SDK: google-genai)

This service uses the latest Google Gen AI SDK to provide career and exam roadmaps.
"""

import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure Gemini API Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found in environment.")

# Try models in this order until one works
# Try models in this order until one works
MODEL_PRIORITY = [
    "gemini-2.5-flash",        # Best balance of speed and intelligence
    "gemini-2.5-pro",          # Higher intelligence backup
    "gemini-2.0-flash",        # Backup
    "gemini-2.0-flash-lite",   # Faster backup
]

def _extract_json_from_text(text: str):
    """Extract JSON object from AI response text."""
    # Remove markdown code blocks if present
    text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)
    
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = text[start_idx:end_idx + 1]
        
        # Clean up common LLM JSON errors
        json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    return None

def _call_gemini_api(prompt: str, max_retries: int = 3):
    """Call Google Gemini API using google-generativeai SDK with retry logic."""
    if not GEMINI_API_KEY:
        return {"error": "CONFIG_ERROR", "message": "API Client not configured. Check your API Key in .env file."}
    
    # Try each model in priority order
    for model_name in MODEL_PRIORITY:
        try:
            print(f"Trying model: {model_name}")
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                print(f"Model {model_name} returned empty response, trying next...")
                continue  # Try next model
                
            print(f"✅✅✅ SUCCESS with model: {model_name} ✅✅✅")
            return {"content": response.text}
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # If quota exceeded, don't try other models
            if "429" in error_msg or "resource_exhausted" in error_msg:
                retry_after = 60  # Default
                try:
                    if "retry in" in error_msg:
                        import re as regex
                        match = regex.search(r'retry in (\d+)', error_msg)
                        if match:
                            retry_after = int(match.group(1))
                except:
                    pass
                
                return {
                    "error": "QUOTA_EXCEEDED", 
                    "message": "⚠️ **API quota exceeded**. Your Gemini API free tier limit has been reached. Please wait 1 minute or get a new API key at https://aistudio.google.com/app/apikey",
                    "retry_after": retry_after
                }
            
            # If auth error, don't try other models
            if "401" in error_msg or "unauthenticated" in error_msg or "invalid api key" in error_msg or "api_key_invalid" in error_msg:
                return {"error": "AUTH_ERROR", "message": "❌ Invalid API key. Please check your GEMINI_API_KEY in the .env file. Get a new key at: https://aistudio.google.com/app/apikey"}
            
            # If model not found, try next model
            if "404" in error_msg or "not found" in error_msg:
                print(f"Model {model_name} not available, trying next...")
                continue
            
            # Other errors - try next model
            print(f"Error with {model_name}: {str(e)[:100]}")
            continue
    
    # If all models failed
    return {
        "error": "MODEL_NOT_FOUND", 
        "message": f"❌ Could not find a working Gemini model. Tried: {', '.join(MODEL_PRIORITY)}. Your API key might not have access to these models. Please check at: https://aistudio.google.com/app/apikey"
    }

def get_career_details(topic: str):
    """Fetch comprehensive career details using Gemini. NOT CACHED to allow retries."""
    topic = (str(topic) or "").strip()
    if not topic:
        return {"error": "EMPTY_QUERY", "message": "Please provide a career name."}
    
    print(f"Gemini Service (New SDK): Fetching career details for '{topic}'...")
    
    prompt = f"""You are an expert career counselor.

For the career/degree: "{topic}"

Provide a concise career roadmap in India. Return ONLY a valid JSON object with these exact keys:

{{
  "career_name": "Full name of the career",
  "stream_after_10th": "Which stream to choose after 10th (Science/Commerce/Arts/Vocational) and why. Be specific about subjects.",
  "stream_after_12th": "Which stream/subjects to choose after 12th and why. Mention specific subjects if applicable.",
  "college_type": "Types of colleges offering this course (Government/Private/Deemed universities, etc.)",
  "courses": "Available courses related to this career (degree names, diploma names, certifications)",
  "entrance_exams": "List all entrance exams required (national, state, university level). Include exam names.",
  "future_scope": "Future scope, job opportunities, and growth prospects in India",
  "salary": {{
    "starting": "Starting salary range for freshers in India (in INR)",
    "average": "Average salary range for experienced professionals (in INR)",
    "highest": "Highest salary potential (in INR)"
  }},
  "duration": "Course duration (e.g., '3 years', '4 years', '5.5 years')",
  "top_colleges": "Top 5-7 colleges/institutes in India offering this course (names only, comma-separated)",
  "skills": "Key skills required for this career (technical and soft skills)",
  "reality_check": "Competition level, difficulty, market demand, challenges, and realistic expectations"
}}

Important:
- Focus on Indian education system and job market
- Be specific, practical, and concise (max 2 sentences per field)
- Return ONLY the raw JSON object
"""

    response = _call_gemini_api(prompt)
    if "error" in response:
        return response

    text = response.get("content", "").strip()
    data = _extract_json_from_text(text)
    
    if data:
        # Normalize salary structure if AI returned a string instead of object
        if isinstance(data.get("salary"), str):
            data["salary"] = {"starting": data.get("salary", ""), "average": "N/A", "highest": "N/A"}
        
        print("Gemini Service: Success!")
        return data
    else:
        return {
            "error": "PARSE_ERROR",
            "message": "Failed to parse AI response.",
            "raw_text": text[:200]
        }

def get_exam_details(exam_name: str):
    """Fetch comprehensive exam details using Gemini. NOT CACHED to allow retries."""
    exam_name = (str(exam_name) or "").strip()
    if not exam_name:
        return {"error": "EMPTY_QUERY", "message": "Please provide an exam name."}
    
    print(f"Gemini Service (New SDK): Fetching exam details for '{exam_name}'...")
    
    prompt = f"""You are an expert on Indian competitive exams.

For the exam: "{exam_name}"

Provide concise exam details. Return ONLY a valid JSON object with these exact keys:

{{
  "exam_name": "Full name of the exam",
  "conducting_authority": "Who conducts this exam (organization name)",
  "purpose": "What is this exam for? What can you achieve through it?",
  "number_of_papers": "Number of papers/sections in the exam",
  "total_marks": "Total marks for the exam",
  "eligibility": "Eligibility criteria (age, educational qualification, percentage, etc.)",
  "importance": "Why this exam is important and what opportunities it opens",
  "colleges_and_degrees": "Colleges and degrees that can be obtained through this exam",
  "subjects": "Subjects/topics included in the exam syllabus",
  "exam_level": "Exam level (National / State / University level)",
  "mode": "Mode of exam (Online / Offline / Both)"
}}

Important:
- Focus on Indian exams and education system
- Return ONLY the raw JSON object
"""

    response = _call_gemini_api(prompt)
    if "error" in response:
        return response

    text = response.get("content", "").strip()
    data = _extract_json_from_text(text)
    
    if data:
        return data
    else:
        return {
            "error": "PARSE_ERROR",
            "message": "Failed to parse AI response."
        }

def get_gemini_details(topic, mode="career", max_retries=0):
    """Backward compatibility wrapper for existing app.py code."""
    if mode == "exam":
        result = get_exam_details(topic)
        if "error" not in result:
            return {
                "exam_name": result.get("exam_name", topic),
                "purpose": result.get("purpose", ""),
                "eligibility": result.get("eligibility", ""),
                "pattern": f"Papers: {result.get('number_of_papers', 'N/A')}, Total Marks: {result.get('total_marks', 'N/A')}, Mode: {result.get('mode', 'N/A')}",
                "syllabus": result.get("subjects", ""),
                "preparation_tips": result.get("importance", ""),
                "important_dates": "Check official notification for latest dates."
            }
        return result
    else:
        result = get_career_details(topic)
        if "error" not in result:
            salary = result.get("salary", {})
            if isinstance(salary, dict):
                salary_str = f"Starting: {salary.get('starting', 'N/A')}, Average: {salary.get('average', 'N/A')}, Highest: {salary.get('highest', 'N/A')}"
            else:
                salary_str = str(salary)
            
            return {
                "career_name": result.get("career_name", topic),
                "after_10th": result.get("stream_after_10th", ""),
                "after_12th": result.get("stream_after_12th", ""),
                "exams": result.get("entrance_exams", ""),
                "course": result.get("courses", ""),
                "top_colleges": result.get("top_colleges", ""),
                "skills": result.get("skills", ""),
                "challenges": result.get("reality_check", ""),
                "duration": result.get("duration", ""),
                "degree": result.get("courses", ""),
                "salary": salary_str,
                "growth": result.get("future_scope", ""),
                "eligibility": "Refer to specific college criteria.",
                "college_type": result.get("college_type", "")
            }
        return result
