from typing import TYPE_CHECKING, Any

from magic_filter.magic import MagicFilter

from aiosend import loggers
from aiosend.enums import InvoiceStatus
from aiosend.handler import HandlerObject

from .base import BasePollingManager, PollingTask

if TYPE_CHECKING:
    from collections.abc import Callable

    import aiosend
    from aiosend.handler import Handler
    from aiosend.types import Invoice


class InvoicePollingManager(BasePollingManager):
    """Invoice polling manager."""

    def __init__(self) -> None:
        self._invoice_tasks: dict[int, PollingTask[Invoice]] = {}
        self._invoice_handlers: list[HandlerObject] = []
        self._exp_invoice_handlers: list[HandlerObject] = []

    def invoice_polling(
        self,
        *filters: MagicFilter,
    ) -> "Callable[[Handler], Handler]":
        """
        Register a handler for polling invoice updates.

        Decorator for handler function.

        :return: handler function.
        """

        def wrapper(handler: "Handler") -> "Handler":
            self._invoice_handlers.append(HandlerObject(handler, filters))
            return handler

        return wrapper

    def expired_invoice_polling(
        self,
        *filters: MagicFilter,
    ) -> "Callable[[Handler], Handler]":
        """
        Register a handler for timed out invoices.

        Decorator for handler function.

        :return: handler function.
        """

        def wrapper(handler: "Handler") -> "Handler":
            self._exp_invoice_handlers.append(HandlerObject(handler, filters))
            return handler

        return wrapper

    def _poll_invoice(self, invoice: "Invoice", data: dict[str, Any]) -> None:
        self._invoice_tasks[invoice.invoice_id] = PollingTask(
            invoice,
            self._timeout,
            data,
        )

    async def _handle_invoice(
        self: "aiosend.CryptoPay",
        invoice: "Invoice",
    ) -> None:
        self._invoice_tasks[invoice.invoice_id].timeout -= self._delay
        task = self._invoice_tasks[invoice.invoice_id]
        if (
            invoice.status in (InvoiceStatus.PAID, InvoiceStatus.EXPIRED)
            or task.timeout <= 0
        ):
            del self._invoice_tasks[invoice.invoice_id]
        if task.timeout <= 0 or invoice.status == InvoiceStatus.EXPIRED:
            for handler in self._exp_invoice_handlers:
                if handler.check(invoice):
                    await handler.call(
                        invoice,
                        task.data
                        | self._kwargs,
                    )
                    loggers.invoice_polling.info(
                        "EXPIRED INVOICE id=%d is handled.",
                        invoice.invoice_id,
                    )
                    break
            else:
                loggers.invoice_polling.info(
                    "EXPIRED INVOICE id=%d is not handled.",
                    invoice.invoice_id,
                )
        elif invoice.status == InvoiceStatus.PAID:
            for handler in self._invoice_handlers:
                if handler.check(invoice):
                    await handler.call(
                        invoice,
                        task.data | self._kwargs,
                    )
                    loggers.invoice_polling.info(
                        "PAID INVOICE id=%d is handled.",
                        invoice.invoice_id,
                    )
                    break
            else:
                loggers.invoice_polling.info(
                    "PAID INVOICE id=%d is not handled.",
                    invoice.invoice_id,
                )

    async def _start_invoice_polling(self: "aiosend.CryptoPay") -> None:
        """Start invoice polling."""
        await self._start_polling(
            self.get_invoices,  # type: ignore[arg-type]
            self._handle_invoice,  # type: ignore[arg-type]
            self._invoice_tasks,
            "invoice_ids",
            loggers.invoice_polling,
        )
