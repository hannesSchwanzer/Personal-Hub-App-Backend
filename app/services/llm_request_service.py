from abc import ABC, abstractmethod
import base64
from io import BytesIO
import logging
from typing import List, Literal, Tuple
import openai

from PIL import Image
from copilot import CopilotClient, SubprocessConfig
from copilot.session import PermissionRequestResult

from app.utils.env import get_user_token_copilot, get_user_token_openrouter

logger = logging.getLogger("app.services.llm_request_service")


class LlmRequestService(ABC):
    def __init__(self):
        pass

    @abstractmethod
    async def send_request_images(
        self,
        prompt: str,
        images_with_mime_types: List[Tuple[bytes, str]],
        resize_images: bool = True,
    ) -> str | None:
        pass

    @abstractmethod
    async def send_request(self, prompt: str) -> str | None:
        pass

    @staticmethod
    def resize_image_bytes(
        image_bytes: bytes, mime_type: str, max_width: int = 1024, quality: int = 85
    ) -> bytes:
        """
        Resize and compress image to a maximum width, keeping aspect ratio, and output as JPEG or PNG bytes as appropriate.
        - If already smaller, original is kept.
        - Compression is applied if possible.
        """
        with Image.open(BytesIO(image_bytes)) as img:
            if img.width > max_width:
                wpercent = max_width / float(img.width)
                hsize = int(float(img.height) * wpercent)
                resample = Image.Resampling.LANCZOS
                img = img.resize((max_width, hsize), resample)

            output = BytesIO()
            ext = mime_type.split("/")[-1].lower()
            if ext == "jpeg" or ext == "jpg":
                img.save(output, format="JPEG", quality=quality, optimize=True)
                return output.getvalue()
            elif ext == "png":
                img.save(output, format="PNG", optimize=True)
                return output.getvalue()
            else:
                img.save(output, format="JPEG", quality=quality, optimize=True)
                return output.getvalue()


class CopilotRequestService(LlmRequestService):
    def __init__(self, model: str = "gpt-4.1"):
        super().__init__()
        self.model = model
        config = SubprocessConfig(
            env={"COPILOT_GITHUB_TOKEN": get_user_token_copilot()}
        )
        self.client = CopilotClient(config=config)
        self.started = False

    async def start_client(self):
        if not self.started:
            await self.client.start()
            self.started = True

            models = await self.client.list_models()
            model_names = [m.id for m in models]
            logger.info(f"Available models: {model_names}")
            assert (
                self.model in model_names
            ), f"Model {self.model} not found in available models: {model_names}"

    async def stop_client(self):
        if self.started:
            await self.client.stop()
            self.started = False

    async def send_request_images(
        self,
        prompt: str,
        images_with_mime_types: List[Tuple[bytes, str]],
        resize_images: bool = True,
    ) -> str | None:
        await self.start_client()
        if resize_images:
            processed_images = [
                LlmRequestService.resize_image_bytes(img[0], img[1])
                for img in images_with_mime_types
            ]
        else:
            processed_images = [img for img, _ in images_with_mime_types]

        base64_images = [
            base64.b64encode(img).decode("utf-8") for img in processed_images
        ]
        mime_types = [img[1] for img in images_with_mime_types]

        attachments = [
            {
                "type": "blob",
                "data": img,
                "mimeType": mime_type,
            }
            for img, mime_type in zip(base64_images, mime_types)
        ]

        session = await self.client.create_session(
            on_permission_request=lambda req, inv: PermissionRequestResult(
                kind="approved"
            ),
            model=self.model,
        )

        try:
            response = await session.send_and_wait(
                prompt, attachments=attachments, timeout=300
            )
            if response is None:
                return None
            text = response.data.content

            return str(text)
        finally:
            await session.destroy()

    async def send_request(self, prompt: str) -> str | None:
        session = await self.client.create_session(
            on_permission_request=lambda req, inv: PermissionRequestResult(
                kind="approved"
            ),
            model=self.model,
        )

        try:
            response = await session.send_and_wait(prompt, timeout=300)
            if response is None:
                return None
            text = response.data.content

            return str(text)
        finally:
            await session.destroy()


