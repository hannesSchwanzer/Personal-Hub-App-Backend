import logging
from typing import Annotated, List
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.recipe import RecipeEntity, IngredientEntity, StepEntity, StepIngredientEntity, NutritionInfoEntity
from app.services.recipe_generator import RecipeGeneratorService

router = APIRouter(prefix="/recipe", tags=["recipe"])
service = RecipeGeneratorService()

logger = logging.getLogger(__name__)

# @router.post("/generate-recipe", response_model=RecipeEntity)
# async def generate_recipe(
#     file: UploadFile = File(...),
#     input_language: str | None = None,
#     output_language: str | None = None
# ):
#     if not (file.content_type and file.content_type.startswith("image/")):
#         raise HTTPException(status_code=400, detail="Only image files are allowed.")
#     image_bytes = await file.read()
#     logger.info(file.content_type)
#     recipe = await service.generate_recipe_from_image(
#         image_bytes, file.content_type,
#         input_language=input_language, output_language=output_language
#     )
#     return recipe


@router.post("/generate-recipe", response_model=RecipeEntity)
async def generate_recipe(
    files: List[UploadFile] = File(...),
    input_language: str | None = None,
    output_language: str | None = None,
):
    logger.info(
        f"/generate-recipe request received. input_language=%r, output_language=%r",
        input_language,
        output_language,
    )

    # Log status of files
    if not files:
        logger.info("No files uploaded.")
    else:
        logger.info(f"Number of files uploaded: {len(files)}")

    image_files = []
    for idx, file in enumerate(files):
        if not (file.content_type and file.content_type.startswith("image/")):
            logger.warning(f"File {idx} has invalid content_type: {file.content_type}")
            raise HTTPException(
                status_code=400, detail="All uploaded files must be images."
            )
        image_bytes = await file.read()

        image_files.append((image_bytes, file.content_type))

    logger.info(f"mime types of uploaded files: {[file.content_type for file in files]}")

    if len(image_files) == 0:
        raise HTTPException(status_code=400, detail="No valid image files uploaded.")
    elif len(image_files) == 1:
        recipe = await service.generate_recipe_from_image(
            image_files[0][0],
            image_files[0][1],
            input_language=input_language,
            output_language=output_language,
        )
    else:
        recipe = await service.generate_recipe_from_images(
            image_files, input_language=input_language, output_language=output_language
        )
    return recipe


