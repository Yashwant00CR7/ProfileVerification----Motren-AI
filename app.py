from flask import Flask, request, jsonify
from pymongo import MongoClient
import requests
from bson import ObjectId
from collections import defaultdict

app = Flask(__name__)

# MongoDB setup
MONGO_URI = "mongodb+srv://bharath2005:bharath2005@cluster0.0vibjmv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["test"]
users_collection = db["users"]
developers_collection = db["developers"]

# GitHub headers
GITHUB_TOKEN = "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"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# Get all repos of a user
def get_user_repos(username):
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

# Get languages used in a repo
def get_repo_languages(username, repo_name):
    url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
    response = requests.get(url, headers=HEADERS)
    return list(response.json().keys()) if response.status_code == 200 else []

@app.route('/classify', methods=['GET'])
def classify_developer():
    developer_id = request.args.get("developer_id")  # _id from developers collection

    if not developer_id:
        return jsonify({"error": "developer_id is required"}), 400

    try:
        developer_object_id = ObjectId(developer_id)
    except Exception as e:
        return jsonify({"error": f"Invalid ObjectId: {str(e)}"}), 400

    # Get developer document
    developer_doc = developers_collection.find_one({"_id": developer_object_id})
    if not developer_doc:
        return jsonify({"error": "Developer not found"}), 404

    user_id = developer_doc.get("userId")
    if not user_id:
        return jsonify({"error": "userId not found in developer document"}), 400

    try:
        user_object_id = ObjectId(user_id)
    except Exception as e:
        return jsonify({"error": f"Invalid userId format: {str(e)}"}), 400

    # Get user document
    user_doc = users_collection.find_one({"_id": user_object_id})
    if not user_doc:
        return jsonify({"error": "User not found"}), 404

    # Extract GitHub username from URL
    github_url = user_doc.get("profile", {}).get("links", {}).get("github", "")
    if not github_url or "github.com/" not in github_url:
        return jsonify({"error": "GitHub URL is invalid or missing"}), 400

    github_username = github_url.split("github.com/")[-1].strip("/")

    # Get GitHub tech stack
    repos = get_user_repos(github_username)
    github_tech_stack = set()
    for repo in repos:
        repo_name = repo.get("name")
        if repo_name:
            languages = get_repo_languages(github_username, repo_name)
            github_tech_stack.update(languages)

    # Convert tech to lowercase for case-insensitive match
    github_tech_stack_lower = {lang.lower() for lang in github_tech_stack}

    # Get user's listed skills
    user_skills = user_doc.get("profile", {}).get("skills", [])
    user_skills_lower = [skill.lower() for skill in user_skills]

    # Compare profile.skills with GitHub tech stack
    matched_skills = [skill for skill in user_skills_lower if skill in github_tech_stack_lower]
    match_percentage = (len(matched_skills) / len(user_skills_lower)) * 100 if user_skills_lower else 0

    # Debug logging
    print("User Skills:", user_skills)
    print("GitHub Stack:", list(github_tech_stack))
    print("Matched Skills:", matched_skills)
    print("Match %:", match_percentage)

    if match_percentage >= 50:
        users_collection.update_one(
            {"_id": user_object_id},
            {"$set": {"role": "developer"}}
        )
        developers_collection.update_one(
            {"_id": developer_object_id},
            {"$set": {"status": "approved"}}
        )
        return jsonify({
            "message": "User verified successfully.",
            "match_percentage": match_percentage,
            "status": "approved",
            "github_stack": list(github_tech_stack),
            "user_skills": user_skills,
            "updated_role": "developer"
        }), 200
    else:
        return jsonify({
            "message": "User did not meet minimum skill match criteria.",
            "match_percentage": match_percentage,
            "status": "pending",
            "github_stack": list(github_tech_stack),
            "user_skills": user_skills
        }), 200

if __name__ == '__main__':
    app.run(debug=True)
