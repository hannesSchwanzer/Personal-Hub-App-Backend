from fastapi import FastAPI
from app.api.recipe import router as recipe_router
from app.api.food import router as food_router

app = FastAPI()

app.include_router(recipe_router)
app.include_router(food_router)
