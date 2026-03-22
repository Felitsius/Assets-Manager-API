from fastapi import APIRouter
from .endpoints import (
    auth, users, categories, locations, assets,
    movements
)

router = APIRouter(prefix="")

router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(categories.router, prefix="/categories", tags=["categories"])
router.include_router(locations.router, prefix="/locations", tags=["locations"])
router.include_router(assets.router, prefix="/assets", tags=["assets"])
router.include_router(movements.router, prefix="/movements", tags=["movements"])