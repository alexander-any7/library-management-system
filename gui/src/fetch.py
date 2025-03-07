import json

import requests


class DictToObject:
    def __init__(self, dictionary):
        # Ensure the input is a dictionary; if not, treat it as a regular value
        if not isinstance(dictionary, dict):
            return

        for key, value in dictionary.items():
            # Handle nested dictionaries
            if isinstance(value, dict):
                setattr(self, key, DictToObject(value))
            # Handle lists (check if items are dictionaries)
            elif isinstance(value, list):
                setattr(
                    self,
                    key,
                    [DictToObject(item) if isinstance(item, dict) else item for item in value],
                )
            # Handle all other types (strings, numbers, etc.)
            else:
                setattr(self, key, value)


class FetchHelper:
    def __init__(self):
        try:
            with open("tokens.json", "r") as f:
                data = json.load(f)
            self.ACCESS_TOKEN = data["access_token"]
            self.REFRESH_TOKEN = data["refresh_token"]
        except Exception:
            self.ACCESS_TOKEN = None
            self.REFRESH_TOKEN = None

        if not self.ACCESS_TOKEN:
            self.self_fetch_access_token()

    def self_fetch_access_token(self):
        response = requests.post(
            "http://localhost:5000/login",
            json={"email": "tlucero@example.com", "password": "password"},
        )

        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        if access_token:
            self.ACCESS_TOKEN = access_token
            self.REFRESH_TOKEN = refresh_token

            with open("tokens.json", "w") as f:
                json.dump({"access_token": access_token, "refresh_token": refresh_token}, f)

    def update_access_token(self):
        response = requests.post(
            "http://localhost:5000/refresh",
            headers={"Authorization": f"Bearer {self.REFRESH_TOKEN}"},
        )
        access_token = response.json().get("access_token")
        if access_token:
            self.ACCESS_TOKEN = access_token

            with open("tokens.json", "w") as f:
                json.dump({"access_token": access_token, "refresh_token": self.REFRESH_TOKEN}, f)

    def fetch(self, url, method="get", data=None) -> object:
        if method == "get":
            request = requests.get
        elif method == "post":
            request = requests.post
        elif method == "put":
            request = requests.put
        elif method == "delete":
            request = requests.delete
        else:
            raise ValueError("Invalid method")

        response = request(
            url, headers={"Authorization": f"Bearer {self.ACCESS_TOKEN}"}, json=data
        )
        if response.status_code == 401 and response.json().get("msg") == "Token has expired":
            self.update_access_token()
            response = request(
                url, headers={"Authorization": f"Bearer {self.ACCESS_TOKEN}"}, json=data
            )
            if response.status_code == 401:
                self.self_fetch_access_token()
                response = request(
                    url, headers={"Authorization": f"Bearer {self.ACCESS_TOKEN}"}, json=data
                )

        return DictToObject(response.json())
