from flask import Flask, request, jsonify
from pymongo import MongoClient
import requests
from collections import defaultdict
from bson import ObjectId

app = Flask(__name__)

# MongoDB connection
MONGO_URI = "mongodb+srv://bharath2005:bharath2005@cluster0.0vibjmv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["test"]
posts_collection = db["users"]

# GitHub token and headers
GITHUB_TOKEN = "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"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# GitHub utility functions
def get_user_repos(username):
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url, headers=HEADERS)
    return response.json()

def get_repo_languages(username, repo_name):
    url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return list(response.json().keys())
    return []

@app.route('/classify', methods=['GET'])
def classify_post():
    users_id = request.args.get('users_id')
    github_username = request.args.get('github_username')  # Get GitHub username too

    if not users_id or not github_username:
        return jsonify({"error": "users_id and github_username are required"}), 400

    # Try to convert users_id to ObjectId
    try:
        object_id = ObjectId(users_id)  # This will raise an error if the ID is not a valid ObjectId
    except Exception as e:
        return jsonify({"error": f"Invalid users_id format: {str(e)}"}), 400

    # Logging the object_id to debug
    print(f"ObjectId to search in MongoDB: {object_id}")

    # Fetch the user from MongoDB
    user_data = posts_collection.find_one({"_id": object_id})

    # Logging to check if we are retrieving the correct data
    print(f"User data fetched: {user_data}")

    if not user_data:
        return jsonify({"error": "User not found"}), 404

    # Collect tech stack frequencies
    repos = get_user_repos(github_username)
    tech_stack_counter = defaultdict(int)

    for repo in repos:
        repo_name = repo['name']
        languages = get_repo_languages(github_username, repo_name)
        for lang in languages:
            tech_stack_counter[lang] += 1

    # Convert to dictionary format for MongoDB (e.g., [{"tech": "Python", "count": 5}, ...])
    tech_skills = [{"tech": tech, "count": count} for tech, count in tech_stack_counter.items()]

    # Update the user's document in the "users" collection
    posts_collection.update_one(
        {"_id": object_id},
        {"$set": {"profile.skills": tech_skills}}
    )

    return jsonify({
        "message": "Tech stack updated successfully.",
        "skills": tech_skills
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
