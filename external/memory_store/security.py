# external/security.py
from cryptography.fernet import Fernet
import base64
from typing import Optional
##TODO:理应放在common里
class Encryptor:
    def __init__(self, key_b64: Optional[str] = None):
        if key_b64:
            key = base64.urlsafe_b64decode(key_b64)
            self._fernet = Fernet(key)
            self._enabled = True
        else:
            self._enabled = False  # 开发模式：不加密

    def encrypt(self, plaintext: str) -> bytes:
        if not self._enabled:
            return plaintext.encode('utf-8')  # 明文返回 bytes
        return self._fernet.encrypt(plaintext.encode('utf-8'))

    def decrypt(self, ciphertext: bytes) -> str:
        if not self._enabled:
            return ciphertext.decode('utf-8')
        return self._fernet.decrypt(ciphertext).decode('utf-8')