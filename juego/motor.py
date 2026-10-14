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

    def __post_init__(self):
        self.tablero_de_inicio = [fila[:] for fila in self.tablero]
        self.turno_de_inicio = self.turno

    def inspeccionar(self, origen: str, destino: str, permitidas: list[dict]) -> dict:
        fila, columna = posicion(origen)
        fila_destino, columna_destino = posicion(destino)
        ficha = self.tablero[fila][columna]
        ficha_propia = ficha.lower() == self.turno
        es_dama = ficha.isupper()
        simbolo_origen = "V" if ficha == "-" else "P" if ficha_propia else "E"
        resultado = {"origen": origen, "destino": destino, "jugador": self.turno,
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
            ocupante = self.tablero[fila_actual][columna_actual]
            simbolo = "V" if ocupante == "-" else "O" if ocupante.lower() == self.turno else "E"
            recorrido.append({"casilla": coordenada(fila_actual, columna_actual), "ficha": ocupante, "simbolo": simbolo})
        validacion = evaluar("".join(paso["simbolo"] for paso in recorrido), es_dama)
        valido = any(jugada["origen"] == origen and jugada["destino"] == destino for jugada in permitidas)
        if valido:
            motivo = "Jugada permitida por el motor."
        elif self.ganador:
            motivo = "La partida terminó."
        elif ficha.lower() != self.turno:
            motivo = "La ficha pertenece al jugador que no tiene el turno."
        elif not validacion["aceptada"]:
            motivo = "El autómata rechaza la ocupación del recorrido."
        elif self.tablero[fila_destino][columna_destino] != "-":
            motivo = "El destino debe estar vacío."
        elif ficha.islower() and ((diferencia_fila > 0) != (ficha == "n") or (distancia > 1 and distancia % 2)):
            motivo = "Una ficha normal avanza una casilla o encadena saltos de dos casillas hacia adelante."
        elif ficha.islower() and distancia > 1 and validacion["cadena"] != "P" + "EV" * (distancia // 2):
            motivo = "Cada salto necesita una pieza rival y una casilla vacía donde aterrizar."
        elif self.captura_obligatoria:
            motivo = f"Debe continuar la captura con la ficha de {self.captura_obligatoria}."
        else:
            motivo = "Hay una captura obligatoria disponible."
        return {**resultado, "recorrido": recorrido, "validacion": validacion, "permitida": valido, "motivo": motivo}

    def candidata(self, origen: str, destino: str) -> dict | None:
        fila, columna = posicion(origen)
        fila_destino, columna_destino = posicion(destino)
        ficha = self.tablero[fila][columna]
        diferencia_fila, diferencia_columna = fila_destino - fila, columna_destino - columna
        distancia = abs(diferencia_fila)
        if ficha == "-" or ficha.lower() != self.turno or self.tablero[fila_destino][columna_destino] != "-":
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
            ocupante = self.tablero[fila_actual][columna_actual]
            if ocupante == "-":
                cadena += "V"
            elif ocupante.lower() == self.turno:
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

    def candidatas(self, solo_origen=None) -> list[dict]:
        jugadas = []
        for fila in range(8):
            for columna in range(8):
                origen = coordenada(fila, columna)
                if self.tablero[fila][columna].lower() != self.turno or (solo_origen and origen != solo_origen):
                    continue
                for diferencia_fila, diferencia_columna in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                    for distancia in range(1, 8):
                        fila_actual, columna_actual = fila + diferencia_fila * distancia, columna + diferencia_columna * distancia
                        if not (0 <= fila_actual < 8 and 0 <= columna_actual < 8):
                            break
                        jugada = self.candidata(origen, coordenada(fila_actual, columna_actual))
                        if jugada:
                            jugadas.append(jugada)
        return jugadas

    def jugadas_permitidas(self) -> list[dict]:
        if self.ganador:
            return []
        jugadas = self.candidatas(self.captura_obligatoria)
        capturas = [jugada for jugada in jugadas if jugada["capturadas"]]
        return capturas if capturas or self.captura_obligatoria else jugadas

    def mover(self, origen: str, destino: str) -> None:
        posicion(origen)
        posicion(destino)
        if self.ganador:
            raise ValueError("La partida terminó. Iniciá una nueva para seguir jugando.")
        # jugadas_permitidas() obtiene las candidatas evaluadas por el autómata
        # y aplica la captura obligatoria. Buscamos la jugada solicitada entre ellas.
        seleccionada = next((jugada for jugada in self.jugadas_permitidas()
                         if jugada["origen"] == origen.upper() and jugada["destino"] == destino.upper()), None)
        if seleccionada is None:
            raise ValueError("Jugada inválida. Elegí uno de los destinos marcados; las capturas son obligatorias.")
        # Conservamos el recorrido y su traza antes de modificar el tablero,
        # para que la interfaz pueda mostrar cómo se evaluó esta jugada.
        self.ultima_inspeccion = self.inspeccionar(seleccionada["origen"], seleccionada["destino"], [seleccionada])
        fila_actual, columna_actual = posicion(origen)
        fila_destino, columna_destino = posicion(destino)
        ficha = self.tablero[fila_actual][columna_actual]
        self.tablero[fila_actual][columna_actual] = "-"
        self.tablero[fila_destino][columna_destino] = ficha
        for casilla in seleccionada["capturadas"]:
            fila_capturada, columna_capturada = posicion(casilla)
            self.tablero[fila_capturada][columna_capturada] = "-"
        self.capturas[self.turno] += len(seleccionada["capturadas"])
        self.ultima_validacion = seleccionada["validacion"]
        self.historial.append({"origen": seleccionada["origen"], "destino": seleccionada["destino"],
                             "jugador": self.turno, "capturadas": seleccionada["capturadas"]})
        coronada = ficha.islower() and fila_destino == (0 if self.turno == "b" else 7)
        if coronada:
            self.tablero[fila_destino][columna_destino] = ficha.upper()
        if seleccionada["capturadas"] and not coronada:
            if any(jugada["capturadas"] for jugada in self.candidatas(seleccionada["destino"])):
                self.captura_obligatoria = seleccionada["destino"]
                return
        self.captura_obligatoria = None
        anterior = self.turno
        self.turno = "n" if self.turno == "b" else "b"
        if not self.candidatas():
            self.ganador = anterior

    def serializar(self) -> dict:
        return {"tablero": self.tablero, "turno": self.turno, "captura_obligatoria": self.captura_obligatoria,
                "capturas": self.capturas, "historial": self.historial,
                "ganador": self.ganador, "ultima_validacion": self.ultima_validacion,
                "ultima_inspeccion": self.ultima_inspeccion}

    def estado(self) -> dict:
        permitidas = self.jugadas_permitidas()
        inspecciones = {}
        for fila in range(8):
            for columna in range(8):
                if self.tablero[fila][columna] == "-":
                    continue
                origen = coordenada(fila, columna)
                inspecciones[origen] = {coordenada(fila_actual, columna_actual): self.inspeccionar(origen, coordenada(fila_actual, columna_actual), permitidas)
                                       for fila_actual in range(8) for columna_actual in range(8)}
        return {**self.serializar(), "jugadas_permitidas": permitidas, "inspecciones": inspecciones,
                "automata": definicion(), "automata_dama": definicion(es_dama=True),
                "restantes": {color: sum(ficha.lower() == color for fila in self.tablero for ficha in fila)
                              for color in ("b", "n")}}
