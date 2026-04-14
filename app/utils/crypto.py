import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from app.core.config import settings

def _get_encryption_key() -> bytes:
    """Tạo 32-byte key từ SECRET_KEY."""
    kdf = Scrypt(
        salt=b"salt",
        length=32,
        n=16384,
        r=8,
        p=1,
        backend=default_backend()
    )
    return kdf.derive(settings.SECRET_KEY.encode("utf-8"))

ENCRYPTION_KEY = _get_encryption_key()

def encrypt_aes256(text: str) -> str:
    """Mã hóa chuỗi bằng thuật toán AES-256-CBC."""
    if not text:
        return text
    
    # Bỏ qua nếu chuỗi đã có format iv:encrypted (ví dụ IV length là 32 ký tự hex)
    if ":" in text:
        parts = text.split(":")
        if len(parts[0]) == 32:
            return text
            
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(text.encode("utf-8")) + padder.finalize()
    
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    
    return f"{iv.hex()}:{encrypted.hex()}"

def decrypt_aes256(encrypted_data: str) -> str:
    """Giải mã chuỗi từ AES-256-CBC."""
    if not encrypted_data or ":" not in encrypted_data:
        return encrypted_data
        
    try:
        iv_hex, encrypted_hex = encrypted_data.split(":")
        if len(iv_hex) != 32:
            return encrypted_data
            
        iv = bytes.fromhex(iv_hex)
        encrypted_bytes = bytes.fromhex(encrypted_hex)
        
        cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()
        
        unpadder = padding.PKCS7(128).unpadder()
        decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return decrypted_data.decode("utf-8")
    except Exception:
        # Fallback nếu giải mã thất bại hoặc chuỗi không phải là chuỗi mã hóa
        return encrypted_data
