from datetime import datetime, timedelta
import traceback

from flask import Flask, render_template, request, jsonify

from google_service import (
    obtener_coordenadas_osm,
    obtener_rutas_osrm,
    buscar_lugares_osm,
    obtener_lugares_por_ruta,
)
from grafo import (
    calcular_rutas_por_algoritmo,
    zona_horaria_por_longitud,
    hora_local_por_offset,
)

gps = Flask(__name__)
app = gps


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/buscar_lugar")
def buscar_lugar():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    try:
        resultados = buscar_lugares_osm(query)
        return jsonify(resultados)
    except Exception:
        return jsonify([]), 500


@app.route("/calcular_ruta", methods=["POST"])
def calcular_ruta():
    data = request.get_json(silent=True) or {}

    origen = data.get("origen", "").strip()
    destino = data.get("destino", "").strip()
    vehiculo = data.get("vehiculo", "auto")
    usar_peajes = bool(data.get("peajes", True))
    rendimiento_personalizado = data.get("rendimiento_personalizado")

    if not origen or not destino:
        return jsonify({
            "error": "Debes escribir origen y destino."
        }), 400

    try:
        origen_coord, origen_direccion = obtener_coordenadas_osm(origen)
        destino_coord, destino_direccion = obtener_coordenadas_osm(destino)

        if origen_coord == destino_coord:
            return jsonify({
                "error": "El origen y el destino son el mismo punto.",
                "detalle": "Selecciona dos puntos diferentes."
            }), 400

        rutas_osm = obtener_rutas_osrm(origen_coord, destino_coord)
        algoritmos = calcular_rutas_por_algoritmo(rutas_osm, vehiculo, usar_peajes, rendimiento_personalizado)

        for ruta in algoritmos:
            ruta["lugares"] = obtener_lugares_por_ruta(ruta.get("coordenadas", []))

        ruta_principal = min(algoritmos, key=lambda r: r["duracion_minutos"])
        criticas_raw = [
            {
                "zonas_rojas": r["zonas_rojas"],
                "peajes_detectados": r["peajes_detectados"],
                "motivo": r["critica_detalle"],
                "lugares": r.get("lugares", [])
            }
            for r in algoritmos if r["critica"]
        ]

        resumen_criticas = {}
        for crit in criticas_raw:
            key = (
                tuple(sorted(crit["zonas_rojas"])),
                tuple(sorted(crit["peajes_detectados"]))
            )
            if key not in resumen_criticas:
                resumen_criticas[key] = {
                    "zonas_rojas": crit["zonas_rojas"],
                    "peajes_detectados": crit["peajes_detectados"],
                    "motivo": crit["motivo"],
                    "conteo": 0,
                    "lugares": []
                }
            resumen_criticas[key]["lugares"] = list({*resumen_criticas[key].get("lugares", []), *crit.get("lugares", [])})
            resumen_criticas[key]["conteo"] += 1

        rutas_criticas = list(resumen_criticas.values())

        rutas_alternas = []
        for idx, ruta in enumerate(rutas_osm[1:4], start=1):
            puntos = [[p[0], p[1]] for p in ruta["geometry"]]
            rutas_alternas.append({
                "nombre": f"Alternativa {idx}",
                "distancia_km": round(ruta["distance"] / 1000, 2),
                "duracion_minutos": int(ruta["duration"] / 60),
                "puntos": puntos,
                "lugares": obtener_lugares_por_ruta(puntos),
                "color": "#1d72d8",
                "dashArray": "8,10"
            })

    except Exception as error:
        traceback.print_exc()
        return jsonify({
            "error": "No se pudo calcular la ruta.",
            "detalle": str(error)
        }), 500

    distancia_km = ruta_principal["distancia_metros"] / 1000
    duracion_texto = ruta_principal["duracion_texto"]
    origen_tz = zona_horaria_por_longitud(origen_coord[1])
    destino_tz = zona_horaria_por_longitud(destino_coord[1])
    origen_hora = hora_local_por_offset(origen_tz)
    destino_hora = hora_local_por_offset(destino_tz)

    capacidad_tanque = 50
    rendimiento = ruta_principal["rendimiento"]
    litros = distancia_km / rendimiento
    rango_km = rendimiento * capacidad_tanque
    hora_actual_origen = hora_local_por_offset(origen_tz)
    hora_llegada_origen = hora_local_por_offset(origen_tz, int(ruta_principal["duracion_minutos"]))
    hora_actual_destino = hora_local_por_offset(destino_tz)
    hora_llegada_destino = hora_local_por_offset(destino_tz, int(ruta_principal["duracion_minutos"]))

    if litros > capacidad_tanque:
        alerta_gasolina = "Advertencia: la ruta supera la autonomía con un tanque completo. Carga gasolina antes de salir."
    elif distancia_km > rango_km * 0.75:
        alerta_gasolina = "Atención: la ruta consume más del 75% de tu tanque. Considera una parada extra."
    else:
        alerta_gasolina = "Autonomía suficiente para la ruta planificada."

    ruta_principal["litros_necesarios"] = round(litros, 2)
    ruta_principal["rendimiento"] = rendimiento
    ruta_principal["autonomia_km"] = round(rango_km, 1)
    ruta_principal["casetas"] = ruta_principal.get("peajes_detectados", [])
    ruta_principal["costo_casetas"] = ruta_principal.get("peaje_estimado", 0.0)
    ruta_principal["trafico_saturado"] = bool(ruta_principal.get("zonas_rojas"))

    return jsonify({
        "origen": origen,
        "destino": destino,
        "origen_direccion": origen_direccion,
        "destino_direccion": destino_direccion,
        "origen_coord": origen_coord,
        "destino_coord": destino_coord,
        "ruta_principal": ruta_principal,
        "algoritmos": algoritmos,
        "rutas_criticas": rutas_criticas,
        "zona_horaria_origen": origen_tz,
        "zona_horaria_destino": destino_tz,
        "hora_local_origen": hora_actual_origen,
        "hora_llegada_origen": hora_llegada_origen,
        "hora_local_destino": hora_actual_destino,
        "hora_llegada_destino": hora_llegada_destino,
        "alerta_gasolina": alerta_gasolina,
        "rutas_alternas": rutas_alternas
    })


if __name__ == "__main__":
    gps.run(host="0.0.0.0", port=5000, debug=True)
