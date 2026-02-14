import requests
import time
from threading import Thread

def keep_alive():
    while True:
        try:
            requests.get('https://roblox-api-97oe.onrender.com/health')
            print('API keepalive ping sent')
        except:
            pass
        time.sleep(840)

def start_keepalive():
    t = Thread(target=keep_alive)
    t.daemon = True
    t.start()