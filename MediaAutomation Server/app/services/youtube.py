import datetime

def gerar_titulo():
    dia = datetime.datetime.now().strftime("%A")

    titulos = {
        "Sunday": "Culto de Domingo",
        "Wednesday": "Culto de Ensino",
    }

    return titulos.get(dia, "Culto Ao Vivo")