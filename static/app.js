const $ = (id) => document.getElementById(id);
let partida = null;
let partidaActual = null;
const cacheReproduccion = new Map();
let seleccionada = null;
let ocupado = false;
let destinoPrevio = null;
const nombres = { b: 'Blancas', n: 'Negras' };
const isReviewing = () => partida && partidaActual && partida.historial.length < partidaActual.historial.length;

function aceptarPartidaActual(datos) {
  partida = partidaActual = datos;
  cacheReproduccion.clear();
}

async function review(paso) {
  if (ocupado || !partidaActual || paso < 0 || paso > partidaActual.historial.length) return;
  ocupado = true; render();
  try {
    const vista = paso === partidaActual.historial.length ? partidaActual
      : cacheReproduccion.get(paso) || await request(`/api/partida/reproducir/${paso}`);
    cacheReproduccion.set(paso, vista);
    partida = vista; seleccionada = null; destinoPrevio = null;
  } finally { ocupado = false; render(); }
}

async function request(recorrido, datos) {
  const respuesta = await fetch(recorrido, datos === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(datos),
  });
  const contenido = await respuesta.json();
  if (!respuesta.ok) throw new Error(contenido.error || 'No se pudo completar la acción.');
  return contenido;
}

function renderBoard() {
  if (!partida) return;
  const tablero = $('tablero');
  if (!tablero.children.length) {
    const fragmento = document.createDocumentFragment();
    for (let fila = 0; fila < 8; fila++) {
      for (let columna = 0; columna < 8; columna++) {
        const casilla = `${String.fromCharCode(65 + columna)}${8 - fila}`;
        const boton = document.createElement('button');
        boton.type = 'button';
        boton.dataset.casilla = casilla;
        if (columna === 0) {
          const numeroFila = document.createElement('span');
          numeroFila.className = 'numero-fila';
          numeroFila.textContent = 8 - fila;
          numeroFila.setAttribute('aria-hidden', 'true');
          boton.append(numeroFila);
        }
        boton.addEventListener('click', () => seleccionar(casilla));
        boton.addEventListener('pointerenter', () => previsualizar(casilla));
        boton.addEventListener('focus', () => previsualizar(casilla));
        fragmento.append(boton);
      }
    }
    tablero.append(fragmento);
  }
  const opciones = partida.jugadas_permitidas.filter((jugada) => jugada.origen === seleccionada);
  const ultima = partida.historial.at(-1);
  partida.tablero.forEach((fila, filaActual) => fila.forEach((ficha, columnaActual) => {
    const casilla = `${String.fromCharCode(65 + columnaActual)}${8 - filaActual}`;
    const boton = tablero.children[filaActual * 8 + columnaActual];
    boton.className = `casilla${(filaActual + columnaActual) % 2 ? ' oscura' : ''}`;
    if (ultima && [ultima.origen, ultima.destino].includes(casilla)) boton.classList.add('ultima');
    if (casilla === seleccionada) boton.classList.add('seleccionada');
    const destino = opciones.some((jugada) => jugada.destino === casilla);
    if (destino) boton.classList.add('disponible');
    boton.disabled = ocupado;
    boton.setAttribute('aria-pressed', String(casilla === seleccionada));
    const etiqueta = ficha === '-' ? 'vacía' : `${nombres[ficha.toLowerCase()]}${ficha === ficha.toUpperCase() ? ', dama' : ', ficha'}`;
    boton.setAttribute('aria-label', `${casilla}, ${etiqueta}${destino ? ', destino válido' : ''}`);
    let disco = boton.querySelector('.ficha');
    if (ficha === '-') disco?.remove();
    else {
      if (!disco) {
        disco = document.createElement('span');
        disco.setAttribute('aria-hidden', 'true');
        boton.append(disco);
      }
      disco.className = `ficha ${ficha.toLowerCase() === 'b' ? 'blanca' : 'negra'}`;
      const coronada = ficha === ficha.toUpperCase();
      disco.classList.toggle('coronada', coronada);
      disco.textContent = coronada ? '♛' : '';
    }
  }));
}

function render() {
  renderBoard();
  $('nueva-partida').disabled = ocupado || !partida;
  if (!partida) return;
  inspector.setup(partida.automata, partida.automata_dama);
  inspector.show(seleccionada ? partida.inspecciones[seleccionada]?.[destinoPrevio || seleccionada] : partida.ultima_inspeccion, true);
  const estado = partida.ganador ? `Ganan las ${nombres[partida.ganador].toLowerCase()}.`
    : partida.captura_obligatoria ? `Turno: ${nombres[partida.turno]}. Continuá capturando con ${partida.captura_obligatoria}.`
    : `Turno: ${nombres[partida.turno]}.`;
  $('estado').textContent = `${isReviewing() ? 'Revisión · ' : ''}${estado}`;
  const paso = partida.historial.length, total = partidaActual.historial.length;
  const ultima = partida.historial.at(-1);
  $('posicion-reproduccion').textContent = `${paso ? `Jugada ${paso} de ${total} · ${ultima.origen} → ${ultima.destino}${ultima.capturadas.length ? ` × ${ultima.capturadas.join(', ')}` : ''}` : `Posición inicial · 0 de ${total}`}${isReviewing() ? '' : ' · Actual'}`;
  $('jugada-anterior').disabled = ocupado || paso === 0;
  $('jugada-siguiente').disabled = ocupado || paso === total;
}

async function seleccionar(casilla) {
  if (ocupado || !partida) return;
  if (!isReviewing() && seleccionada && partida.jugadas_permitidas.some((jugada) => jugada.origen === seleccionada && jugada.destino === casilla)) {
    ocupado = true; render();
    try {
      aceptarPartidaActual(await request('/api/partida/mover', { origen: seleccionada, destino: casilla }));
      seleccionada = partida.captura_obligatoria;
      destinoPrevio = null;
    } finally { ocupado = false; render(); }
  } else if (partida.inspecciones[casilla]) {
    seleccionada = seleccionada === casilla ? null : casilla;
    destinoPrevio = null;
    render();
  } else previsualizar(casilla);
}

function previsualizar(casilla) {
  if (!seleccionada || ocupado || !partida || destinoPrevio === casilla) return;
  destinoPrevio = casilla;
  inspector.show(partida.inspecciones[seleccionada]?.[casilla]);
}

async function load() {
  aceptarPartidaActual(await request('/api/partida'));
  seleccionada = partida.captura_obligatoria;
  render();
}

$('jugada-anterior').addEventListener('click', () => review(partida.historial.length - 1));
$('jugada-siguiente').addEventListener('click', () => review(partida.historial.length + 1));
$('nueva-partida').addEventListener('click', () => $('dialogo-reinicio').showModal());
$('cancelar-reinicio').addEventListener('click', () => $('dialogo-reinicio').close());
$('confirmar-reinicio').addEventListener('click', async () => {
  if (ocupado) return;
  $('dialogo-reinicio').close(); ocupado = true; render();
  try { aceptarPartidaActual(await request('/api/partida/reiniciar', {})); seleccionada = null; destinoPrevio = null; }
  finally { ocupado = false; render(); }
});
load();
