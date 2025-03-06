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
    ```bash
    pyhton3 index.py
    ```

3. Start webapp:
    ```bash
    bash setup_webapp.sh
    ```


