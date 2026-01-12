import asyncio
from bot.utils.db_manager import update_user_balance

async def main():
    user_id = 7238078273
    amount = 10000
    new_balance = await update_user_balance(user_id, amount)
    print(f"Успешно! Пользователю {user_id} начислено {amount} койнов. Новый баланс: {new_balance}")

if __name__ == "__main__":
    asyncio.run(main())
