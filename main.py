from fastapi import FastAPI
from app.routes.recipe import router as recipe_router

app = FastAPI()

app.include_router(recipe_router)
