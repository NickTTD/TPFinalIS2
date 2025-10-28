import boto3
import json
from datetime import datetime

#*-----------------------------------------------------------
#* Conexión a DynamoDB
#*-----------------------------------------------------------
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CorporateLog')

#*-----------------------------------------------------------
#* Leer toda la tabla
#*-----------------------------------------------------------
print(f"Leyendo todos los elementos de la tabla '{table.name}'...\n")

response = table.scan()
items = response.get('Items', [])

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))

#*-----------------------------------------------------------
#* Funciones auxiliares
#*-----------------------------------------------------------
def parse_timestamp(value):
    """Convierte el timestamp a un valor comparable (epoch)."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace(" ", "T")).timestamp()
        except ValueError:
            return 0.0
    return 0.0

def readable_timestamp(value):
    """Convierte el timestamp a formato YYYY-MM-DD HH:MM:SS y tiempo transcurrido."""
    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value)
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace(" ", "T"))
        except ValueError:
            return str(value)
    else:
        return str(value)
    
    now = datetime.now()
    delta = now - dt
    # Formato de tiempo transcurrido
    if delta.days > 0:
        elapsed = f"hace {delta.days} días"
    elif delta.seconds >= 3600:
        elapsed = f"hace {delta.seconds//3600} horas"
    elif delta.seconds >= 60:
        elapsed = f"hace {delta.seconds//60} minutos"
    else:
        elapsed = f"hace {delta.seconds} segundos"
    
    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} ({elapsed})"

#*-----------------------------------------------------------
#* Ordenar y mostrar los 10 más recientes
#*-----------------------------------------------------------
if not items:
    print("La tabla está vacía.")
else:
    items_sorted = sorted(items, key=lambda x: parse_timestamp(x.get('timestamp')), reverse=True)
    top_10 = items_sorted[:10]

    print(f"Mostrando los 10 registros más recientes de '{table.name}':\n")
    for i, item in enumerate(top_10, start=1):
        ts = readable_timestamp(item.get('timestamp'))
        print(f"--- Item {i} ---")
        print(json.dumps(item, indent=4, default=str))
        print(f"Timestamp legible: {ts}\n")

print("Lectura completa.")
