//Lógica de presentación del autómata
const inspector = (() => {
  const etiquetas = { inicio: 'Inicio', propia: 'Propia', movimiento: 'Movimiento', enemiga: 'Enemiga', captura: 'Captura', invalido: 'Inválido' };
  let timers = [];
  let definicion = null;
  let definiciones = null;
  let viz = null;
  let claveActual = null;
  let ultimaInspeccion = null;
  let tipoSeleccionado = 'ficha';
  const pestanas = [...document.querySelectorAll('.pestanas-automata [role="tab"]')];

  function diagram(titulo, viz) {
    const seccion = document.createElement('section'); seccion.className = 'diagrama-automata';
    const encabezado = document.createElement('h3'); encabezado.textContent = titulo;
    seccion.append(encabezado);
    const grupos = {};
    for (const [origen, transiciones] of Object.entries(definicion.transiciones)) {
      for (const [simbolo, destino] of Object.entries(transiciones)) {
        const clave = `${origen}:${destino}`;
        grupos[clave] ??= { origen, destino, simbolos: [] };
        grupos[clave].simbolos.push(simbolo);
      }
    }
    const transiciones = Object.values(grupos);
    // Viz.js calcula las posiciones, curvas y flechas a partir del AFD del servidor.
    const svg = viz.renderSVGElement({
      directed: true,
      graphAttributes: { rankdir: 'LR', bgcolor: 'transparent', pad: 0.15, nodesep: 0.5, ranksep: 0.5 },
      nodeAttributes: { shape: 'circle', style: 'filled', fillcolor: '#1c293a', color: '#8293a8', fontcolor: '#e6edf5', fontname: 'Arial', fontsize: 12 },
      edgeAttributes: { color: '#8293a8', fontcolor: '#b8c5d6', fontname: 'Arial', fontsize: 11, arrowsize: 0.7 },
      nodes: [
        { name: 'entrada', attributes: { shape: 'point', label: '', width: 0.05 } },
        ...definicion.estados.map(estado => ({
          name: estado,
          attributes: { id: `estado-${estado}`, label: etiquetas[estado], shape: definicion.finales.includes(estado) ? 'doublecircle' : 'circle' },
        })),
      ],
      edges: [
        { tail: 'entrada', head: definicion.inicial },
        ...transiciones.map(({ origen, destino, simbolos }, indice) => ({
          tail: origen, head: destino,
          attributes: { id: `transicion-${indice}`, label: simbolos.sort().join(',') },
        })),
      ],
    });
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Estados y transiciones del autómata de recorrido');
    svg.removeAttribute('width');
    svg.removeAttribute('height');
    // Asociamos los elementos generados con los estados de la traza para animarlos.
    transiciones.forEach(({ origen, destino }, indice) => {
      const arco = svg.querySelector(`#transicion-${indice}`);
      arco.classList.add('arco-automata');
      arco.dataset.origen = origen;
      arco.dataset.destino = destino;
    });
    for (const estado of definicion.estados) {
      const nodo = svg.querySelector(`#estado-${estado}`);
      nodo.classList.add('nodo-automata');
      nodo.dataset.estado = estado;
    }
    seccion.append(svg);
    const aclaracion = document.createElement('p');
    aclaracion.textContent = 'Solo se evalúan recorridos en diagonal.';
    seccion.append(aclaracion);
    const traza = document.createElement('p'); traza.className = 'traza-automata'; seccion.append(traza);
    const simbolos = document.createElement('ul'); simbolos.className = 'simbolos-diagrama';
    for (const [simbolo, significado] of [['P', 'Origen con ficha propia'], ['E', 'Ficha enemiga'], ['V', 'Casilla vacía'], ['O', 'Ficha propia que bloquea el recorrido']]) {
      const elementoLista = document.createElement('li');
      const codigo = document.createElement('b'); codigo.textContent = simbolo;
      elementoLista.append(codigo, `: ${significado}.`); simbolos.append(elementoLista);
    }
    seccion.append(simbolos);
    return seccion;
  }

  async function setup(datos, datosDama) {
    if (definiciones) return;
    definiciones = { ficha: datos, dama: datosDama };
    const contenedor = document.getElementById('diagramas-automata');
    contenedor.textContent = 'Cargando diagrama…';
    try {
      viz = await Viz.instance();
      show(ultimaInspeccion, true, false);
    } catch (excepcion) {
      definiciones = null;
      definicion = null;
      viz = null;
      contenedor.textContent = 'No se pudo generar el diagrama del autómata.';
      console.error('Error al generar el diagrama:', excepcion);
    }
  }

  function clear() {
    timers.forEach(clearTimeout); timers = [];
    document.querySelectorAll('.casilla.inspeccionada, .casilla.leyendo').forEach(elemento => elemento.classList.remove('inspeccionada', 'leyendo'));
  }

  function frame(inspeccion, paso) {
    const validacion = inspeccion?.validacion;
    const traza = validacion ? validacion.traza.slice(0, paso + 1) : ['inicio'];
    const estadosVisitados = new Set(traza);
    const transicionesVisitadas = new Set(traza.slice(1).map((destino, indice) => `${traza[indice]}:${destino}`));
    for (const panel of document.querySelectorAll('.diagrama-automata')) {
      panel.querySelectorAll('.nodo-automata').forEach(nodo => nodo.classList.toggle('activo', estadosVisitados.has(nodo.dataset.estado)));
      panel.querySelectorAll('.arco-automata').forEach(arco => {
        const activo = transicionesVisitadas.has(`${arco.dataset.origen}:${arco.dataset.destino}`);
        arco.classList.toggle('activo', activo);
      });
      panel.querySelector('.traza-automata').textContent = traza.map(estado => etiquetas[estado]).join(' → ');
    }
    document.querySelectorAll('.casilla.leyendo').forEach(elemento => elemento.classList.remove('leyendo'));
    const casilla = inspeccion?.recorrido[paso - 1]?.casilla;
    if (casilla) document.querySelector(`[data-casilla="${casilla}"]`)?.classList.add('leyendo');
  }

  function show(inspeccion, force = false, actualizarTipo = true) {
    ultimaInspeccion = inspeccion;
    if (actualizarTipo && inspeccion) tipoSeleccionado = inspeccion.es_dama ? 'dama' : 'ficha';
    for (const pestana of pestanas) {
      const seleccionada = pestana.dataset.tipo === tipoSeleccionado;
      pestana.setAttribute('aria-selected', String(seleccionada));
      pestana.tabIndex = seleccionada ? 0 : -1;
    }
    document.getElementById('diagramas-automata').setAttribute('aria-labelledby', `tab-${tipoSeleccionado}`);
    if (!viz) return;
    const datos = definiciones[tipoSeleccionado];
    if (definicion !== datos) {
      clear();
      definicion = datos;
      claveActual = null;
      document.getElementById('diagramas-automata').replaceChildren(diagram('Control de recorrido', viz));
    }
    // Solo animamos la evaluación si pertenece al tipo de pieza mostrado.
    if (inspeccion && inspeccion.es_dama !== (tipoSeleccionado === 'dama')) inspeccion = null;
    const clave = JSON.stringify(inspeccion);
    if (clave === claveActual && !force) return;
    claveActual = clave; clear();
    for (const paso of inspeccion?.recorrido || []) {
      document.querySelector(`[data-casilla="${paso.casilla}"]`)?.classList.add('inspeccionada');
    }
    frame(inspeccion, 0);
    if (!inspeccion?.validacion) return;
    const longitud = inspeccion.validacion.cadena.length;
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { frame(inspeccion, longitud); return; }
    for (let paso = 1; paso <= longitud; paso++) timers.push(setTimeout(() => frame(inspeccion, paso), paso * 260));
  }

  function selectTab(pestana) {
    tipoSeleccionado = pestana.dataset.tipo;
    show(ultimaInspeccion, true, false);
  }

  pestanas.forEach((pestana, indice) => {
    pestana.addEventListener('click', () => selectTab(pestana));
    pestana.addEventListener('keydown', event => {
      const desplazamientos = { ArrowLeft: -1, ArrowRight: 1, Home: -indice, End: pestanas.length - 1 - indice };
      if (!(event.key in desplazamientos)) return;
      event.preventDefault();
      const siguiente = pestanas[(indice + desplazamientos[event.key] + pestanas.length) % pestanas.length];
      selectTab(siguiente);
      siguiente.focus();
    });
  });

  return { setup, show };
})();
