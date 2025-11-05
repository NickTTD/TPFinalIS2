#!/usr/bin/env python3
"""
printLog_interactive.py - Visualizador interactivo de logs de CorporateLog
Muestra los 10 elementos más recientes con navegación por páginas
"""

import boto3
import json
from datetime import datetime, timezone
import pytz
import sys
import os

# Detectar SO para limpiar pantalla
CLEAR_CMD = 'clear' if os.name == 'posix' else 'cls'

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

def parse_timestamp(value):
    """Convierte el timestamp a un valor comparable"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        dt = None
        
        try:
            if 'T' in value and ('+' in value or value.endswith('Z')):
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                dt = dt.astimezone(local_tz).replace(tzinfo=None)
                return dt.timestamp()
        except ValueError:
            pass
        
        try:
            dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            dt_aware = dt.replace(tzinfo=local_tz)
            return dt_aware.timestamp()
        except ValueError:
            pass
        
        try:
            dt = datetime.strptime(value.split('.')[0], '%Y-%m-%d %H:%M:%S')
            dt_aware = dt.replace(tzinfo=local_tz)
            return dt_aware.timestamp()
        except ValueError:
            pass
    
    return 0.0

def readable_timestamp(value):
    """Convierte el timestamp a formato legible"""
    dt = None
    
    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value)
    elif isinstance(value, str):
        if 'T' in value and ('+' in value or value.endswith('Z')):
            try:
                dt_aware = datetime.fromisoformat(value.replace('Z', '+00:00'))
                dt = dt_aware.astimezone(local_tz).replace(tzinfo=None)
            except ValueError:
                pass
        
        if dt is None:
            try:
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        if dt is None:
            try:
                dt = datetime.strptime(value.split('.')[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return str(value)
    
    if dt is None:
        return str(value)
    
    now = datetime.now()
    delta = now - dt

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

    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} ({elapsed})"

def display_page(items_sorted, page):
    """Muestra una página de items"""
    os.system(CLEAR_CMD)
    
    items_per_page = 10
    total_pages = (len(items_sorted) + items_per_page - 1) // items_per_page
    
    if page < 0 or page >= total_pages:
        page = 0
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_items = items_sorted[start_idx:end_idx]
    
    print(f"{'='*80}")
    print(f"Registros de '{table.name}' - Página {page + 1}/{total_pages} (Total: {len(items_sorted)} items)")
    print(f"{'='*80}\n")
    
    for i, item in enumerate(page_items, start=start_idx + 1):
        ts = readable_timestamp(item.get('timestamp'))
        print(f"--- Item {i} ---")
        print(json.dumps(item, indent=4, default=str))
        print(f"Timestamp legible: {ts}\n")
    
    print(f"{'='*80}")
    print(f"Página {page + 1}/{total_pages}")
    print("Controles: ↑ Anterior | ↓ Siguiente | Q Salir")
    print(f"{'='*80}")
    
    return page, total_pages

def get_key_press():
    """Obtiene una tecla presionada sin Enter (funciona en Windows y Unix)"""
    if os.name == 'nt':  # Windows
        import msvcrt
        return msvcrt.getch().decode('utf-8', errors='ignore')
    else:  # Linux/Mac
        import tty
        import termios
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

# Programa principal
if not items:
    print("La tabla está vacía.")
    sys.exit(0)

# Ordenar items por timestamp descendente (más recientes primero)
items_sorted = sorted(items, key=lambda x: parse_timestamp(x.get('timestamp')), reverse=True)

page = 0
total_pages = (len(items_sorted) + 9) // 10

while True:
    page, total_pages = display_page(items_sorted, page)
    
    try:
        key = get_key_press().lower()
        
        if key == 'q':
            print("\nSaliendo...")
            break
        elif key == '\x1b':  # Secuencia de escape (flechas)
            next_key = sys.stdin.read(2)
            if next_key == '[A':  # Flecha arriba
                page = max(0, page - 1)
            elif next_key == '[B':  # Flecha abajo
                page = min(total_pages - 1, page + 1)
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario.")
        break
    except Exception as e:
        print(f"\nError: {e}")
        break

print("Lectura completada.")