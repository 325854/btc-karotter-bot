import json
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Optional

import httpx


class KarotterClient:
    def __init__(self, username: str, password: str, client_type: str = "web", device_name: str = "Chrome on Linux"):
        self.username = username
        self.password = password
        self.client_type = client_type
        self.device_name = device_name
        self.device_id = str(uuid.uuid4())
        self.base_url = "https://api.karotter.com/api"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            follow_redirects=True,
            headers={"x-client-type": self.client_type, "User-Agent": "btc-karotter-bot/1.0"},
        )
        self.csrf_token: Optional[str] = None
        self.access_token: Optional[str] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        await self.client.aclose()

    async def fetch_csrf_token(self) -> str:
        resp = await self.client.get("/auth/csrf-token")
        resp.raise_for_status()
        token = resp.json()["csrfToken"]
        self.csrf_token = token
        self.client.headers["x-csrf-token"] = token
        return token

    async def login(self) -> None:
        if not self.csrf_token:
            await self.fetch_csrf_token()

        payload = {
            "identifier": self.username,
            "password": self.password,
            "deviceId": self.device_id,
            "clientType": self.client_type,
            "deviceName": self.device_name,
        }
        resp = await self.client.post("/auth/login", json=payload)
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["accessToken"]
        self.client.headers["Authorization"] = f"Bearer {self.access_token}"

    async def create_post(
        self,
        content: str,
        image_path: Optional[str] = None,
        image_alt: str = "BTC 24h price chart",
        visibility: str = "PUBLIC",
        reply_restriction: str = "EVERYONE",
        is_ai_generated: bool = False,
    ):
        data = {
            "content": content,
            "visibility": visibility,
            "replyRestriction": reply_restriction,
            "isAiGenerated": str(is_ai_generated).lower(),
        }

        files = []
        file_handle = None
        try:
            if image_path:
                path = Path(image_path)
                mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                file_handle = open(path, "rb")
                files.append(("media", (path.name, file_handle, mime_type)))
                data["mediaAlts"] = json.dumps([image_alt], ensure_ascii=False)
                data["mediaSpoilerFlags"] = json.dumps([False])
                data["mediaR18Flags"] = json.dumps([False])

            resp = await self.client.post("/posts", data=data, files=files or None)
            resp.raise_for_status()
            return resp.json()
        finally:
            if file_handle:
                file_handle.close()
