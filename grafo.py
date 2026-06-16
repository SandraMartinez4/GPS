import heapq
import math
from datetime import datetime, timedelta


def distancia_haversine_km(punto_a, punto_b):
    lat1, lng1 = punto_a
    lat2, lng2 = punto_b
    radio_tierra = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radio_tierra * c


def distancia_manhattan_km(punto_a, punto_b):
    lat1, lng1 = punto_a
    lat2, lng2 = punto_b

    km_por_grado_lat = 111.32
    lat_promedio = math.radians((lat1 + lat2) / 2)
    km_por_grado_lng = 111.32 * math.cos(lat_promedio)

    distancia_lat = abs(lat2 - lat1) * km_por_grado_lat
    distancia_lng = abs(lng2 - lng1) * km_por_grado_lng

    return distancia_lat + distancia_lng


def redondear_nodo(punto):
    return round(punto[0], 6), round(punto[1], 6)


def agregar_arista(grafo, nodo_a, nodo_b, peso):
    grafo.setdefault(nodo_a, []).append((nodo_b, peso))
    grafo.setdefault(nodo_b, []).append((nodo_a, peso))


def construir_grafo_desde_rutas(rutas_osm):
    grafo = {}
    rutas_en_puntos = []

    for ruta in rutas_osm:
        puntos_ruta = [redondear_nodo(punto) for punto in ruta["geometry"]]
        puntos_limpios = []

        for punto in puntos_ruta:
            if not puntos_limpios or puntos_limpios[-1] != punto:
                puntos_limpios.append(punto)

        rutas_en_puntos.append(puntos_limpios)

        for i in range(len(puntos_limpios) - 1):
            nodo_a = puntos_limpios[i]
            nodo_b = puntos_limpios[i + 1]
            peso = distancia_haversine_km(nodo_a, nodo_b)
            agregar_arista(grafo, nodo_a, nodo_b, peso)

    return grafo, rutas_en_puntos


def construir_camino(anteriores, destino):
    camino = []
    nodo = destino
    while nodo is not None:
        camino.append(nodo)
        nodo = anteriores.get(nodo)
    camino.reverse()
    return camino


def dijkstra(grafo, inicio, destino):
    cola = []
    heapq.heappush(cola, (0, inicio))
    distancias = {inicio: 0}
    anteriores = {inicio: None}
    visitados = set()

    while cola:
        distancia_actual, nodo_actual = heapq.heappop(cola)
        if nodo_actual in visitados:
            continue
        visitados.add(nodo_actual)
        if nodo_actual == destino:
            break
        for vecino, peso in grafo.get(nodo_actual, []):
            nueva_distancia = distancia_actual + peso
            if vecino not in distancias or nueva_distancia < distancias[vecino]:
                distancias[vecino] = nueva_distancia
                anteriores[vecino] = nodo_actual
                heapq.heappush(cola, (nueva_distancia, vecino))

    if destino not in anteriores:
        raise RuntimeError("No se encontró una ruta válida.")

    return construir_camino(anteriores, destino), distancias[destino]


def astar(grafo, inicio, destino):
    def heuristica(nodo):
        return distancia_manhattan_km(nodo, destino)

    cola = []
    g_score = {inicio: 0}
    heapq.heappush(cola, (heuristica(inicio), inicio))
    anteriores = {inicio: None}
    visitados = set()

    while cola:
        _, nodo_actual = heapq.heappop(cola)
        if nodo_actual in visitados:
            continue
        visitados.add(nodo_actual)
        if nodo_actual == destino:
            break
        for vecino, peso in grafo.get(nodo_actual, []):
            tentative = g_score[nodo_actual] + peso
            if tentative < g_score.get(vecino, float("inf")):
                g_score[vecino] = tentative
                anteriores[vecino] = nodo_actual
                heapq.heappush(cola, (tentative + heuristica(vecino), vecino))

    if destino not in anteriores:
        raise RuntimeError("No se encontró una ruta válida.")

    return construir_camino(anteriores, destino), g_score[destino]


def greedy_manhattan(grafo, inicio, destino):
    def heuristica(nodo):
        return distancia_manhattan_km(nodo, destino)

    cola = []
    heapq.heappush(cola, (heuristica(inicio), inicio))
    anteriores = {inicio: None}
    visitados = set()

    while cola:
        _, nodo_actual = heapq.heappop(cola)
        if nodo_actual in visitados:
            continue
        visitados.add(nodo_actual)
        if nodo_actual == destino:
            break
        for vecino, peso in grafo.get(nodo_actual, []):
            if vecino not in visitados:
                if vecino not in anteriores:
                    anteriores[vecino] = nodo_actual
                heapq.heappush(cola, (heuristica(vecino), vecino))

    if destino not in anteriores:
        raise RuntimeError("No se encontró una ruta válida.")

    camino = construir_camino(anteriores, destino)
    distancia_total = sum(
        distancia_haversine_km(camino[i], camino[i + 1])
        for i in range(len(camino) - 1)
    )
    return camino, distancia_total


def costo_uniforme(grafo, inicio, destino):
    return dijkstra(grafo, inicio, destino)


