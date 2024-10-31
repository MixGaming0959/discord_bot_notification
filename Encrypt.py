
from cryptography.fernet import Fernet # type: ignore

class Encrypt:
    def __init__(self):
        with open('assets/key.txt', 'rb') as mykey:
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
    de = Encrypt()
    message = "Hello World"
    x = "gAAAAABnIdH5PBbFYAAJj7lkNnErNncL7-rnRBowy19W4LZ-i1KscpiEwRizEyWWMvJPzpvEAMzJeIHMWBv13a5aRaUEFWovYA=="
    TOKEN = str(de.encrypt(message))

    print(TOKEN)
    print(de.decrypt(x))