import meilisearch
import json
import requests

INDEX = "misp-galaxy"

GITHUB_OWNER = "MISP"
GITHUB_REPO = "misp-galaxy"
BRANCH = "main"
DATA_DIR = "clusters"

with open("./src/config.json", "r") as config_file:
    config = json.load(config_file)
API_KEY = config.get("MEILI_ADMIN_API_KEY")
HOST = config.get("MEILI_URL")

client = meilisearch.Client(HOST, API_KEY)


def fetch_files_from_github(owner, repo, path, branch="main"):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def load_clusters_from_github():
    print("Fetching data from GitHub repository...")
    docs = []
    file_list = fetch_files_from_github(GITHUB_OWNER, GITHUB_REPO, DATA_DIR, BRANCH)
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


def cleanup():
    client.delete_index(INDEX)


def index_documents(docs):
    client.create_index(INDEX, {"primaryKey": "uuid"})
    for doc in docs:
        client.index(INDEX).update_documents([doc])


def main():
    clusters = load_clusters_from_github()
    cleanup()
    index_documents(clusters)


if __name__ == "__main__":
    main()
