#!/usr/bin/env python3
"""
printLog.py - Visualizador de logs de CorporateLog
Muestra los 10 elementos más recientes, normalizando timezones
"""

import boto3
import json
from datetime import datetime, timezone
import pytz

# Conexión a DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CorporateLog')

# Leer toda la tabla
print(f"Leyendo todos los elementos de la tabla '{table.name}'...\n")
response = table.scan()
items = response.get('Items', [])

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))


# Detectar timezone local
local_tz = datetime.now(timezone.utc).astimezone().tzinfo
utc_tz = pytz.UTC


def parse_timestamp(value):
    """Convierte el timestamp a un valor comparable (epoch en hora local)"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        dt = None
        
        try:
            # Formato ISO con timezone: 2025-10-28T23:01:25.443763+00:00
            if 'T' in value and ('+' in value or value.endswith('Z')):
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                # Convertir a hora local
                dt = dt.astimezone(local_tz).replace(tzinfo=None)
                return dt.timestamp()
        except ValueError:
            pass
        
        try:
            # Formato con espacio: 2025-11-05 17:19:03 (asumir hora local)
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            # Hacer aware con timezone local para timestamp correcto
            dt_aware = dt.replace(tzinfo=local_tz)
            return dt_aware.timestamp()
        except ValueError:
            pass
        
        try:
            # Formato con espacio y microsegundos
            dt = datetime.strptime(value.split('.')[0], '%Y-%m-%d %H:%M:%S')
            dt_aware = dt.replace(tzinfo=local_tz)
            return dt_aware.timestamp()
        except ValueError:
            pass
    
    return 0.0


def readable_timestamp(value):
    """Convierte el timestamp a formato legible en hora local"""
    dt_utc = None
    
    if isinstance(value, (int, float)):
        dt_utc = datetime.utcfromtimestamp(value)
    elif isinstance(value, str):
        # Formato ISO con timezone: 2025-10-28T23:01:25.443763+00:00
        if 'T' in value and ('+' in value or value.endswith('Z')):
            try:
                dt_aware = datetime.fromisoformat(value.replace('Z', '+00:00'))
                dt_utc = dt_aware.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                pass
        
        # Formato con espacio: se asume UTC
        if dt_utc is None:
            try:
                dt_utc = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        # Formato con espacio y microsegundos
        if dt_utc is None:
            try:
                dt_utc = datetime.strptime(value.split('.')[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return str(value)
    
    if dt_utc is None:
        return str(value)
    
    # Convertir UTC → hora local
    dt_utc_aware = dt_utc.replace(tzinfo=timezone.utc)
    dt_local = dt_utc_aware.astimezone(local_tz).replace(tzinfo=None)
    
    # Comparar con UTC actual para "hace X"
    now_utc = datetime.utcnow()
    delta = now_utc - dt_utc

    # Formato de tiempo transcurrido
    if delta.days > 0:
        elapsed = f"hace {delta.days} día{'s' if delta.days > 1 else ''}"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        elapsed = f"hace {hours} hora{'s' if hours > 1 else ''}"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        elapsed = f"hace {minutes} minuto{'s' if minutes > 1 else ''}"
    else:
        elapsed = f"hace {delta.seconds} segundo{'s' if delta.seconds != 1 else ''}"

    # Mostrar en hora local
    return f"{dt_local.strftime('%Y-%m-%d %H:%M:%S')} ({elapsed})"


# Debug: mostrar algunos timestamps para verificar parsing
print("=== DEBUG: Primeros 5 timestamps ===")
for i, item in enumerate(items[:5]):
    ts = item.get('timestamp')
    parsed = parse_timestamp(ts)
    print(f"  {i}: '{ts}' -> {parsed}")
print()

# Debug: mostrar los 5 items después de ordenar
print("=== DEBUG: Top 5 después de sort ===")
items_sorted = sorted(items, key=lambda x: parse_timestamp(x.get('timestamp')), reverse=True)
for i, item in enumerate(items_sorted[:5]):
    ts = item.get('timestamp')
    parsed = parse_timestamp(ts)
    print(f"  {i}: '{ts}' (parsed: {parsed}) - uuid: {item.get('uuid', 'N/A')[:8]}...")
print()

# Ordenar y mostrar los 10 más recientes
if not items:
    print("La tabla está vacía.")
else:
    items_sorted = sorted(items, key=lambda x: parse_timestamp(x.get('timestamp')), reverse=True)
    top_10 = items_sorted[:10]
    
    print(f"Mostrando los 10 registros más recientes de '{table.name}' (Total: {len(items)} items):\n")
    
    for i, item in enumerate(top_10, start=1):
        ts = readable_timestamp(item.get('timestamp'))
        print(f"--- Item {i} ---")
        print(json.dumps(item, indent=4, default=str))
        print(f"Timestamp legible: {ts}\n")

print("Lectura completa.")