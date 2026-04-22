from fastapi import FastAPI
from app.routes.example import router as example_router
from app.routes.recipe import router as recipe_router

app = FastAPI()

app.include_router(example_router)
app.include_router(recipe_router)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

