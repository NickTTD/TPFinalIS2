import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CorporateLog')

response = table.scan()
items = response.get('Items', [])

# Buscar items CON uuid (tu app)
con_uuid = [i for i in items if 'uuid' in i and '2025-11-05 17' in str(i.get('timestamp', ''))]

print(f"Items de tu app (con 'uuid' y 17:XX): {len(con_uuid)}")
if con_uuid:
    print(f"Primero: {con_uuid[0]}")