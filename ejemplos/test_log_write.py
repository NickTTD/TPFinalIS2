import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
log_table = dynamodb.Table('CorporateLog')

test_item = {
    'id': 'test-123',
    'uuid': 'uuid-test',
    'session': 'session-test',
    'action': 'test',
    'timestamp': '2025-11-05T16:55:57.644407',
    'record_id': 'MFND-001'
}

try:
    response = log_table.put_item(Item=test_item)
    print("✓ Escritura exitosa")
    print(f"Response: {response}")
    
    # Verificar que se grabó
    get_response = log_table.get_item(Key={'id': 'test-123'})
    if 'Item' in get_response:
        print("✓ Item verificado en BD")
        print(f"Item: {get_response['Item']}")
    else:
        print("✗ Item NO encontrado después de escribir")
        
except Exception as e:
    print(f"✗ Error al escribir: {e}")