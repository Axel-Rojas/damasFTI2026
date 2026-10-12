from dataclasses import dataclass, field

from .automata import definicion, evaluar


def coordenada(fila: int, columna: int) -> str:
    return f"{chr(65 + columna)}{8 - fila}"


def posicion(casilla: str) -> tuple[int, int]:
    if not isinstance(casilla, str) or len(casilla) != 2:
        raise ValueError("Usá una coordenada entre A1 y H8.")
    casilla = casilla.upper()
    if casilla[0] not in "ABCDEFGH" or casilla[1] not in "12345678":
        raise ValueError("Usá una coordenada entre A1 y H8.")
    return 8 - int(casilla[1]), ord(casilla[0]) - 65


def tablero_inicial() -> list[list[str]]:
    return [[("n" if fila < 3 else "b" if fila > 4 else "-")
             if (fila + columna) % 2 else "-" for columna in range(8)] for fila in range(8)]


@dataclass
class Partida:
    tablero: list[list[str]] = field(default_factory=tablero_inicial)
    turno: str = "b"
    captura_obligatoria: str | None = None
    capturas: dict = field(default_factory=lambda: {"b": 0, "n": 0})
    historial: list = field(default_factory=list)
    ganador: str | None = None
    ultima_validacion: dict | None = None
    ultima_inspeccion: dict | None = None
    tablero_de_inicio: list[list[str]] = field(init=False, repr=False)
    turno_de_inicio: str = field(init=False, repr=False)

    def __post_init__(instancia):
        instancia.tablero_de_inicio = [fila[:] for fila in instancia.tablero]
        instancia.turno_de_inicio = instancia.turno

    def inspeccionar(instancia, origen: str, destino: str, permitidas: list[dict]) -> dict:
        fila, columna = posicion(origen)
        fila_destino, columna_destino = posicion(destino)
        ficha = instancia.tablero[fila][columna]
        ficha_propia = ficha.lower() == instancia.turno
        es_dama = ficha.isupper()
        simbolo_origen = "V" if ficha == "-" else "P" if ficha_propia else "E"
        resultado = {"origen": origen, "destino": destino, "jugador": instancia.turno,
                  "recorrido": [], "validacion": None, "permitida": False, "es_dama": es_dama}
        diferencia_fila, diferencia_columna = fila_destino - fila, columna_destino - columna
        if origen == destino:
            return {**resultado, "recorrido": [{"casilla": origen, "ficha": ficha, "simbolo": simbolo_origen}],
                    "validacion": evaluar(simbolo_origen, es_dama), "parcial": ficha_propia,
                    "motivo": "Ficha seleccionada. Elegí un destino para completar la cadena." if ficha_propia
                    else "La ficha pertenece al jugador que no tiene el turno."}
        if not diferencia_fila or abs(diferencia_fila) != abs(diferencia_columna):
            return {**resultado, "motivo": "Elegí un destino en diagonal para evaluar el recorrido."}
        distancia = abs(diferencia_fila)
        sentido_fila, sentido_columna = (1 if diferencia_fila > 0 else -1), (1 if diferencia_columna > 0 else -1)
        recorrido = [{"casilla": origen, "ficha": ficha, "simbolo": simbolo_origen}]
        for desplazamiento in range(1, distancia + 1):
            fila_actual, columna_actual = fila + sentido_fila * desplazamiento, columna + sentido_columna * desplazamiento
            ocupante = instancia.tablero[fila_actual][columna_actual]
            simbolo = "V" if ocupante == "-" else "O" if ocupante.lower() == instancia.turno else "E"
            recorrido.append({"casilla": coordenada(fila_actual, columna_actual), "ficha": ocupante, "simbolo": simbolo})
        validacion = evaluar("".join(paso["simbolo"] for paso in recorrido), es_dama)
        valido = any(jugada["origen"] == origen and jugada["destino"] == destino for jugada in permitidas)
        if valido:
            motivo = "Jugada permitida por el motor."
        elif instancia.ganador:
            motivo = "La partida terminó."
        elif ficha.lower() != instancia.turno:
            motivo = "La ficha pertenece al jugador que no tiene el turno."
        elif not validacion["aceptada"]:
            motivo = "El autómata rechaza la ocupación del recorrido."
        elif instancia.tablero[fila_destino][columna_destino] != "-":
            motivo = "El destino debe estar vacío."
        elif ficha.islower() and ((diferencia_fila > 0) != (ficha == "n") or (distancia > 1 and distancia % 2)):
            motivo = "Una ficha normal avanza una casilla o encadena saltos de dos casillas hacia adelante."
        elif ficha.islower() and distancia > 1 and validacion["cadena"] != "P" + "EV" * (distancia // 2):
            motivo = "Cada salto necesita una pieza rival y una casilla vacía donde aterrizar."
        elif instancia.captura_obligatoria:
            motivo = f"Debe continuar la captura con la ficha de {instancia.captura_obligatoria}."
        else:
            motivo = "Hay una captura obligatoria disponible."
        return {**resultado, "recorrido": recorrido, "validacion": validacion, "permitida": valido, "motivo": motivo}

    def candidata(instancia, origen: str, destino: str) -> dict | None:
        fila, columna = posicion(origen)
        fila_destino, columna_destino = posicion(destino)
        ficha = instancia.tablero[fila][columna]
        diferencia_fila, diferencia_columna = fila_destino - fila, columna_destino - columna
        distancia = abs(diferencia_fila)
        if ficha == "-" or ficha.lower() != instancia.turno or instancia.tablero[fila_destino][columna_destino] != "-":
            return None
        if not distancia or distancia != abs(diferencia_columna):
            return None
        if ficha.islower() and ((diferencia_fila > 0) != (ficha == "n") or (distancia > 1 and distancia % 2)):
            return None
        paso_fila, paso_columna = (1 if diferencia_fila > 0 else -1), (1 if diferencia_columna > 0 else -1)
        # Convertimos la diagonal en una cadena del alfabeto del autómata.
        # P representa el origen; cada casilla siguiente aporta V, O o E.
        cadena, enemigas = "P", []
        for desplazamiento in range(1, distancia + 1):
            fila_actual, columna_actual = fila + desplazamiento * paso_fila, columna + desplazamiento * paso_columna
            ocupante = instancia.tablero[fila_actual][columna_actual]
            if ocupante == "-":
                cadena += "V"
            elif ocupante.lower() == instancia.turno:
                cadena += "O"
            else:
                cadena += "E"
                enemigas.append((fila_actual, columna_actual))
        # El AFD valida la ocupación del recorrido; el motor también controla
        # dirección y captura obligatoria para decidir si se puede jugar.
        # Elegimos las transiciones según si la pieza está coronada.
        validacion = evaluar(cadena, ficha.isupper())
        if not validacion["aceptada"]:
            return None
        if ficha.islower() and distancia > 1 and cadena != "P" + "EV" * (distancia // 2):
            return None
        return {"origen": origen.upper(), "destino": destino.upper(),
                "capturadas": [coordenada(fila_actual, columna_actual) for fila_actual, columna_actual in enemigas], "validacion": validacion}

    def candidatas(instancia, solo_origen=None) -> list[dict]:
        jugadas = []
        for fila in range(8):
            for columna in range(8):
                origen = coordenada(fila, columna)
                if instancia.tablero[fila][columna].lower() != instancia.turno or (solo_origen and origen != solo_origen):
                    continue
                for diferencia_fila, diferencia_columna in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                    for distancia in range(1, 8):
                        fila_actual, columna_actual = fila + diferencia_fila * distancia, columna + diferencia_columna * distancia
                        if not (0 <= fila_actual < 8 and 0 <= columna_actual < 8):
                            break
                        jugada = instancia.candidata(origen, coordenada(fila_actual, columna_actual))
                        if jugada:
                            jugadas.append(jugada)
        return jugadas

    def jugadas_permitidas(instancia) -> list[dict]:
        if instancia.ganador:
            return []
        jugadas = instancia.candidatas(instancia.captura_obligatoria)
        capturas = [jugada for jugada in jugadas if jugada["capturadas"]]
        return capturas if capturas or instancia.captura_obligatoria else jugadas

    def mover(instancia, origen: str, destino: str) -> None:
        posicion(origen)
        posicion(destino)
        if instancia.ganador:
            raise ValueError("La partida terminó. Iniciá una nueva para seguir jugando.")
        # jugadas_permitidas() obtiene las candidatas evaluadas por el autómata
        # y aplica la captura obligatoria. Buscamos la jugada solicitada entre ellas.
        seleccionada = next((jugada for jugada in instancia.jugadas_permitidas()
                         if jugada["origen"] == origen.upper() and jugada["destino"] == destino.upper()), None)
        if seleccionada is None:
            raise ValueError("Jugada inválida. Elegí uno de los destinos marcados; las capturas son obligatorias.")
        # Conservamos el recorrido y su traza antes de modificar el tablero,
        # para que la interfaz pueda mostrar cómo se evaluó esta jugada.
        instancia.ultima_inspeccion = instancia.inspeccionar(seleccionada["origen"], seleccionada["destino"], [seleccionada])
        fila_actual, columna_actual = posicion(origen)
        fila_destino, columna_destino = posicion(destino)
        ficha = instancia.tablero[fila_actual][columna_actual]
        instancia.tablero[fila_actual][columna_actual] = "-"
        instancia.tablero[fila_destino][columna_destino] = ficha
        for casilla in seleccionada["capturadas"]:
            fila_capturada, columna_capturada = posicion(casilla)
            instancia.tablero[fila_capturada][columna_capturada] = "-"
        instancia.capturas[instancia.turno] += len(seleccionada["capturadas"])
        instancia.ultima_validacion = seleccionada["validacion"]
        instancia.historial.append({"origen": seleccionada["origen"], "destino": seleccionada["destino"],
                             "jugador": instancia.turno, "capturadas": seleccionada["capturadas"]})
        coronada = ficha.islower() and fila_destino == (0 if instancia.turno == "b" else 7)
        if coronada:
            instancia.tablero[fila_destino][columna_destino] = ficha.upper()
        if seleccionada["capturadas"] and not coronada:
            if any(jugada["capturadas"] for jugada in instancia.candidatas(seleccionada["destino"])):
                instancia.captura_obligatoria = seleccionada["destino"]
                return
        instancia.captura_obligatoria = None
        anterior = instancia.turno
        instancia.turno = "n" if instancia.turno == "b" else "b"
        if not instancia.candidatas():
            instancia.ganador = anterior

    def serializar(instancia) -> dict:
        return {"tablero": instancia.tablero, "turno": instancia.turno, "captura_obligatoria": instancia.captura_obligatoria,
                "capturas": instancia.capturas, "historial": instancia.historial,
                "ganador": instancia.ganador, "ultima_validacion": instancia.ultima_validacion,
                "ultima_inspeccion": instancia.ultima_inspeccion}

    def estado(instancia) -> dict:
        permitidas = instancia.jugadas_permitidas()
        inspecciones = {}
        for fila in range(8):
            for columna in range(8):
                if instancia.tablero[fila][columna] == "-":
                    continue
                origen = coordenada(fila, columna)
                inspecciones[origen] = {coordenada(fila_actual, columna_actual): instancia.inspeccionar(origen, coordenada(fila_actual, columna_actual), permitidas)
                                       for fila_actual in range(8) for columna_actual in range(8)}
        return {**instancia.serializar(), "jugadas_permitidas": permitidas, "inspecciones": inspecciones,
                "automata": definicion(), "automata_dama": definicion(es_dama=True),
                "restantes": {color: sum(ficha.lower() == color for fila in instancia.tablero for ficha in fila)
                              for color in ("b", "n")}}
