from aiogram import Router

from .main_handlers import router as user_main_router

router = Router()
router.include_router(user_main_router)
