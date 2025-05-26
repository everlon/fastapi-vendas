import smtplib
import ssl
from email.mime.text import MIMEText
import asyncio
from .notification_channel import NotificationChannel
from src.core.config import settings

class EmailNotificationChannel(NotificationChannel):
    async def send_notification(self, recipient: str, message: str, subject: str):
        smtp_server = settings.SMTP_HOST
        port = settings.SMTP_PORT
        sender_email = settings.EMAILS_FROM_EMAIL
        sender_password = settings.SMTP_PASSWORD

        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = f"{settings.EMAILS_FROM_NAME} <{sender_email}>"
        msg['To'] = recipient

        print(f"Tentando enviar email real para {recipient} com a mensagem: {message}")
        print(f"Usando servidor: {smtp_server}:{port}")

        # Implementação real de envio (usando asyncio.to_thread para não bloquear)
        def _send_sync_email():
            try:
                # Configuração de SSL/TLS
                # Usar settings.SMTP_TLS para configurar SSL/TLS
                if settings.SMTP_TLS:
                    context = ssl.create_default_context()
                    with smtplib.SMTP(smtp_server, port) as server:
                        server.starttls(context=context)
                        server.login(sender_email, sender_password)
                        server.sendmail(sender_email, recipient, msg.as_string())
                else:
                    with smtplib.SMTP(smtp_server, port) as server:
                         server.login(sender_email, sender_password)
                         server.sendmail(sender_email, recipient, msg.as_string())
                print("Email enviado com sucesso.")
            except Exception as e:
                print(f"Falha ao enviar email: {e}")
        
        # Executar a função síncrona em um thread separado
        await asyncio.to_thread(_send_sync_email) # Usa o pool de threads padrão do asyncio 