from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.utils.db_manager import (
    get_chat_balance, update_chat_balance, get_catalog_categories, 
    add_catalog_request, get_catalog_chat, update_catalog_link, delete_catalog_link, get_approved_chats
)
from bot.utils.filters import ModuleEnabledFilter
import logging

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}), ModuleEnabledFilter("catalog"))

# Константы
CATALOG_MIN_BALANCE = 35000

@router.message(F.text.lower() == "каталог добавить")
async def handle_catalog_add(message: types.Message):
    """Подает заявку на добавление чата в каталог."""
    # 1. Проверяем баланс чата
    balance = await get_chat_balance(message.chat.id)
    if balance < CATALOG_MIN_BALANCE:
        await message.reply(
            f"❌ Для подачи заявки в каталог на балансе чата должно быть не менее <b>{CATALOG_MIN_BALANCE}</b> койнов.\n"
            f"Текущий баланс чата: <b>{balance}</b> койн.",
            parse_mode="HTML"
        )
        return

    # 2. Проверяем, есть ли уже в каталоге
    existing = await get_catalog_chat(message.chat.id)
    if existing:
        if existing["is_approved"]:
            await message.reply("ℹ️ Ваш чат уже находится в каталоге.")
        else:
            await message.reply("ℹ️ Ваша заявка находится на рассмотрении модераторами.")
        return

    # 3. Предлагаем выбрать категорию
    categories = await get_catalog_categories()
    if not categories:
        await message.reply("❌ Категории каталога пока не настроены администратором.")
        return

    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat["name"], callback_data=f"cat_add_{cat['id']}")
    builder.adjust(2)
    
    await message.answer(
        "📂 Выберите категорию для вашего чата:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("cat_add_"))
async def process_cat_add(callback: types.CallbackQuery):
    """Обработка выбора категории для заявки."""
    category_id = int(callback.data.split("_")[-1])
    
    success = await add_catalog_request(
        chat_id=callback.message.chat.id,
        category_id=category_id,
        added_by=callback.from_user.id
    )
    
    if success:
        await callback.message.edit_text(
            "✅ Заявка успешно подана! Она будет рассмотрена модераторами.\n"
            "Не забудьте установить ссылку командой <code>+Чат ссылка</code>",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text("❌ Ошибка при подаче заявки.")
    await callback.answer()

@router.message(F.text.lower().startswith("+чат"))
async def handle_set_link(message: types.Message):
    """Устанавливает ссылку на чат."""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("❌ Укажите ссылку.\nПример: <code>+Чат https://t.me/...</code>", parse_mode="HTML")
        return
        
    link = parts[1].strip()
    if not (link.startswith("https://t.me/") or link.startswith("t.me/")):
        await message.reply("❌ Ссылка должна быть форматом t.me/ или https://t.me/")
        return
        
    # Проверяем, подана ли заявка
    chat_data = await get_catalog_chat(message.chat.id)
    if not chat_data:
        await message.reply("❌ Сначала подайте заявку командой <code>Каталог добавить</code>", parse_mode="HTML")
        return
        
    success = await update_catalog_link(message.chat.id, link)
    if success:
        await message.reply(f"✅ Ссылка <code>{link}</code> успешно установлена!", parse_mode="HTML")
    else:
        await message.reply("❌ Ошибка при обновлении ссылки.")

@router.message(F.text.lower().startswith("-чат"))
async def handle_remove_link(message: types.Message):
    """Удаляет ссылку на чат."""
    # Проверяем, есть ли чат в каталоге
    chat_data = await get_catalog_chat(message.chat.id)
    if not chat_data or not chat_data.get("link"):
        await message.reply("❌ У вашего чата нет установленной ссылки в каталоге.")
        return
        
    success = await delete_catalog_link(message.chat.id)
    if success:
        await message.reply("✅ Ссылка успешно удалена из каталога. Теперь там будет кнопка «Попроситься в чат».")
    else:
        await message.reply("❌ Ошибка при удалении ссылки.")

@router.message(F.text.lower() == "каталог")
async def handle_catalog_list(message: types.Message):
    """Показывает категории каталога."""
    categories = await get_catalog_categories()
    if not categories:
        await message.reply("📂 Каталог пока пуст.")
        return

    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat["name"], callback_data=f"cat_view_{cat['id']}")
    builder.adjust(2)
    
    await message.answer(
        "📖 <b>Каталог чатов</b>\nВыберите категорию для просмотра:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("cat_view_"))
async def process_cat_view(callback: types.CallbackQuery):
    """Просмотр чатов в категории."""
    category_id = int(callback.data.split("_")[-1])
    chats = await get_approved_chats(category_id)
    
    if not chats:
        await callback.answer("В этой категории пока нет чатов.", show_alert=True)
        return
        
    text = "📍 <b>Чаты в этой категории:</b>\n\n"
    builder = InlineKeyboardBuilder()
    
    for i, chat in enumerate(chats, 1):
        # Здесь мы не знаем название чата, так как бот может не быть в нем или мы не храним его
        # В реальном боте лучше хранить название чата при подаче заявки
        chat_link = chat["link"]
        if chat_link:
            builder.button(text=f"Чат #{i}", url=chat_link)
        else:
            builder.button(text=f"Чат #{i} (Попроситься)", callback_data=f"chat_req_{chat['chat_id']}")
            
    builder.button(text="⬅️ Назад", callback_data="catalog_back")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "catalog_back")
async def process_catalog_back(callback: types.CallbackQuery):
    """Возврат к списку категорий."""
    categories = await get_catalog_categories()
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat["name"], callback_data=f"cat_view_{cat['id']}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "📖 <b>Каталог чатов</b>\nВыберите категорию для просмотра:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()
