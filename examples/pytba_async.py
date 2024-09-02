import asyncio

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from cryptopay import CryptoPay
from cryptopay.types import Invoice

bot = AsyncTeleBot("TOKEN")
cp = CryptoPay("TOKEN")


@bot.message_handler()
async def get_invoice(message: Message) -> None:
    invoice = cp.create_invoice(1, "USDT")
    await bot.send_message(
        message.from_user.id,
        f"pay: {invoice.mini_app_invoice_url}",
    )
    invoice.await_payment(user_id=message.from_user.id)


@cp.polling_handler()
async def handle_payment(
    invoice: Invoice,
    user_id: int,
) -> None:
    await bot.send_message(
        user_id,
        f"payment received: {invoice.amount} {invoice.asset}",
    )


async def main() -> None:
    await asyncio.gather(
        bot.infinity_polling(),
        cp.run_polling(),
    )


if __name__ == "__main__":
    asyncio.run(main())
