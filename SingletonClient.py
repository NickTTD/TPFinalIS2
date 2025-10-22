#!/usr/bin/env python3
"""
setup_dynamodb_tables.py
Script para crear las tablas necesarias en DynamoDB
"""

import boto3
from botocore.exceptions import ClientError

def create_corporate_data_table():
    """Crea la tabla CorporateData"""
    dynamodb = boto3.resource('dynamodb')
    
    try:
        table = dynamodb.create_table(
            TableName='CorporateData',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand, sin necesidad de provisionar capacidad
        )
        
        print("Creando tabla CorporateData...")
        table.wait_until_exists()
        print("✓ Tabla CorporateData creada exitosamente")
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("✓ Tabla CorporateData ya existe")
            return True
        else:
            print(f"✗ Error al crear tabla CorporateData: {e}")
            return False


def create_corporate_log_table():
    """Crea la tabla CorporateLog"""
    dynamodb = boto3.resource('dynamodb')
    
    try:
        table = dynamodb.create_table(
            TableName='CorporateLog',
            KeySchema=[
                {
                    'AttributeName': 'log_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'log_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'uuid',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'uuid-timestamp-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'uuid',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print("Creando tabla CorporateLog...")
        table.wait_until_exists()
        print("✓ Tabla CorporateLog creada exitosamente")
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("✓ Tabla CorporateLog ya existe")
            return True
        else:
            print(f"✗ Error al crear tabla CorporateLog: {e}")
            return False


def insert_sample_data():
    """Inserta datos de ejemplo en CorporateData"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('CorporateData')
    
    sample_records = [
        {
            "id": "UADER-FCyT-IS2",
            "cp": "3260",
            "CUIT": "30-70925411-8",
            "domicilio": "25 de Mayo 385-1P",
            "idreq": "473",
            "idSeq": "1146",
            "localidad": "Concepción del Uruguay",
            "provincia": "Entre Rios",
            "sede": "FCyT",
            "seqID": "23",
            "telefono": "03442 43-1442",
            "web": "http://www.uader.edu.ar"
        },
        {
            "id": "UTN-FRP-001",
            "cp": "3100",
            "CUIT": "30-52653875-5",
            "domicilio": "Almafuerte 1033",
            "idreq": "100",
            "idSeq": "500",
            "localidad": "Paraná",
            "provincia": "Entre Ríos",
            "sede": "Facultad Regional Paraná",
            "seqID": "10",
            "telefono": "0343 422-4096",
            "web": "https://www.frp.utn.edu.ar"
        },
        {
            "id": "MUNI-CDU-001",
            "cp": "3260",
            "CUIT": "30-67890123-4",
            "domicilio": "Supremo Entrerriano 101",
            "idreq": "250",
            "idSeq": "800",
            "localidad": "Concepción del Uruguay",
            "provincia": "Entre Ríos",
            "sede": "Palacio Municipal",
            "seqID": "15",
            "telefono": "03442 42-5400",
            "web": "https://www.cdeluruguay.gob.ar"
        }
    ]
    
    print("\nInsertando datos de ejemplo...")
    
    try:
        for record in sample_records:
            table.put_item(Item=record)
            print(f"✓ Registro insertado: {record['id']}")
        
        print(f"\n✓ Se insertaron {len(sample_records)} registros de ejemplo")
        return True
        
    except Exception as e:
        print(f"✗ Error al insertar datos de ejemplo: {e}")
        return False


def verify_tables():
    """Verifica que las tablas existan y muestra su estado"""
    dynamodb = boto3.client('dynamodb')
    
    print("\n" + "="*70)
    print("VERIFICACIÓN DE TABLAS")
    print("="*70)
    
    tables = ['CorporateData', 'CorporateLog']
    
    for table_name in tables:
        try:
            response = dynamodb.describe_table(TableName=table_name)
            table_info = response['Table']
            
            print(f"\nTabla: {table_name}")
            print(f"  Estado: {table_info['TableStatus']}")
            print(f"  Registros: {table_info['ItemCount']}")
            print(f"  Partition Key: {table_info['KeySchema'][0]['AttributeName']}")
            
            if 'GlobalSecondaryIndexes' in table_info:
                print(f"  Índices secundarios: {len(table_info['GlobalSecondaryIndexes'])}")
        
        except ClientError as e:
            print(f"\n✗ Tabla {table_name} no encontrada: {e}")


def main():
    """Función principal"""
    print("="*70)
    print("CONFIGURACIÓN DE TABLAS DYNAMODB")
    print("="*70)
    print()
    
    # Crear tablas
    success_data = create_corporate_data_table()
    success_log = create_corporate_log_table()
    
    if not (success_data and success_log):
        print("\n✗ Hubo errores al crear las tablas")
        return
    
    # Insertar datos de ejemplo
    print("\n¿Desea insertar datos de ejemplo? (s/n): ", end='')
    response = input().strip().lower()
    
    if response == 's':
        insert_sample_data()
    
    # Verificar tablas
    verify_tables()
    
    print("\n" + "="*70)
    print("✓ Configuración completada")
    print("="*70)
    print("\nPuede iniciar el servidor con:")
    print("  python SingletonProxyObserverTPFI.py")
    print("  python SingletonProxyObserverTPFI.py -p 8080 -v")
    print()


if __name__ == '__main__':
    main()