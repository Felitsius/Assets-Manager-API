from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.core.config import settings
from app.api.v1 import router as api_v1_router  

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Asset Manager",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_v1_router, prefix=settings.API_V1_STR)  

@app.get("/")
async def root():
    return {
        "message": f"{settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "users": f"{settings.API_V1_STR}/users",  
            "auth": f"{settings.API_V1_STR}/auth",
            "categories": f"{settings.API_V1_STR}/categories",
            "locations": f"{settings.API_V1_STR}/locations",
            "movements": f"{settings.API_V1_STR}/movements",
            "assets": f"{settings.API_V1_STR}/assets"
        }
    }
