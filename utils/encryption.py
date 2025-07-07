from cryptography.fernet import Fernet
from django.conf import settings


class CredentialEncryption:
    def __init__(self):
        self.key = settings.ENCRYPTION_KEY.encode()
        self.cipher = Fernet(self.key)

    def encrypt(self, text):
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        return self.cipher.decrypt(encrypted_text.encode()).decode()