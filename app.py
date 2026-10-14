import os
import secrets
import threading
from time import monotonic

from flask import Flask, jsonify, render_template, request, session

from juego.motor import Partida


def create_app() -> Flask:
    aplicacion = Flask(__name__, template_folder=".")
    aplicacion.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    aplicacion.config.update(MAX_CONTENT_LENGTH=4096, SESSION_COOKIE_SAMESITE="Strict")
    partidas = {}
    bloqueo = threading.Lock()

    def partida_actual() -> Partida:
        ahora = monotonic()
        vencidas = [clave for clave, (_, ultimo_acceso) in partidas.items() if ahora - ultimo_acceso > 86400]
        for clave in vencidas:
            del partidas[clave]
        clave = session.get("id_partida")
        if clave not in partidas:
            clave = secrets.token_urlsafe(24)
            session["id_partida"] = clave
            partidas[clave] = (Partida(), ahora)
        partida = partidas[clave][0]
        partidas[clave] = (partida, ahora)
        return partida

    @aplicacion.get("/")
    def inicio():
        return render_template("index.html")

    @aplicacion.get("/api/partida")
    def estado():
        with bloqueo:
            return jsonify(partida_actual().estado())

    @aplicacion.post("/api/partida/reiniciar")
    def reiniciar():
        with bloqueo:
            partida_actual()
            partida = Partida()
            partidas[session["id_partida"]] = (partida, monotonic())
            return jsonify(partida.estado())

    @aplicacion.get("/api/partida/reproducir/<int:paso>")
    def reproducir(paso):
        with bloqueo:
            partida = partida_actual()
            if paso > len(partida.historial):
                return jsonify(error="Esa jugada no existe en el historial."), 400
            vista = Partida(tablero=[fila[:] for fila in partida.tablero_de_inicio], turno=partida.turno_de_inicio)
            for entrada in partida.historial[:paso]:
                vista.mover(entrada["origen"], entrada["destino"])
            return jsonify(vista.estado())

    @aplicacion.post("/api/partida/mover")
    def mover():
        # El navegador envía las coordenadas como {"origen": "A3", "destino": "B4"}.
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify(error="La jugada debe enviarse como JSON."), 400
        with bloqueo:
            partida = partida_actual()
            try:
                # El motor comprueba la jugada mediante sus reglas y el AFD.
                # Solo modifica el tablero si la jugada está permitida.
                partida.mover(datos.get("origen"), datos.get("destino"))
            except ValueError as error:
                return jsonify(error=str(error)), 400
            return jsonify(partida.estado())

    @aplicacion.after_request
    def sin_cache(respuesta):
        if request.path.startswith("/api/"):
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    return aplicacion


def main():
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)


if __name__ == "__main__":
    main()
