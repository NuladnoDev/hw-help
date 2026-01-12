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
from .welcome_handlers import router as welcome_router
from .clans import router as clans_router
from .clubs import router as clubs_router
from .jokes import router as jokes_router
from .reputation import router as reputation_router
from .economy import router as economy_router
from .shippering import router as shippering_router
from .repeat import router as repeat_router
from .info import router as info_router
from .yesno import router as yesno_router
from .who import router as who_router
from .choose import router as choose_router
from .ping import router as ping_router
from .catalog import router as catalog_router
from .antispam import router as antispam_router
from .module_management import router as module_mgmt_router
from .permission_management import router as permission_mgmt_router

router = Router()
router.include_router(module_mgmt_router)
router.include_router(permission_mgmt_router)
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
router.include_router(welcome_router)
router.include_router(clans_router)
router.include_router(clubs_router)
router.include_router(jokes_router)
router.include_router(reputation_router)
router.include_router(antispam_router)
router.include_router(economy_router)
router.include_router(shippering_router)
router.include_router(repeat_router)
router.include_router(info_router)
router.include_router(yesno_router)
router.include_router(who_router)
router.include_router(choose_router)
router.include_router(ping_router)
router.include_router(catalog_router)
