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

    You can use the `index.py` file to automatically index Meilisearch with the data from the sources above. You can choose if you want to fetch the data from the GitHub API or clone the corresponding repos locally:

    **Locally**:
    ```bash
    python3 index.py --local
    ```

    **GitHub API**:
    ```bash
    pyhton3 index.py --api
    ```

    > Note: You need to add a GitHub personal access token to the `src/config.json` file in order to fetch all the files from GitHub due to their rate limiting. Just add `"GITHUB_PAT":"<token>"` to the file.


3. Start webapp:
    ```bash
    bash setup_webapp.sh
    ```
    > Note: Per default the webapp will bind to localhost:8000 on your host machine

### Update

To update the data in Meilisearch you can run the index script with the `--update` flag:

```bash
pyhton3 index.py --update
```
