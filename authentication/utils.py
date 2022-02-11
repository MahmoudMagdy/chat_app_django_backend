from django.core.mail import EmailMessage
import threading


class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        super().__init__()

    def run(self):
        self.email.send()


class MailingUtils:
    @staticmethod
    def send_email(data):
        email = EmailMessage(**data)
        EmailThread(email).start()
