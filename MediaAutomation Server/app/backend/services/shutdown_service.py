import os

def desligar_em(segundos):
    os.system(f"shutdown /s /t {segundos}")