class OpenRouterRequestService(LlmRequestService):
    BASE_URL = "https://openrouter.ai/api/v1"
    IMAGE_MODELS = [
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/llama-nemotron-embed-vl-1b-v2:free",
        "google/gemma-3-27b-it:free",
    ]
    TEXT_MODELS = [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "tencent/hy3-preview:free",
        "inclusionai/ling-2.6-flash:free",
        "inclusionai/ling-2.6-1t:free",
        "z-ai/glm-4.5-air:free",
    ]

    def __init__(self):
        super().__init__()
        self.client = openai.OpenAI(
            api_key=get_user_token_openrouter(),
            base_url=self.BASE_URL,
        )
        self.recent_models = dict()

    async def _try_models(
        self, messages, request_type: Literal["text", "image"] = "text"
    ) -> str | None:
        """
        Try models in order until one succeeds.
        """

        def send_request_with_model(model, timeout=30):
            return self.client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=timeout,
            )

        if self.recent_models.get(request_type):
            # Try the most recently successful model first
            try:
                response = send_request_with_model(self.recent_models[request_type])
                if response and response.choices:
                    return response.choices[0].message.content
            except Exception as e:
                logging.warning(
                    f"[OpenRouter] Recent model failed: {self.recent_models[request_type]} → {e}"
                )

        last_exception = None
        models = self.IMAGE_MODELS if request_type == "image" else self.TEXT_MODELS
        for model in models:
            try:
                response = send_request_with_model(model, 150 if request_type == "image" else 30)
                if response and response.choices:
                    self.recent_models[request_type] = model
                    return response.choices[0].message.content

            except Exception as e:
                last_exception = e
                logging.warning(f"[OpenRouter] Model failed: {model} → {e}")

        logging.error(f"[OpenRouter] All models failed. Last error: {last_exception}")
        return None

    async def send_request_images(
        self,
        prompt: str,
        images_with_mime_types: List[Tuple[bytes, str]],
        resize_images: bool = True,
    ) -> str | None:
        if resize_images:
            processed_images = [
                LlmRequestService.resize_image_bytes(img[0], img[1])
                for img in images_with_mime_types
            ]
        else:
            processed_images = [img for img, _ in images_with_mime_types]

        content = [{"type": "text", "text": prompt}]
        for image_bytes, mime_type in zip(
            processed_images, [img[1] for img in images_with_mime_types]
        ):
            image_data_url = f"data:{mime_type};base64,{image_bytes.decode()}"
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_url, "detail": "auto"},
                }
            )

        messages = [
            {
                "role": "user",
                "content": content,
            }
        ]
        return await self._try_models(messages, request_type="image")

    async def send_request(self, prompt: str) -> str | None:
        messages = [{"role": "user", "content": prompt}]

        return await self._try_models(messages, request_type="text")


class AutoRequestService(LlmRequestService):
    def __init__(self):
        super().__init__()
        self.copilot_service = CopilotRequestService()
        self.openrouter_service = OpenRouterRequestService()

        self.copilot_available = True

    async def send_request_images(
        self,
        prompt: str,
        images_with_mime_types: List[Tuple[bytes, str]],
        resize_images: bool = True,
    ) -> str | None:
        if self.copilot_available:
            try:
                response = await self.copilot_service.send_request_images(
                    prompt, images_with_mime_types, resize_images
                )
            except Exception as e:
                logging.warning(f"Copilot image request raised an exception: {e}")
                response = None
            if response is not None:
                return response
            else:
                self.copilot_available = False
                logging.warning(
                    "Copilot image request failed, falling back to OpenRouter for future requests."
                )

        return await self.openrouter_service.send_request_images(
            prompt, images_with_mime_types, resize_images
        )

    async def send_request(self, prompt: str) -> str | None:
        if self.copilot_available:
            try:
                response = await self.copilot_service.send_request(prompt)
            except Exception as e:
                logging.warning(f"Copilot text request raised an exception: {e}")
                response = None

            if response is not None:
                return response
            else:
                self.copilot_available = False
                logging.warning(
                    "Copilot text request failed, falling back to OpenRouter for future requests."
                )

        return await self.openrouter_service.send_request(prompt)
