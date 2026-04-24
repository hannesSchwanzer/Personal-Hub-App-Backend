import base64
import logging
from typing import List, Optional, Tuple
from copilot import CopilotClient
from copilot.session import PermissionRequestResult
from app.models.recipe import RecipeEntity
import json
from io import BytesIO
from PIL import Image
from app.models.recipe import RecipeEntity


from app.services.recipe_extractor import RecipeExtractorService

logger = logging.getLogger("app.services.recipe_generator")


class RecipeGeneratorService:
    RECIPE_RULES = f"""Please follow these rules:
- Output only valid, raw JSON—no explanations, preamble, markdown, or code blocks.
- Use the provided JSON schema; do not add, omit, or rename any fields.
- If a unit in the recipe is not part of the schema, convert it to a valid one.
- For ingredients that contain preparation steps (e.g., “1 diced onion”), extract as “1 piece onion” in the ingredients, and add a recipe step: “Dice the onion.”
- If instructions mention ingredients or amounts missing from the ingredient list (e.g., adding 100 ml water), add them to the ingredients.
- Percent values must be represented as decimal numbers between 0 and 1.

Here is the JSON Schema you must adhere to (do not change its field names or add new enum types):\n{json.dumps(RecipeEntity.model_json_schema(), indent=2)}
"""

    def __init__(self, model: str = "gpt-4.1"):
        self.model = model
        self.client = CopilotClient()
        self.started = False
        self.recipe_extractor_service = RecipeExtractorService()

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

    async def generate_recipe_from_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None,
        resize: bool = True,
    ):
        await self.start_client()
        if resize:
            processed_bytes = RecipeGeneratorService.resize_image_bytes(
                image_bytes, mime_type
            )
        else:
            processed_bytes = image_bytes
        base64_image = base64.b64encode(processed_bytes).decode("utf-8")
        session = await self.client.create_session(
            on_permission_request=lambda req, inv: PermissionRequestResult(
                kind="approved"
            ),
            model=self.model,
        )
        try:
            json_prompt = self._create_prompt_single_image(
                input_language=input_language, output_language=output_language
            )
            logger.info("Sending prompt to LLM API...")

            response = await session.send_and_wait(
                json_prompt,
                attachments=[
                    {
                        "type": "blob",
                        "data": base64_image,
                        "mimeType": mime_type,
                    }
                ],
                timeout=300,  # seconds
            )
            recipe = self._parse_response(response)
            return recipe

        finally:
            await session.destroy()

    async def generate_recipe_from_images(
        self,
        images_with_mime_types: List[Tuple[bytes, str]],
        input_language: Optional[str] = None,
        output_language: Optional[str] = None,
        resize: bool = True,
    ):
        await self.start_client()

        if resize:
            processed_images = [
                RecipeGeneratorService.resize_image_bytes(img[0], img[1])
                for img in images_with_mime_types
            ]
        else:
            processed_images = [img for img, _ in images_with_mime_types]
        base64_images = [
            base64.b64encode(img).decode("utf-8") for img in processed_images
        ]
        mime_types = [img[1] for img in images_with_mime_types]
        session = await self.client.create_session(
            on_permission_request=lambda req, inv: PermissionRequestResult(
                kind="approved"
            ),
            model=self.model,
        )
        try:
            json_prompt = self._create_prompt_images(
                input_language=input_language, output_language=output_language
            )
            logger.info("Sending prompt with multiple images to LLM API...")

            attachments = [
                {
                    "type": "blob",
                    "data": img,
                    "mimeType": mime_type,
                }
                for img, mime_type in zip(base64_images, mime_types)
            ]
            response = await session.send_and_wait(
                json_prompt, attachments=attachments, timeout=300
            )
            recipe = self._parse_response(response)
            return recipe

        finally:
            await session.destroy()

    async def generate_recipe_from_url(
        self,
        url: str,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None,
    ):
        recipe_text = self.recipe_extractor_service.extract_recipe_auto(url)

        recipe = await self.generate_recipe_from_str(
            recipe_text=str(recipe_text),
            input_language=input_language,
            output_language=output_language,
        )
        return recipe

    async def generate_recipe_from_str(
        self,
        recipe_text: str,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None,
    ):
        await self.start_client()

        session = await self.client.create_session(
            on_permission_request=lambda req, inv: PermissionRequestResult(
                kind="approved"
            ),
            model=self.model,
        )
        try:
            json_prompt = self._create_prompt_recipe_text(
                recipe_text=recipe_text,
                input_language=input_language,
                output_language=output_language,
            )
            logger.info("Sending prompt with Text to LLM API...")

            response = await session.send_and_wait(json_prompt)
            recipe = self._parse_response(response)
            return recipe

        finally:
            await session.destroy()

    def _parse_response(self, response):
        if response is None or response.data is None:
            raise ValueError("No response data from LLM API.")
        text = response.data.content

        text = RecipeGeneratorService.extract_json_text(text)
        text = str(text)

        # Try to parse and validate the output to the model
        try:
            data = json.loads(text)
        except Exception:
            raise ValueError(f"LLM did not return valid JSON: {text}")

        # Normalize units to fall back to default if not valid.
        def normalize_units(data):
            from app.models.recipe import UnitType

            if isinstance(data, dict) and "ingredients" in data:
                allowed_units = set(item.value for item in UnitType)
                for ingredient in data["ingredients"]:
                    unit = ingredient.get("unit")
                    if unit not in allowed_units:
                        logger.warning(
                            f"Unknown unit '{unit}' found. Falling back to 'pieces'."
                        )
                        ingredient["unit"] = "pieces"
            return data

        try:
            data = normalize_units(data)
            recipe = RecipeEntity.model_validate(data)
        except Exception as e:
            raise ValueError(f"Invalid recipe structure: {e}\nReceived: {data}")
        return recipe

    def _input_output_language_lines(
        self, input_language: Optional[str], output_language: Optional[str]
    ):
        input_language_line = (
            f"The recipe is written in {input_language}."
            if input_language
            else "Detect the language of the recipe."
        )
        output_language_line = (
            f"Your output must be in {output_language}."
            if output_language
            else "Output the recipe in the same language as the input."
        )
        return input_language_line, output_language_line

    def _create_prompt_single_image(
        self,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None,
    ):
        input_language_line, output_language_line = self._input_output_language_lines(
            input_language, output_language
        )
        json_prompt = f"""You will see an image of a recipe. {input_language_line} {output_language_line}

Extract all information from the image and generate a full recipe that exactly matches the JSON schema provided below.

{self.RECIPE_RULES}"""

        return json_prompt

    def _create_prompt_images(
        self,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None,
    ):
        input_language_line, output_language_line = self._input_output_language_lines(
            input_language, output_language
        )
        json_prompt = f"""You will see multiple images of one recipe. {input_language_line} {output_language_line}

Extract all information from the images and generate a full recipe that exactly matches the JSON schema provided below.

{self.RECIPE_RULES}"""

        return json_prompt

    def _create_prompt_recipe_text(
        self,
        recipe_text: str,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None,
    ):
        input_language_line = (
            f"The recipe is written in {input_language}."
            if input_language
            else "Detect the language of the recipe."
        )
        output_language_line = (
            f"Your output must be in {output_language}."
            if output_language
            else "Output the recipe in the same language as the input."
        )
        json_prompt = f"""You will extract a recipe from a text. {input_language_line} {output_language_line}

Extract all information from the text and generate a full recipe that exactly matches the JSON schema provided below.

{self.RECIPE_RULES}

Here is the recipe:\n{recipe_text}"""

        return json_prompt

    @staticmethod
    def extract_json_text(input_text):
        # Handles cases where text may be wrapped in triple backticks (optionally with 'json')
        lines = input_text.strip().splitlines()

        def starts_json_block(line):
            # Accepts lines that start with ``` or ```json (case-insensitive, extra whitespace ignored)
            lstr = line.strip().lower()
            return lstr.startswith("```json") or lstr == "```"

        if (
            len(lines) >= 2
            and starts_json_block(lines[0])
            and lines[-1].strip().startswith("```")
        ):
            # Remove the starting and ending code block lines
            return "\n".join(lines[1:-1]).strip()
        return input_text

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
                # For PNG, save with optimize
                img.save(output, format="PNG", optimize=True)
                return output.getvalue()
            else:
                # Default fallback to JPEG
                img.save(output, format="JPEG", quality=quality, optimize=True)
                return output.getvalue()
