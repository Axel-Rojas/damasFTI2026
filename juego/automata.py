from automata.fa.dfa import DFA as AutomataAFD

# Cada estado representa el avance de la lectura del recorrido diagonal.
# P: ficha propia de origen; E: enemiga; V: casilla vacía; O: otra ficha propia
ESTADOS = {"inicio", "propia", "enemiga", "movimiento", "captura", "invalido"}
SIMBOLOS = {"P", "E", "V", "O"}

# Toda transición no permitida conduce al estado sumidero
TRANSICIONES = {estado: {simbolo: "invalido" for simbolo in SIMBOLOS} for estado in ESTADOS}

# El recorrido debe comenzar en la ficha propia que se quiere mover.
TRANSICIONES["inicio"]["P"] = "propia"

# Leer una casilla vacía permite avanzar, encontrar una enemiga exige saltarla.
TRANSICIONES["propia"].update(V="movimiento", E="enemiga")

# Después de una enemiga debe existir una casilla vacía donde aterrizar.
TRANSICIONES["enemiga"]["V"] = "captura"

# Una ficha normal solo avanza una casilla
TRANSICIONES["captura"]["E"] = "enemiga"
FINALES = {"movimiento", "captura"}

# Las damas pueden recorrer varias casillas vacías antes y después de un salto.
TRANSICIONES_DAMA = {estado: destinos.copy() for estado, destinos in TRANSICIONES.items()}
TRANSICIONES_DAMA["movimiento"].update(V="movimiento", E="enemiga")
TRANSICIONES_DAMA["captura"]["V"] = "captura"

AUTOMATA = AutomataAFD(
    states=ESTADOS, input_symbols=SIMBOLOS, transitions=TRANSICIONES,
    initial_state="inicio", final_states=FINALES,
)
AUTOMATA_DAMA = AutomataAFD(
    states=ESTADOS, input_symbols=SIMBOLOS, transitions=TRANSICIONES_DAMA,
    initial_state="inicio", final_states=FINALES,
)


def definicion(es_dama: bool = False) -> dict:
    return {"estados": sorted(ESTADOS), "simbolos": sorted(SIMBOLOS),
            "transiciones": TRANSICIONES_DAMA if es_dama else TRANSICIONES,
            "inicial": "inicio", "finales": sorted(FINALES)}


def evaluar(cadena: str, es_dama: bool = False) -> dict:
    if not cadena or not set(cadena) <= SIMBOLOS:
        raise ValueError("El recorrido debe ser una cadena no vacía del alfabeto P, E, V, O.")
    # La biblioteca decide si la cadena termina en un estado de aceptación.
    # Por ejemplo, PEV recorre inicio -> propia -> enemiga -> captura.
    automata = AUTOMATA_DAMA if es_dama else AUTOMATA
    transiciones = TRANSICIONES_DAMA if es_dama else TRANSICIONES
    aceptada = automata.accepts_input(cadena)
    # Reconstruimos los estados visitados para animar el diagrama en la interfaz.
    estado = "inicio"
    traza = [estado]
    for simbolo in cadena:
        estado = transiciones[estado][simbolo]
        traza.append(estado)
    return {"cadena": cadena, "traza": traza, "aceptada": aceptada}
