import re

import isodate
from app.models.recipe import (
    IngredientEntity,
    NutritionInfoEntity,
    RecipeEntity,
    StepEntity,
    UnitType,
)
from app.services.recipe_extractor import RecipeExtractorService


class RecipeParserService:
    UNIT_ABBREVIATIONS = {
        # grams-German
        "g": UnitType.grams,
        "gram": UnitType.grams,
        "gramm": UnitType.grams,
        # kilograms
        "kg": UnitType.kilograms,
        "kilogram": UnitType.kilograms,
        "kilogramm": UnitType.kilograms,
        # milligrams
        "mg": UnitType.miligrams,
        "milligram": UnitType.miligrams,
        "milligramm": UnitType.miligrams,
        # ml (milliliter)
        "ml": UnitType.milliliters,
        "milliliter": UnitType.milliliters,
        # cl
        "cl": UnitType.milliliters,
        # liters
        "l": UnitType.liters,
        "liter": UnitType.liters,
        # tablespoons / EL
        "el": UnitType.tablespoons,
        "tbsp": UnitType.tablespoons,
        "tablespoon": UnitType.tablespoons,
        "eßl": UnitType.tablespoons,
        # teaspoons / TL
        "tl": UnitType.teaspoons,
        "tsp": UnitType.teaspoons,
        "teelöffel": UnitType.teaspoons,
        # ounces
        "oz": UnitType.ounces,
        "ounce": UnitType.ounces,
        # pounds
        "lb": UnitType.pounds,
        "pound": UnitType.pounds,
        # pieces
        "stück": UnitType.pieces,
        "stk": UnitType.pieces,
        "piece": UnitType.pieces,
        "pcs": UnitType.pieces,
        # pinches
        "prise": UnitType.pinches,
        "pinches": UnitType.pinches,
        "prisen": UnitType.pinches,
        # centimeters
        "cm": UnitType.centimeters,
        "zentimeter": UnitType.centimeters,
    }

    def __init__(self) -> None:
        self.recipe_extractor_service = RecipeExtractorService()

    def extract_recipe_from_url(self, url: str):
        structured_recipe = self.recipe_extractor_service.extract_recipe_structured(url)
        return RecipeParserService.extract_recipe_from_structured_data(structured_recipe)

    @staticmethod
    def extract_recipe_from_structured_data(structured_recipe: dict):

        if not structured_recipe or "data" not in structured_recipe:
            return None
        data = structured_recipe["data"]

        # INGREDIENTS
        ingredients = []
        recipe_ingredients = (
            data.get("recipeIngredient") or data.get("ingredients") or []
        )

        for ingredient_line in recipe_ingredients:
            parsed_name, parsed_qty, parsed_unit = RecipeParserService._parse_ingredient(
                ingredient_line
            )
            ingredients.append(
                IngredientEntity(
                    name=parsed_name, quantity=parsed_qty, unit=parsed_unit
                )
            )

        # STEPS (handle HowToSection/HowToStep structure)
        steps = []
        recipe_instructions = data.get("recipeInstructions")


        step_texts = RecipeParserService._extract_step_texts(recipe_instructions)
        for text in step_texts:
            steps.append(StepEntity(ingredients=[], instruction=text))

        # NUTRITION
        nutrition = data.get("nutrition", {})
        nutrition_entity = NutritionInfoEntity(
            calories=RecipeParserService._parse_int(nutrition.get("calories", 0)),
            carbohydratesGrams=RecipeParserService._parse_float(
                nutrition.get("carbohydrateContent", 0)
            ),
            proteinGrams=RecipeParserService._parse_float(
                nutrition.get("proteinContent", 0)
            ),
            fatGrams=RecipeParserService._parse_float(nutrition.get("fatContent", 0)),
        )

        # RECIPE ENTITY
        recipe = RecipeEntity(
            name=data.get("name", ""),
            description=data.get("description", ""),
            ingredients=ingredients,
            steps=steps,
            servings=RecipeParserService._parse_int(data.get("recipeYield", 0)),
            cookingTimeMinutes=RecipeParserService._parse_duration(
                data.get("cookTime", data.get("totalTime", "0"))
            ),
            preparationTimeMinutes=RecipeParserService._parse_duration(
                data.get("prepTime", "0")
            ),
            nutritionInfo=nutrition_entity,
            imageUrl=None,
        )
        # Handle image field (could be url, list, or dict)
        img = data.get("image")
        if isinstance(img, str):
            recipe.imageUrl = img
        elif isinstance(img, list) and len(img) > 0:
            recipe.imageUrl = img[0]
        elif isinstance(img, dict) and "url" in img:
            recipe.imageUrl = img["url"]

        return recipe

    @staticmethod
    def _parse_float(val):
        try:
            if isinstance(val, (int, float)):
                return float(val)
            val = str(val).replace(",", ".")
            return float(re.findall(r"[\d,.]+", val)[0])
        except Exception:
            return 0.0

    @staticmethod
    def _parse_int(val):
        try:
            # Attempt to extract a number from string like '4 Portionen'
            if isinstance(val, (int, float)):
                return int(val)
            m = re.search(r"(\d+)", str(val))
            if m:
                return int(m.group(1))
        except Exception:
            return 0
        return 0

    @staticmethod
    def _get_unit(name):
        if not name:
            return UnitType.pieces
        name = name.lower()
        for unit in UnitType:
            if unit.value in name or unit.name.lower() in name:
                return unit
        return UnitType.pieces

    @staticmethod
    def _parse_duration(duration_str):
        # ISO 8601 duration, e.g. PT20M; fallback to int minutes if possible
        try:
            if isinstance(duration_str, (int, float)):
                return int(duration_str)
            d = isodate.parse_duration(duration_str)
            # returns timedelta or Duration
            minutes = int(d.total_seconds() // 60)
            return minutes
        except Exception:
            try:
                return int(str(duration_str).replace("PT", "").replace("M", ""))
            except Exception:
                return 0

    @staticmethod
    def _parse_ingredient(ingredient_str):
        s = ingredient_str.strip()
        # Regex handles [quantity] [unit] [ingredient], e.g. "2 EL Zucker", "1/2 TL Salz", etc
        regex = r"^([\d]+(?:[\.,\/][\d]+)?)?\s*([a-zA-ZäöüÄÖÜµß\.]+)?\s*(.+)"
        match = re.match(regex, s)
        amount = 1.0
        unit = UnitType.pieces
        name = s
        if match:
            qty_str, unit_str, raw_name = match.groups()
            # Quantity: accepts whole, decimal, or fraction
            if qty_str:
                # Handle fractions like 1/2
                if "/" in qty_str:
                    try:
                        amount = float(qty_str.split("/")[0]) / float(
                            qty_str.split("/")[1]
                        )
                    except Exception:
                        amount = 1.0
                else:
                    amount = RecipeParserService._parse_float(qty_str)
            # Unit abbreviation mapping
            if unit_str:
                lowered = unit_str.lower().replace(".", "")
                unit = RecipeParserService.UNIT_ABBREVIATIONS.get(
                    lowered, RecipeParserService._get_unit(unit_str)
                )
            # Name cleanup
            name = raw_name.strip()
            # Remove trailing (something), e.g. Gurke(n)
            name = re.sub(r"\s*\([^)]*\)$", "", name)
            name = re.sub(r"\(s\)$", "", name, flags=re.IGNORECASE).strip()
            # Fallback: never let name be empty
            if not name:
                name = s
        else:
            name = s
        return name, amount, unit

    @staticmethod
    def _extract_step_texts(instructions):
        # Recursively extract step 'text'
        result = []
        if isinstance(instructions, list):
            for entry in instructions:
                if isinstance(entry, dict):
                    if "itemListElement" in entry:  # HowToSection
                        result.extend(RecipeParserService._extract_step_texts(entry["itemListElement"]))
                    elif "text" in entry:
                        result.append(entry["text"])
                elif isinstance(entry, str):
                    result.append(entry)
        elif isinstance(instructions, dict):
            if "itemListElement" in instructions:
                result.extend(RecipeParserService._extract_step_texts(instructions["itemListElement"]))
            elif "text" in instructions:
                result.append(instructions["text"])
        elif isinstance(instructions, str):
            result.extend(
                [s.strip() for s in instructions.split("\n") if s.strip()]
            )
        return result

