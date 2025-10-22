import boto3
from decimal import Decimal
import json
from boto3.dynamodb.conditions import Key, Attr

#*-----------------------------------------------------------
#* Conexión a DynamoDB
#*-----------------------------------------------------------
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CorporateData')

#*-----------------------------------------------------------
#* Leer toda la tabla
#*-----------------------------------------------------------
print(f"Leyendo todos los elementos de la tabla '{table.name}'...\n")

response = table.scan()
items = response.get('Items', [])

# Si hay más páginas (cuando la tabla es grande)
while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))

#*-----------------------------------------------------------
#* Mostrar resultados
#*-----------------------------------------------------------
if not items:
    print("La tabla está vacía.")
else:
    print(f"Total de registros: {len(items)}\n")
    for i, item in enumerate(items, start=1):
        print(f"--- Item {i} ---")
        print(json.dumps(item, indent=4, default=str))
        print()

print("Lectura completa.")
