from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    @abstractmethod
    def send_notification(self, recipient: str, message: str):
        pass 