import meilisearch
import json
import requests
import os
import subprocess
import argparse

with open("./src/config.json", "r") as config_file:
    config = json.load(config_file)
API_KEY = config.get("MEILI_ADMIN_API_KEY")
HOST = config.get("MEILI_URL")

client = meilisearch.Client(HOST, API_KEY)

# ============================
# GitHub API functions
# ============================


def fetch_files_from_github(owner, repo, path, token, branch="main"):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def fetch_subdir_files_from_github(owner, repo, path, token, branch="main"):
    all_files = []
    items = fetch_files_from_github(owner, repo, path, token, branch)
    for item in items:
        if item["type"] == "file":
            all_files.append(item)
        elif item["type"] == "dir":
            all_files.extend(
                fetch_subdir_files_from_github(owner, repo, item["path"], branch)
            )
    return all_files


def load_clusters_from_github(token):
    print("Fetching data from MISP Galaxy GitHub repository (API mode)...")
    docs = []
    file_list = fetch_files_from_github(
        "MISP", "misp-galaxy", "clusters", token, "main"
    )
    for file_info in file_list:
        if file_info["name"].endswith(".json"):
            file_url = file_info["download_url"]
            galaxy = file_info["name"].removesuffix(".json")
            file_response = requests.get(file_url)
            file_response.raise_for_status()
            try:
                doc = file_response.json()
                for cluster in doc["values"]:
                    cluster["galaxy"] = galaxy
                    docs.append(cluster)
            except Exception as e:
                print(f"Error processing {file_info['name']}: {e}")
    print(f"Loaded {len(docs)} documents from GitHub.")
    return docs


def load_objects_from_github(token):
    print("Fetching data from MISP Objects GitHub repository (API mode)...")
    docs = []
    file_list = fetch_subdir_files_from_github(
        "MISP", "misp-objects", "objects", token, "main"
    )
    for file_info in file_list:
        if file_info["name"].endswith(".json"):
            file_url = file_info["download_url"]
            file_response = requests.get(file_url)
            file_response.raise_for_status()
            try:
                doc = file_response.json()
                docs.append(doc)
            except Exception as e:
                print(f"Error processing {file_info['name']}: {e}")
    print(f"Loaded {len(docs)} documents from GitHub.")
    return docs


def load_taxonomies_from_github(token):
    print("Fetching data from MISP Taxonomies GitHub repository (API mode)...")
    docs = []
    file_list = fetch_subdir_files_from_github(
        "MISP", "misp-taxonomies", "", token, "main"
    )
    for file_info in file_list:
        if file_info["name"] == "machinetag.json":
            file_url = file_info["download_url"]
            file_response = requests.get(file_url)
            file_response.raise_for_status()
            try:
                doc = file_response.json()
                ns = doc["namespace"]
                for predicate in doc["predicates"]:
                    predicate["namespace"] = ns
                    docs.append(predicate)
                try:
                    for value in doc["values"]:
                        pred = value["predicate"]
                        for entry in value["entry"]:
                            entry["namespace"] = ns
                            entry["predicate"] = pred
                            docs.append(entry)
                except Exception:
                    pass
                docs.append(doc)
            except Exception as e:
                print(f"Error processing {file_info['name']}: {e}")
    print(f"Loaded {len(docs)} documents from GitHub.")
    return docs


# ============================
# Local mode functions
# ============================


def clone_repo(owner, repo, local_path, branch="main"):
    if not os.path.exists(local_path):
        print(f"Cloning repository {repo} into {local_path}...")
        subprocess.run(
            [
                "git",
                "clone",
                "--branch",
                branch,
                f"https://github.com/{owner}/{repo}.git",
                local_path,
            ],
            check=True,
        )
    else:
        print(
            f"Repository {repo} already exists at {local_path}. Pulling latest changes..."
        )
        subprocess.run(["git", "-C", local_path, "pull"], check=True)


def load_clusters_from_local():
    print("Fetching data from local MISP Galaxy repository...")
    docs = []
    repo_dir = "./data/misp-galaxy"
    clusters_dir = os.path.join(repo_dir, "clusters")
    if not os.path.exists(clusters_dir):
        print(f"Directory {clusters_dir} does not exist.")
        return docs
    for filename in os.listdir(clusters_dir):
        if filename.endswith(".json"):
            galaxy = filename.removesuffix(".json")
            file_path = os.path.join(clusters_dir, filename)
            try:
                with open(file_path, "r") as f:
                    doc = json.load(f)
                    for cluster in doc["values"]:
                        cluster["galaxy"] = galaxy
                        docs.append(cluster)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    print(f"Loaded {len(docs)} documents from local repository.")
    return docs


