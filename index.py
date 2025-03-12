import meilisearch
import json
import os
import subprocess
import argparse

with open("./src/config.json", "r") as config_file:
    config = json.load(config_file)
API_KEY = config.get("MEILI_ADMIN_API_KEY")
HOST = config.get("MEILI_URL")

client = meilisearch.Client(HOST, API_KEY)

# ============================
# Cloning functions
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


def test_galaxy_deprecated(file):
    galaxy_dir = "./data/misp-galaxy/galaxies"
    file_path = os.path.join(galaxy_dir, file)
    if not os.path.exists(file_path):
        return True
    try:
        with open(file_path, "r") as f:
            galaxy = json.load(f)
            if galaxy["namespace"] == "deprecated":
                return True
            return False
    except Exception as e:
        print(f"Could not read file {file_path}: {e}")
        return True


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
            if test_galaxy_deprecated(filename):
                continue
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
    client.index("misp-galaxy").update_filterable_attributes(["galaxy"])

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


def main_clean():
    indexes = client.get_indexes()
    for index in indexes["results"]:
        index.delete()


# ============================
# Argument parsing and entry point
# ============================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index MISP data from GitHub")
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--index",
        action="store_true",
        help="Clone repositories locally and index Meilisearch",
    )
    group.add_argument(
        "--update",
        action="store_true",
        help="Update indexes during production from local files cloning repositories",
    )
    group.add_argument(
        "--clean", action="store_true", help="Clean all indexes on Meilisearch"
    )
    args = parser.parse_args()

    if args.index:
        main_local()
    elif args.update:
        main_update()
    elif args.clean:
        main_clean()
