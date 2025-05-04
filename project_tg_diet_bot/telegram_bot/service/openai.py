import os
import base64
import requests
import logging.config

from omegaconf import OmegaConf

# from openai import OpenAI


logging_config = OmegaConf.to_container(OmegaConf.load("./telegram_bot/conf/logging_config.yaml"), resolve=True)

# Apply the logging configuration
logging.config.dictConfig(logging_config)

# Configure logging
logger = logging.getLogger(__name__)


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


class OpenAiService:
    def __init__(self, max_tokens: int = 1000):
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
        }
        self.max_tokens = max_tokens

    def _request(self, instruction: str, user_text: str = None, user_base64_image: str = None) -> str:

        if user_text:
            prompt = f"{instruction}\n{user_text}"
        else:
            prompt = instruction

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_tokens": self.max_tokens
        }

        if user_base64_image:
            payload["messages"][0]["content"].append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{user_base64_image}"
                    }
                }
            )

        response = requests.post(self.base_url, headers=self.headers, json=payload)

        # Check if the response code is not 200
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]

    def invoke(
            self,
            instruction: str,
            user_input_text: str = None,
            user_input_image_path: str = None,
            user_input_image_url: str = None
    ) -> str:

        if user_input_image_path:
            user_base64_image = encode_image(user_input_image_path)
        else:
            user_base64_image = None

        response = self._request(instruction, user_input_text, user_base64_image)

        return response


class MockOpenAiService:
    def __init__(self, instruction: str):
        self.instruction = instruction

    def invoke(
            self,
            user_input_text: str = None,
            user_input_image_base64: str = None,
            user_input_image_url: str = None
    ) -> str:
        logger.info(f"Getting image description for image: {user_input_text}")
        return f"Тестовое описание изображения {user_input_text}"
