import meilisearch
import json
import requests

with open("./src/config.json", "r") as config_file:
    config = json.load(config_file)
API_KEY = config.get("MEILI_ADMIN_API_KEY")
HOST = config.get("MEILI_URL")
TOKEN = config.get("GITHUB_PAT")

client = meilisearch.Client(HOST, API_KEY)


def fetch_files_from_github(owner, repo, path, branch="main"):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    headers = {}
    headers["Authorization"] = f"token {TOKEN}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def fetch_subdir_files_from_github(owner, repo, path, branch="main"):
    all_files = []
    items = fetch_files_from_github(owner, repo, path, branch)

    for item in items:
        if item["type"] == "file":
            all_files.append(item)
        elif item["type"] == "dir":
            all_files.extend(
                fetch_subdir_files_from_github(owner, repo, item["path"], branch)
            )
    return all_files


def load_clusters_from_github():
    print("Fetching data from MISP Galaxy GitHub repository...")
    docs = []
    file_list = fetch_files_from_github("MISP", "misp-galaxy", "clusters", "main")
    for file_info in file_list:
        if file_info["name"].endswith(".json"):
            print(f"Processing {file_info['name']}")
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


def load_objects_from_github():
    print("Fetching data from MISP Objects GitHub repository...")
    docs = []
    file_list = fetch_subdir_files_from_github(
        "MISP", "misp-objects", "objects", "main"
    )
    for file_info in file_list:
        if file_info["name"].endswith(".json"):
            print(f"Processing {file_info['name']}")
            file_url = file_info["download_url"]
            file_response = requests.get(file_url)
            file_response.raise_for_status()
            try:
                doc = file_response.json()
                docs.append(doc)
            except Exception as e:
                print(f"Error processing {file_info['name']: {e}}")
    print(f"Loaded {len(docs)} documents from GitHub.")
    return docs

def load_taxonomies_from_github():
    print("Fetching data from MISP Taxonomies GitHub repository...")


def cleanup(index):
    client.delete_index(index)


def index_documents(docs, index_name, primaryKey="uuid"):
    client.create_index(index_name, {"primaryKey": primaryKey})
    for doc in docs:
        client.index(index_name).update_documents([doc])


def main():
    cleanup("misp-galaxy")
    clusters = load_clusters_from_github()
    index_documents(clusters, "misp-galaxy")
    
    cleanup("misp-objects")
    objects = load_objects_from_github()
    index_documents(objects, "misp-objects")
    
    # cleanup("misp-taxonomies")
    # taxonomies = load_taxonomies_from_github()
    # index_documents(taxonomies, "misp-taxonomies")


if __name__ == "__main__":
    main()
