"""Posiciones independientes para explorar las reglas sin modificar la partida."""

from .motor import Partida, posicion


EJEMPLOS = [
    ("Movimiento normal", "B2", "C3", {"B2": "b"}),
    ("Captura normal", "B2", "D4", {"B2": "b", "C3": "n"}),
    ("Captura múltiple", "B2", "F6", {"B2": "b", "C3": "n", "E5": "n"}),
    ("Movimiento con dama", "B6", "E3", {"B6": "B"}),
    ("Captura con dama", "B2", "F6", {"B2": "B", "D4": "n"}),
    ("Captura múltiple con dama", "A1", "H8", {"A1": "B", "C3": "n", "F6": "n"}),
]


def listado():
    return [{"id": indice, "titulo": titulo, "origen": origen, "destino": destino}
            for indice, (titulo, origen, destino, _) in enumerate(EJEMPLOS, 1)]


def partida_ejemplo(indice):
    _, _, _, piezas = EJEMPLOS[indice - 1]
    tablero = [["-"] * 8 for _ in range(8)]
    for casilla, pieza in piezas.items():
        fila, columna = posicion(casilla)
        tablero[fila][columna] = pieza
    return Partida(tablero=tablero)


def ejemplo(indice):
    _, origen, destino, _ = EJEMPLOS[indice - 1]
    partida = partida_ejemplo(indice)
    estado = partida.estado()
    return {"partida": estado, "inspeccion": estado["inspecciones"][origen][destino]}
