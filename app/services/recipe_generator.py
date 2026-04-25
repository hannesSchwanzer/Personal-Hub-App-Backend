import logging
from typing import List, Optional, Tuple
from app.models.recipe import RecipeEntity, UnitType
import json
from app.services.llm_request_service import AutoRequestService

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

    def __init__(self):
        self.recipe_extractor_service = RecipeExtractorService()
        self.llm_request_service = AutoRequestService()

    async def generate_recipe_from_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        input_language: Optional[str] = None,
        output_language: Optional[str] = None,
        resize: bool = True,
    ):
        json_prompt = self._create_prompt_single_image(
            input_language=input_language, output_language=output_language
        )
        response = await self.llm_request_service.send_request_images(prompt=json_prompt, images_with_mime_types=[(image_bytes, mime_type)], resize_images=resize)
        recipe = self._parse_response(response)
        return recipe

    async def generate_recipe_from_images(
        self,
        images_with_mime_types: List[Tuple[bytes, str]],
        input_language: Optional[str] = None,
        output_language: Optional[str] = None,
        resize: bool = True,
    ):
        json_prompt = self._create_prompt_images(
            input_language=input_language, output_language=output_language
        )
        response = await self.llm_request_service.send_request_images(prompt=json_prompt, images_with_mime_types=images_with_mime_types, resize_images=resize)
        recipe = self._parse_response(response)
        return recipe

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
        json_prompt = self._create_prompt_recipe_text(
            recipe_text=recipe_text,
            input_language=input_language,
            output_language=output_language,
        )

        response = await self.llm_request_service.send_request(prompt=json_prompt)
        recipe = self._parse_response(response)
        return recipe

    def _parse_response(self, response):
        if response is None:
            raise ValueError("No response data from LLM API.")

        text = RecipeGeneratorService.extract_json_text(response)
        text = str(text)

        # Try to parse and validate the output to the model
        try:
            data = json.loads(text)
        except Exception:
            raise ValueError(f"LLM did not return valid JSON: {text}")

        # Normalize units to fall back to default if not valid.
        def normalize_units(data):
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
