from aiogram import Router
from .payment import router as router_payment
from .promocode import router as router_promocode

routers = [router_payment, router_promocode]