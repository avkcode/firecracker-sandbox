#!/bin/python3

import os
import requests

def get_public_repos(username):
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url)
    if response.status_code == 200:
        repos = response.json()
        return [repo['clone_url'] for repo in repos]
    else:
        print(f"Failed to fetch repositories for {username}. Status code: {response.status_code}")
        return []

def clone_repos(repo_urls, destination_dir):
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    
    for repo_url in repo_urls:
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_path = os.path.join(destination_dir, repo_name)
        
        if os.path.exists(repo_path):
            print(f"Repository {repo_name} already exists. Skipping...")
        else:
            print(f"Cloning {repo_name}...")
            os.system(f"git clone {repo_url} {repo_path}")

if __name__ == "__main__":
    github_username = input("Enter GitHub username: ")
    destination_directory = input("Enter destination directory (default: ./repos): ") or "./repos"
    
    repo_urls = get_public_repos(github_username)
    if repo_urls:
        clone_repos(repo_urls, destination_directory)
        print("All repositories have been cloned.")
    else:
        print("No repositories found or an error occurred.")
