
from cryptography.fernet import Fernet # type: ignore

class Encrypt:
    def __init__(self):
        with open('key.txt', 'rb') as mykey:
            self.key = mykey.read()

    def encrypt(self, message):
        fernet = Fernet(self.key)
        encrypted = fernet.encrypt(str(message).encode())
        return encrypted

    def decrypt(self, encrypted):
        fernet = Fernet(self.key)
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode("utf-8")
    
if __name__ == "__main__":
    key = Fernet.generate_key()
    print(f"New Key: {key}")

    # de = Encrypt()
    # message = "Hello World"
    # encrypt_code = str(de.encrypt(message))
    # print(encrypt_code)

    # decrypt_code = ""
    # print(de.decrypt(decrypt_code))