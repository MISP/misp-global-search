import json
import requests
from time import sleep
from index import main_update

APP_PATH = "/opt/misp-global-search"


class Repo:
    def __init__(self, id, mode):
        self.id = id
        self.mode = mode
        self.last_seen_update = None

    def check_for_updates(self):
        latest_update = self.get_latest_update()
        if latest_update and (latest_update != self.last_seen_update):
            print(f"Found new update for {self.id}")
            self.last_seen_update = latest_update
            self.save_state()
            return True
        return False

    def get_latest_update(self):
        print(f"Fetching {self.mode} for {self.id}")
        url = f"https://api.github.com/repos/{self.id}/{self.mode}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()[0]["sha"]
        else:
            print(f"Failed to fetch {self.mode} for {self.id}")
            return None

    def save_state(self):
        try:
            with open(f"{APP_PATH}/systemd/state.json", "r") as file:
                try:
                    states = json.load(file)
                except json.JSONDecodeError:
                    states = {}
        except FileNotFoundError:
            states = {}

        states[self.id] = self.last_seen_update

        with open(f"{APP_PATH}/systemd/state.json", "w") as file:
            json.dump(states, file)

    def load_state(self):
        try:
            with open(f"{APP_PATH}/systemd/state.json", "r") as file:
                try:
                    states = json.load(file)
                except json.JSONDecodeError:
                    states = {}
        except FileNotFoundError:
            states = {}

        self.last_seen_update = states.get(self.id, None)


def update_index():
    print("Perform update...")
    main_update()


def main():
    repos = []
    repos.append(Repo("MISP/misp-galaxy", "commits"))
    repos.append(Repo("MISP/misp-objects", "commits"))
    repos.append(Repo("MISP/misp-taxonomies", "commits"))

    for repo in repos:
        repo.load_state()

    while True:
        update = False
        for repo in repos:
            if repo.check_for_updates():
                update = True
        if update:
            update_index()
        sleep(600)


if __name__ == "__main__":
    main()