def calcular_rutas_por_algoritmo(rutas_osm, vehiculo, usar_peajes, rendimiento_personalizado=None):
    grafo, rutas_en_puntos = construir_grafo_desde_rutas(rutas_osm)

    if not rutas_en_puntos or not rutas_en_puntos[0]:
        raise RuntimeError("No hay suficientes puntos para calcular una ruta.")

    inicio = rutas_en_puntos[0][0]
    destino = rutas_en_puntos[0][-1]

    rendimiento = obtener_rendimiento_por_vehiculo(vehiculo, rendimiento_personalizado)
    rutas = []
    operaciones = [
        ("manhattan", "Manhattan"),
        ("astar", "A*"),
        ("costo_uniforme", "Costo uniforme")
    ]

    for clave, nombre in operaciones:
        if clave == "manhattan":
            camino, distancia_total_km = greedy_manhattan(grafo, inicio, destino)
        elif clave == "astar":
            camino, distancia_total_km = astar(grafo, inicio, destino)
        else:
            camino, distancia_total_km = costo_uniforme(grafo, inicio, destino)

        zonas_rojas = encontrar_zonas_rojas(camino)
        peaje_estimado, peajes_detectados = estimar_peaje_por_vehiculo(camino, vehiculo, usar_peajes)
        duracion_minutos = int(round((distancia_total_km / 80.0) * 60.0))
        duracion_texto = f"{duracion_minutos} min" if duracion_minutos < 60 else f"{duracion_minutos // 60}h {duracion_minutos % 60}min"

        rutas.append({
            "algoritmo": nombre,
            "coordenadas": [[lat, lng] for lat, lng in camino],
            "distancia_metros": distancia_total_km * 1000,
            "distancia_km": round(distancia_total_km, 2),
            "duracion_minutos": duracion_minutos,
            "duracion_texto": duracion_texto,
            "zonas_rojas": zonas_rojas,
            "peaje_estimado": round(peaje_estimado, 2),
            "peajes_detectados": peajes_detectados,
            "critica": bool(zonas_rojas or peaje_estimado > 0),
            "critica_detalle": {
                "zonas_rojas": zonas_rojas,
                "peajes_detectados": peajes_detectados
            },
            "rendimiento": rendimiento
        })

    return rutas


def zona_horaria_por_longitud(lng):
    if lng >= -86.5:
        return "UTC-5"
    if lng >= -103.5:
        return "UTC-6"
    if lng >= -115:
        return "UTC-7"
    return "UTC-8"


def hora_local_por_offset(offset_text, minutos=0):
    ahora_utc = datetime.utcnow()
    if offset_text.startswith("UTC"):
        signo = offset_text[3]
        horas = int(offset_text[4:])
        delta = timedelta(hours=horas if signo == "+" else -horas)
        return (ahora_utc + delta + timedelta(minutes=minutos)).strftime("%H:%M")
    return (ahora_utc + timedelta(minutes=minutos)).strftime("%H:%M")


def punto_en_caja(punto, caja):
    lat, lng = punto
    return (
        caja["min_lat"] <= lat <= caja["max_lat"]
        and caja["min_lng"] <= lng <= caja["max_lng"]
    )


def encontrar_zonas_rojas(camino):
    zonas = [
        {
            "nombre": "Zona Roja Ciudad de México",
            "min_lat": 19.15,
            "max_lat": 19.55,
            "min_lng": -99.4,
            "max_lng": -98.9
        },
        {
            "nombre": "Zona Roja Guadalajara",
            "min_lat": 20.55,
            "max_lat": 20.80,
            "min_lng": -103.5,
            "max_lng": -103.2
        },
        {
            "nombre": "Zona Roja Monterrey",
            "min_lat": 25.58,
            "max_lat": 25.75,
            "min_lng": -100.45,
            "max_lng": -100.25
        }
    ]

    encontradas = set()
    for punto in camino:
        for zona in zonas:
            if punto_en_caja(punto, zona):
                encontradas.add(zona["nombre"])

    return list(encontradas)


def estimar_peaje_por_vehiculo(camino, vehiculo, usar_peajes):
    if not usar_peajes:
        return 0.0, []

    peajes = [
        {
            "nombre": "Caseta Puebla-Córdoba",
            "min_lat": 18.8,
            "max_lat": 19.4,
            "min_lng": -98.8,
            "max_lng": -97.9,
            "precio": {"auto": 270, "camioneta": 330, "moto": 180, "camion": 500}
        },
        {
            "nombre": "Caseta México-Querétaro",
            "min_lat": 19.1,
            "max_lat": 20.0,
            "min_lng": -99.4,
            "max_lng": -98.4,
            "precio": {"auto": 116, "camioneta": 146, "moto": 76, "camion": 220}
        }
    ]

    total = 0.0
    detectados = set()
    tipo = vehiculo if vehiculo in ["auto", "camioneta", "moto", "camion"] else "auto"

    for caseta in peajes:
        if any(punto_en_caja(punto, caseta) for punto in camino):
            total += caseta["precio"].get(tipo, caseta["precio"]["auto"])
            detectados.add(caseta["nombre"])

    return total, list(detectados)


def obtener_rendimiento_por_vehiculo(vehiculo, personalizado=None):
    if vehiculo == "personalizado" and personalizado:
        try:
            valor = float(personalizado)
            return max(valor, 1.0)
        except (ValueError, TypeError):
            return 10.0

    rendimientos = {
        "auto": 12.0,
        "camioneta": 8.0,
        "moto": 25.0,
        "camion": 4.0
    }
    return rendimientos.get(vehiculo, 12.0)