def load_objects_from_local():
    print("Fetching data from local MISP Objects repository...")
    docs = []
    repo_dir = "./data/misp-objects"
    objects_dir = os.path.join(repo_dir, "objects")
    if not os.path.exists(objects_dir):
        print(f"Directory {objects_dir} does not exist.")
        return docs
    for root, dirs, files in os.walk(objects_dir):
        for filename in files:
            if filename.endswith(".json"):
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, "r") as f:
                        doc = json.load(f)
                        docs.append(doc)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    print(f"Loaded {len(docs)} documents from local repository.")
    return docs


def load_taxonomies_from_local():
    print("Fetching data from local MISP Taxonomies repository...")
    docs = []
    repo_dir = "./data/misp-taxonomies"
    for root, dirs, files in os.walk(repo_dir):
        for filename in files:
            if filename == "machinetag.json":
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, "r") as f:
                        doc = json.load(f)
                    ns = doc["namespace"]
                    for predicate in doc["predicates"]:
                        predicate["namespace"] = ns
                        docs.append(predicate)
                    try:
                        for value in doc["values"]:
                            pred = value["predicate"]
                            for entry in value["entry"]:
                                entry["namespace"] = ns
                                entry["predicate"] = pred
                                docs.append(entry)
                    except Exception:
                        pass
                    docs.append(doc)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    if not docs:
        print("machinetag.json not found in local repository.")
    else:
        print(f"Loaded {len(docs)} documents from local repository.")
    return docs


# ============================
# Indexing function
# ============================


def index_documents(docs, index_name, primaryKey="uuid"):
    for doc in docs:
        client.index(index_name).update_documents([doc])


# ============================
# Main functions for each mode
# ============================


def main_api():
    token = config.get("GITHUB_PAT")
    clusters = load_clusters_from_github(token)
    index_documents(clusters, "misp-galaxy")

    objects = load_objects_from_github(token)
    index_documents(objects, "misp-objects")

    taxonomies = load_taxonomies_from_github(token)
    index_documents(taxonomies, "misp-taxonomies")
    client.index("misp-taxonomies").update_filterable_attributes(
        ["version", "namespace", "predicate"]
    )
    client.index("misp-galaxy").update_filterable_attributes(["galaxy"])


def main_local():
    clone_repo("MISP", "misp-galaxy", "./data/misp-galaxy", "main")
    clone_repo("MISP", "misp-objects", "./data/misp-objects", "main")
    clone_repo("MISP", "misp-taxonomies", "./data/misp-taxonomies", "main")

    clusters = load_clusters_from_local()
    index_documents(clusters, "misp-galaxy")

    objects = load_objects_from_local()
    index_documents(objects, "misp-objects")

    taxonomies = load_taxonomies_from_local()
    index_documents(taxonomies, "misp-taxonomies")
    client.index("misp-taxonomies").update_filterable_attributes(
        ["version", "namespace", "predicate"]
    )
    client.index("misp-galaxy").update_filterable_attributes(["galaxy"])


def main_update():
    clone_repo("MISP", "misp-galaxy", "./data/misp-galaxy", "main")
    clone_repo("MISP", "misp-objects", "./data/misp-objects", "main")
    clone_repo("MISP", "misp-taxonomies", "./data/misp-taxonomies", "main")

    clusters = load_clusters_from_local()
    index_documents(clusters, "misp-galaxy_new")

    objects = load_objects_from_local()
    index_documents(objects, "misp-objects_new")

    taxonomies = load_taxonomies_from_local()
    index_documents(taxonomies, "misp-taxonomies_new")
    client.index("misp-taxonomies_new").update_filterable_attributes(
        ["version", "namespace", "predicate"]
    )

    client.swap_indexes(
        [
            {"indexes": ["misp-galaxy", "misp-galaxy_new"]},
            {"indexes": ["misp-objects", "misp-objects_new"]},
            {"indexes": ["misp-taxonomies", "misp-taxonomies_new"]},
        ]
    )

    client.index("misp-galaxy_new").delete()
    client.index("misp-objects_new").delete()
    client.index("misp-taxonomies_new").delete()


# ============================
# Argument parsing and entry point
# ============================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Index MISP data from GitHub (API mode) or local repositories (local mode)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--api", action="store_true", help="Fetch files using the GitHub API"
    )
    group.add_argument(
        "--local",
        action="store_true",
        help="Clone repositories locally and load files from disk",
    )
    group.add_argument(
        "--update",
        action="store_true",
        help="Update indexes during production from local files cloning repositories",
    )
    args = parser.parse_args()

    if args.api:
        main_api()
    elif args.local:
        main_local()
    elif args.update:
        main_update()
