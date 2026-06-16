import requests
from functools import lru_cache

SESSION = requests.Session()


def intentar_parsear_coordenadas(texto):
    """
    Detecta si el texto viene como coordenadas directas.
    Ejemplo: 19.951234,-99.532456
    """
    try:
        partes = texto.split(",")

        if len(partes) != 2:
            return None

        lat = float(partes[0].strip())
        lng = float(partes[1].strip())

        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng

        return None

    except ValueError:
        return None


def obtener_coordenadas_osm(lugar):
    """
    Si recibe coordenadas, las usa directo.
    Si recibe texto, usa Nominatim de OpenStreetMap.
    """
    coordenadas_directas = intentar_parsear_coordenadas(lugar)

    if coordenadas_directas:
        lat, lng = coordenadas_directas
        direccion_formateada = f"{lat}, {lng}"
        return coordenadas_directas, direccion_formateada

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": lugar,
        "format": "json",
        "addressdetails": 0,
        "limit": 1,
        "countrycodes": "mx"
    }
    headers = {
        "User-Agent": "GPS-Main-App/1.0"
    }

    try:
        respuesta = requests.get(url, params=params, headers=headers, timeout=15)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except Exception as exc:
        raise RuntimeError(f"Error al obtener coordenadas de OSM: {exc}")

    if not datos:
        raise RuntimeError("No se encontraron coordenadas con OSM para ese lugar.")

    resultado = datos[0]
    lat = float(resultado["lat"])
    lon = float(resultado["lon"])
    direccion_formateada = resultado.get("display_name", lugar)

    return (lat, lon), direccion_formateada


def buscar_lugares_osm(query, limit=5):
    if not query:
        return []

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 0,
        "limit": limit,
        "countrycodes": "mx"
    }
    headers = {
        "User-Agent": "GPS-Main-App/1.0"
    }

    try:
        respuesta = SESSION.get(url, params=params, headers=headers, timeout=15)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except Exception:
        return []

    resultados = []
    for item in datos:
        try:
            resultados.append({
                "display_name": item.get("display_name", query),
                "lat": float(item["lat"]),
                "lon": float(item["lon"])
            })
        except (ValueError, KeyError, TypeError):
            continue

    return resultados


@lru_cache(maxsize=128)
def _obtener_lugar_por_punto_cached(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 0,
        "zoom": 10
    }
    headers = {
        "User-Agent": "GPS-Main-App/1.0"
    }

    try:
        respuesta = SESSION.get(url, params=params, headers=headers, timeout=15)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except Exception:
        return None

    nombre = datos.get("display_name")
    if not nombre:
        return None

    return nombre.split(",")[0].strip()


def obtener_lugar_por_punto(lat, lon):
    return _obtener_lugar_por_punto_cached(round(lat, 5), round(lon, 5))

    nombre = datos.get("display_name")
    if not nombre:
        return None

    return nombre.split(",")[0].strip()


def obtener_lugares_por_ruta(geometria, max_puntos=3):
    if not geometria:
        return []

    if len(geometria) <= max_puntos + 2:
        puntos = geometria
    else:
        puntos = []
        paso = len(geometria) / (max_puntos + 1)
        for i in range(1, max_puntos + 1):
            indice = min(len(geometria) - 2, int(round(i * paso)))
            puntos.append(geometria[indice])

    lugares = []
    vistos = set()
    for lat, lon in puntos:
        lugar = obtener_lugar_por_punto(lat, lon)
        if lugar:
            nombre = lugar.split(',')[0].strip()
            if nombre and nombre not in vistos:
                lugares.append(nombre)
                vistos.add(nombre)

    return lugares


def obtener_rutas_osrm(origen_coord, destino_coord):
    
    lon_origen, lat_origen = origen_coord[1], origen_coord[0]
    lon_destino, lat_destino = destino_coord[1], destino_coord[0]

    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{lon_origen},{lat_origen};{lon_destino},{lat_destino}"
    )
    params = {
        "alternatives": "true",
        "geometries": "geojson",
        "overview": "full",
        "steps": "false"
    }

    try:
        respuesta = SESSION.get(url, params=params, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except Exception as exc:
        raise RuntimeError(f"Error al llamar a OSRM: {exc}")

    if not isinstance(datos, dict):
        raise RuntimeError("Respuesta de OSRM no es un JSON válido.")

    if datos.get("code") != "Ok":
        motivo = datos.get("message", "Sin detalle")
        raise RuntimeError(f"OSRM respondió error: {motivo}")

    rutas = []
    for ruta in datos.get("routes", []):
        rutas.append({
            "geometry": [
                (punto[1], punto[0]) for punto in ruta["geometry"]["coordinates"]
            ],
            "distance": ruta["distance"],
            "duration": ruta["duration"],
            "weight_name": ruta.get("weight_name", "")
        })

    if not rutas:
        raise RuntimeError("No se encontraron rutas disponibles.")

    return rutas
