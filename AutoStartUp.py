# importing os module 
import os 
import time

os.system('start cmd /k "ngrok http 80"')
time.sleep(3)
os.system('start cmd /k "python main.py"')