@router.post("/generate-recipe-dummy", response_model=RecipeEntity)
async def generate_recipe_dummy(
    files: List[UploadFile] = File(...),
    input_language: str | None = None,
    output_language: str | None = None,
):
    """
    Dummy endpoint for /generate-recipe-dummy that ignores input and returns a hardcoded RecipeEntity.
    """
    # Build IngredientEntity list
    ingredients = [
        IngredientEntity(name="Pflanzenöl", quantity=3.0, unit="tablespoons"),
        IngredientEntity(name="Senfkörner", quantity=1.0, unit="teaspoons"),
        IngredientEntity(name="Curryblätter", quantity=2.0, unit="pieces"),
        IngredientEntity(name="Bockshornsamen", quantity=4.0, unit="pieces"),
        IngredientEntity(name="Zwiebeln", quantity=2.0, unit="pieces"),
        IngredientEntity(name="frischer Ingwer", quantity=3.0, unit="centimeters"),
        IngredientEntity(name="Knoblauchzehen", quantity=3.0, unit="pieces"),
        IngredientEntity(name="grüne Chilischoten", quantity=2.0, unit="pieces"),
        IngredientEntity(name="Tomaten", quantity=4.0, unit="pieces"),
        IngredientEntity(name="Möhre", quantity=1.0, unit="pieces"),
        IngredientEntity(name="gemahlener Koriander", quantity=0.75, unit="teaspoons"),
        IngredientEntity(name="gemahlene Kurkuma", quantity=1.0, unit="pieces"),
        IngredientEntity(name="rotes Chilipulver", quantity=0.5, unit="teaspoons"),
        IngredientEntity(name="gemahlener Kreuzkümmel", quantity=0.75, unit="teaspoons"),
        IngredientEntity(name="Garam masala", quantity=1.5, unit="teaspoons"),
        IngredientEntity(name="rote Paprikaschote", quantity=1.0, unit="pieces"),
        IngredientEntity(name="grüne Bohnen", quantity=75.0, unit="grams"),
        IngredientEntity(name="Wachsbohnen aus der Dose", quantity=400.0, unit="grams"),
        IngredientEntity(name="gehackte Korianderblätter", quantity=2.0, unit="tablespoons"),
        IngredientEntity(name="Wasser", quantity=300.0, unit="milliliters"),
    ]

    # Build StepEntity list
    steps = [
        StepEntity(
            ingredients=[
                StepIngredientEntity(name="Pflanzenöl", quantityPercent=100.0),
                StepIngredientEntity(name="Senfkörner", quantityPercent=100.0),
                StepIngredientEntity(name="Curryblätter", quantityPercent=100.0),
                StepIngredientEntity(name="Bockshornsamen", quantityPercent=100.0),
            ],
            instruction="Das Pflanzenöl in einem Karahi (indische Metallpfanne) oder Wok erhitzen. Senfkörner, Curryblätter und Bockshornsamen hineingeben. Nach etwa 30 Sekunden duften die Gewürze nussig."
        ),
        StepEntity(
            ingredients=[StepIngredientEntity(name="Zwiebeln", quantityPercent=100.0)],
            instruction="Die Zwiebeln hinzufügen und bei schwacher Hitze etwa 10 Minuten anschwitzen."
        ),
        StepEntity(
            ingredients=[
                StepIngredientEntity(name="frischer Ingwer", quantityPercent=100.0),
                StepIngredientEntity(name="Knoblauchzehen", quantityPercent=100.0),
                StepIngredientEntity(name="grüne Chilischoten", quantityPercent=100.0),
            ],
            instruction="Ingwer, Knoblauch und Chilischoten unterrühren und braten, bis die Zwiebeln goldbraun gebacken haben."
        ),
        StepEntity(
            ingredients=[StepIngredientEntity(name="Tomaten", quantityPercent=100.0)],
            instruction="Die Temperatur etwas erhöhen. Die Tomaten in den Topf geben und garen, bis die Mischung dick und dunkler geworden ist."
        ),
        StepEntity(
            ingredients=[
                StepIngredientEntity(name="Möhre", quantityPercent=100.0),
                StepIngredientEntity(name="gemahlener Koriander", quantityPercent=100.0),
                StepIngredientEntity(name="gemahlene Kurkuma", quantityPercent=100.0),
                StepIngredientEntity(name="rotes Chilipulver", quantityPercent=100.0),
                StepIngredientEntity(name="gemahlener Kreuzkümmel", quantityPercent=100.0),
                StepIngredientEntity(name="Garam masala", quantityPercent=100.0),
            ],
            instruction="Die Möhre hinzufügen, dann gemahlenen Koriander, Kurkuma, Chilipulver, Kreuzkümmel und Garam masala darüberstreuen. Die Zutaten 1 Minute braten."
        ),
        StepEntity(
            ingredients=[StepIngredientEntity(name="Wasser", quantityPercent=50.0)],
            instruction="150 ml heißes Wasser dazugießen und zugedeckt 10–15 Minuten köcheln lassen, bis die Möhren fast weich sind."
        ),
        StepEntity(
            ingredients=[
                StepIngredientEntity(name="rote Paprikaschote", quantityPercent=100.0),
                StepIngredientEntity(name="grüne Bohnen", quantityPercent=100.0),
            ],
            instruction="Paprikaschote und grüne Bohnen unterrühren und alles ohne Deckel etwa 10 Minuten weitergaren, bis die Gemüse weich sind."
        ),
        StepEntity(
            ingredients=[
                StepIngredientEntity(name="Wachsbohnen aus der Dose", quantityPercent=100.0),
                StepIngredientEntity(name="Wasser", quantityPercent=50.0),
            ],
            instruction="Die Wachsbohnen sowie weitere 150 ml heißes Wasser hinzufügen und das Curry mit halb aufgelegtem Deckel noch einmal 10 Minuten garen; falls nötig zwischendurch etwas Wasser zugeben."
        ),
        StepEntity(
            ingredients=[StepIngredientEntity(name="gehackte Korianderblätter", quantityPercent=100.0)],
            instruction="Das Gericht mit dem gehackten Koriander garnieren und servieren, dazu gekochten Reis reichen."
        ),
    ]

    # Build NutritionInfoEntity
    nutrition_info = NutritionInfoEntity(
        calories=None,
        carbohydratesGrams=None,
        proteinGrams=None,
        fatGrams=None
    )

    return RecipeEntity(
        name="Butter bean curry Wachsbohnen-Curry",
        description="Gemahlene Masala-Gewürze werden auf den Märkten im südafrikanischen Durban nach Gewicht verkauft und für fast jede Art von Curry gibt es eine andere Gewürzmischung. Zu den beliebtesten gehört das »Schwiegermutterzungen-Masala« mit reichlich Chilischoten. In diesem Rezept lernen Sie meine eigene Variante der Mischung kennen. Sie ist milder als viele andere Masalas und hat einen fast nussigen Charakter mit einer Spur erfrischend scharfer Chilischoten. Die cremige Milde der Wachsbohnen harmoniert mit den kräftigen indischen Gewürzen besonders gut.",
        ingredients=ingredients,
        steps=steps,
        servings=4,
        cookingTimeMinutes=35,
        preparationTimeMinutes=15,
        nutritionInfo=nutrition_info
    )


