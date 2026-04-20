import requests
import time
from app.services.obs_service import trocar_cena

def monitorar_holyrics():
    ultima = None

    while True:
        try:
            res = requests.get("http://localhost:8080/api")  # ajustar
            atual = res.text

            if atual != ultima:
                trocar_cena("LETRA")
                ultima = atual

        except:
            pass

        time.sleep(2)