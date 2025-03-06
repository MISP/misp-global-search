# MISP Global Search

MISP Global Search is a tool to quickly search MISP resources using full-text search. Currently the following resources are included: 

- [MISP Galaxy](https://github.com/MISP/misp-galaxy)
- [MISP Objects](https://github.com/MISP/misp-objects)
- [MISP Taxonomies](https://github.com/MISP/misp-taxonomies)

## Deploy Locally

This repo includes scripts to deploy MISP Global Search using LXD. 

### Prerequisites

1. Setup Python environment:
    ```bash
    python3 -m venv env
    ```

2. Activate the environment:
    ```bash
    source ./env/bin/activate
    ```

3. Install required packages:
    ```bash
    pip install -r requirements.txt
    ```

### Setup

1. Setup a Meilisearch instance:
    ```bash
    bash setup_meilisearch.sh
    ```

2. Index MISP Galaxy data into Meilisearch:
    > After running the `setup_meilisearch` script you have to add a GitHub personal access token to the `src/config.json` file as otherwise the index script cannot fetch all the files from GitHub due to their rate limiting. Just add `"GITHUB_PAT":"<token>"` to the file.

    ```bash
    pyhton3 index.py
    ```

3. Start webapp:
    ```bash
    bash setup_webapp.sh
    ```
    > Note: Per default the webapp will bind to localhost:8000 on your host machine

