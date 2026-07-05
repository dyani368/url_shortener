from fastapi import FastAPI
from app.routers import auth 


app = FastAPI()
app.include_router(auth.router,prefix="/api/users", tags=["users"])


@app.get("/")
def home():
    return {"message":"Welcome to URL Shortener!"}