from aiogram import Router

from .moderation import router as moderation_router
from .events import router as events_router
from .nicknames import router as nicknames_router
from .profile_handlers import router as profile_router
from .ranks import router as ranks_router
from .invites import router as invites_router
from .duels import router as duels_router
from .roulette import router as roulette_router
from .weather import router as weather_router
from .marriages import router as marriages_router
from .relationships import router as relationships_router

router = Router()
router.include_router(weather_router)
router.include_router(ranks_router)
router.include_router(invites_router)
router.include_router(duels_router)
router.include_router(roulette_router)
router.include_router(marriages_router)
router.include_router(relationships_router)
router.include_router(nicknames_router)
router.include_router(profile_router)
router.include_router(moderation_router)
router.include_router(events_router)
