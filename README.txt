Proyecto GPS Autómatas 

Cómo ejecutar en PowerShell:

1. Entra a la carpeta del proyecto:

2. Crea entorno virtual si no existe:
   python -m venv .venv

3. Actívalo:
   .\.venv\Scripts\Activate.ps1

4. Instala dependencias base:
   pip install -r requirements.txt

5. Opcional, si quieres carreteras reales de OpenStreetMap:
   pip install osmnx

7. Ejecuta:
   python app.py

8. Abre:
   http://127.0.0.1:5000

Pruebas rápidas:
- Origen: Jilotepec
- Destino: CDMX

- Origen: Jilotepec
- Destino: Querétaro

- Origen: Jilotepec
- Destino: San Juan del Río
