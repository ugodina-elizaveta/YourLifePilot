import json
import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class VkApi:
    BASE_URL = "https://api.vk.com/method/"
    API_VERSION = "5.199"

    def __init__(self):
        self.token = os.getenv("VK_TOKEN")
        if not self.token:
            raise ValueError("VK_TOKEN not set in .env")

    async def _call(self, method: str, params: dict = None) -> Optional[dict]:
        params = params or {}
        params.update(
            {
                'access_token': self.token,
                'v': self.API_VERSION,
            }
        )
        url = f"{self.BASE_URL}{method}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    if 'error' in data:
                        logger.error(f"VK API error: {data['error']}")
                        return None
                    return data.get('response')
        except Exception as e:
            logger.error(f"VK API request failed: {e}")
            return None

    async def send_message(
        self, user_id: int, message: str, keyboard: Optional[dict] = None, attachment: Optional[str] = None
    ) -> Optional[int]:
        """Отправляет сообщение. Возвращает message_id или None."""
        params = {
            'user_id': user_id,
            'message': message,
            'random_id': 0,  # VK сгенерирует сам
        }
        if keyboard:
            params['keyboard'] = json.dumps(keyboard)
        if attachment:
            params['attachment'] = attachment
        result = await self._call('messages.send', params)
        # Обычно возвращает словарь с peer_id, message_id, но может быть int (ID)
        if isinstance(result, dict):
            return result.get('message_id')
        elif isinstance(result, int):
            return result
        return None

    async def get_user_info(self, user_ids: list[int]) -> Optional[list[dict]]:
        result = await self._call(
            'users.get',
            {
                'user_ids': ','.join(map(str, user_ids)),
                'fields': 'first_name,last_name',
            },
        )
        return result
