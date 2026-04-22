import base64
import logging
import re
from typing import List, Optional, Tuple
from copilot import CopilotClient
from copilot.session import PermissionRequestResult
from app.models.recipe import RecipeEntity
import json

logger = logging.getLogger("app.services.recipe_generator")

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


class RecipeGeneratorService:
    def __init__(self, model: str = "gpt-4.1"):
        self.model = model
        self.client = CopilotClient()
        self.started = False

    async def start_client(self):
        if not self.started:
            await self.client.start()
            self.started = True

            models = await self.client.list_models()
            model_names = [m.id for m in models]
            logger.info(f"Available models: {model_names}")
            assert self.model in model_names, f"Model {self.model} not found in available models: {model_names}"

    async def stop_client(self):
        if self.started:
            await self.client.stop()
            self.started = False

    async def generate_recipe_from_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None
    ):
        await self.start_client()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        session = await self.client.create_session(
            on_permission_request=lambda req, inv: PermissionRequestResult(
                kind="approved"
            ),
            model=self.model,
        )
        try:
            json_prompt = self._create_prompt_single_image(
                input_language=input_language,
                output_language=output_language
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
                timeout=300  # seconds
            )
            recipe = self._parse_response(response)
            return recipe

        finally:
            await session.destroy()

    async def generate_recipe_from_images(self, images_with_mime_types: List[Tuple[bytes, str]], input_language: Optional[str] = None, output_language: Optional[str] = None):
        await self.start_client()

        base64_images = [base64.b64encode(img[0]).decode("utf-8") for img in images_with_mime_types]
        mime_types = [img[1] for img in images_with_mime_types]
        session = await self.client.create_session(
            on_permission_request=lambda req, inv: PermissionRequestResult(
                kind="approved"
            ),
            model=self.model,
        )
        try:
            json_prompt = self._create_prompt_images(
                input_language=input_language,
                output_language=output_language
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
                json_prompt,
                attachments=attachments,
                timeout=300
            )
            recipe = self._parse_response(response)
            return recipe

        finally:
            await session.destroy()

    def _parse_response(self, response):
        if response is None or response.data is None:
            raise ValueError("No response data from LLM API.")
        text = response.data.content

        text = extract_json_text(text)
        text = str(text)

        # Try to parse and validate the output to the model
        try:
            data = json.loads(text)
        except Exception:
            raise ValueError(f"LLM did not return valid JSON: {text}")

        # Normalize units to fall back to default if not valid.
        def normalize_units(data):
            from app.models.recipe import UnitType
            if isinstance(data, dict) and 'ingredients' in data:
                allowed_units = set(item.value for item in UnitType)
                for ingredient in data['ingredients']:
                    unit = ingredient.get('unit')
                    if unit not in allowed_units:
                        logger.warning(f"Unknown unit '{unit}' found. Falling back to 'pieces'.")
                        ingredient['unit'] = 'pieces'
            return data


        try:
            data = normalize_units(data)
            recipe = RecipeEntity.model_validate(data)
        except Exception as e:
            raise ValueError(f"Invalid recipe structure: {e}\nReceived: {data}")
        return recipe

    def _create_prompt_single_image(
        self,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None
    ):
        json_schema = json.dumps(RecipeEntity.model_json_schema(), indent=2)
        input_language_line = f"The recipe is written in {input_language}." if input_language else "Detect the language of the recipe."
        output_language_line = f"Your output must be in {output_language}." if output_language else "Output the recipe in the same language as the input."
        json_prompt = f"""You will see an image of a recipe. {input_language_line} {output_language_line}

Extract all information from the image and generate a full recipe that exactly matches the JSON schema provided below.

Please follow these rules:
- Output only valid, raw JSON—no explanations, preamble, markdown, or code blocks.
- Use the provided JSON schema; do not add, omit, or rename any fields.
- If a unit in the recipe is not part of the schema, convert it to a valid one.
- For ingredients that contain preparation steps (e.g., “1 diced onion”), extract as “1 piece onion” in the ingredients, and add a recipe step: “Dice the onion.”
- If instructions mention ingredients or amounts missing from the ingredient list (e.g., adding 100 ml water), add them to the ingredients.
- If there are multiple recipes, extract the first one
- Percent values must be represented as decimal numbers between 0 and 1.

Here is the JSON Schema you must adhere to (do not change its field names or add new enum types):\n\n{json_schema}\n\n"""

        return json_prompt

    def _create_prompt_images(
        self,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None
    ):
        json_schema = json.dumps(RecipeEntity.model_json_schema(), indent=2)
        input_language_line = f"The recipe is written in {input_language}." if input_language else "Detect the language of the recipe."
        output_language_line = f"Your output must be in {output_language}." if output_language else "Output the recipe in the same language as the input."
        json_prompt = f"""You will see multiple images of one recipe. {input_language_line} {output_language_line}

Extract all information from the images and generate a full recipe that exactly matches the JSON schema provided below.

Please follow these rules:
- Output only valid, raw JSON—no explanations, preamble, markdown, or code blocks.
- Use the provided JSON schema; do not add, omit, or rename any fields.
- If a unit in the recipe is not part of the schema, convert it to a valid one.
- For ingredients that contain preparation steps (e.g., “1 diced onion”), extract as “1 piece onion” in the ingredients, and add a recipe step: “Dice the onion.”
- If instructions mention ingredients or amounts missing from the ingredient list (e.g., adding 100 ml water), add them to the ingredients.
- If there are multiple recipes, extract the first one
- Percent values must be represented as decimal numbers between 0 and 1.

Here is the JSON Schema you must adhere to (do not change its field names or add new enum types):\n\n{json_schema}\n\n"""

        return json_prompt
