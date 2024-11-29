import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Message

from aiocpa import CryptoPay
from aiocpa.types import Invoice

cp = CryptoPay("TOKEN")
bot = Bot("TOKEN")
dp = Dispatcher()


@dp.message()
async def get_invoice(message: Message) -> None:
    invoice = await cp.create_invoice(1, "USDT")
    await message.answer(f"pay: {invoice.mini_app_invoice_url}")
    invoice.await_payment(message=message)


@cp.polling_handler()
async def handle_payment(
    invoice: Invoice,
    message: Message,
) -> None:
    await message.answer(
        f"payment received: {invoice.amount} {invoice.asset}",
    )


async def main() -> None:
    await asyncio.gather(
        dp.start_polling(bot),
        cp.run_polling(),
    )


if __name__ == "__main__":
    asyncio.run(main())
