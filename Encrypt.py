
from cryptography.fernet import Fernet # type: ignore

class Encrypt:
    def __init__(self):
        with open('assets/google/key.txt', 'rb') as mykey:
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
    # key = Fernet.generate_key()
    # print(f"New Key: {key}")

    de = Encrypt()
    message = "Hello World"
    encrypt_code = str(de.encrypt(message))
    print(encrypt_code)

    decrypt_code = "gAAAAABnJEXVa9ojq9X6TKmksSFIWZHqFGgmPxyxi6DRydug3ZInSu6ehBn_ME3fpMCF34ea15CSOI5NuloDnS2PSO-OLt8Ul2bhI_P0WrKs4aithxtaH6mNHgDrE5YHHTmkpPjCzM6RAYZAZqekmUuPND5yCC6idMecflaKY5cnP1XL4JnB-aE="
    print(de.decrypt(decrypt_code))