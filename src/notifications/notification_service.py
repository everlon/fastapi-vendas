import asyncio

from typing import List
from .notification_channel import NotificationChannel
from .email_channel import EmailNotificationChannel
from src.models.order import Order

class NotificationService:
    def __init__(self, channels: List[NotificationChannel]):
        self.channels = channels

    async def send_order_creation_notification(self, order: Order, recipient_email: str):
        subject = f"Novo Pedido Criado: #{order.id}\n\n"
        message_body = f"Detalhes do pedido:\n\nID: {order.id}\nCliente ID: {order.client_id}\nStatus: {order.status}\nData/Hora: {order.created_at}\nTotal: {order.total:.2f}"

        tasks = []
        for channel in self.channels:
            if isinstance(channel, EmailNotificationChannel):
                tasks.append(channel.send_notification(recipient=recipient_email, message=message_body, subject=subject))

        await asyncio.gather(*tasks) 