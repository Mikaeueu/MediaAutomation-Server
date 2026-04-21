from obswebsocket import obsws, requests

HOST = "localhost"
PORT = 4455
PASSWORD = "sua_senha"

def trocar_cena(nome_cena):
    ws = obsws(HOST, PORT, PASSWORD)
    ws.connect()
    ws.call(requests.SetCurrentProgramScene(sceneName=nome_cena))
    ws.disconnect()