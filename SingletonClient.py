"""
SingletonClient.py
Cliente para interactuar con la base de datos CorporateData a través de SingleProxyObserverTPFI
Ingeniería de Software II - UADER-FCyT-IS2
"""

import socket
import json
import argparse
import sys
import uuid
import platform
from typing import Dict, Any, Optional

class SingletonClient:
    """Cliente Singleton para comunicación con el servidor de base de datos"""
    
    _instance = None
    
    def __new__(cls):
        """Implementación del patrón Singleton"""
        if cls._instance is None:
            cls._instance = super(SingletonClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el cliente si no ha sido inicializado antes"""
        if self._initialized:
            return
        
        self.host = 'localhost'
        self.port = 8080
        self.buffer_size = 8192
        self._initialized = True
    
    def set_connection(self, host: str = 'localhost', port: int = 8080):
        """Configura los parámetros de conexión"""
        self.host = host
        self.port = port
    
    def get_machine_uuid(self) -> str:
        """
        Obtiene un identificador único aleatorio para la máquina.
        """
        return str(uuid.uuid4().hex)
    
    def send_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía una solicitud al servidor y espera respuesta.
        
        Args:
            request_data: Diccionario con los datos de la solicitud
            
        Returns:
            Diccionario con la respuesta del servidor
        """
        try:
            # Crear socket TCP
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Configurar timeout
                sock.settimeout(30)
                
                # Conectar al servidor
                sock.connect((self.host, self.port))
                
                # Serializar y enviar datos
                request_json = json.dumps(request_data, default=str)
                sock.sendall(request_json.encode('utf-8'))
                
                # Recibir respuesta
                response_data = b''
                while True:
                    chunk = sock.recv(self.buffer_size)
                    if not chunk:
                        break
                    response_data += chunk
                    
                    # Intenta decodificar para ver si está completo
                    try:
                        response = json.loads(response_data.decode('utf-8'))
                        return response
                    except json.JSONDecodeError:
                        continue
                
                # Si salimos del loop, intentamos decodificar lo que tenemos
                if response_data:
                    return json.loads(response_data.decode('utf-8'))
                else:
                    return {"Error": "No se recibió respuesta del servidor"}
                
        except socket.timeout:
            return {"Error": "Timeout al conectar con el servidor"}
        except ConnectionRefusedError:
            return {"Error": f"No se pudo conectar al servidor en {self.host}:{self.port}"}
        except Exception as e:
            return {"Error": f"Error de comunicación: {str(e)}"}
    
    def validate_request(self, request_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Valida que la solicitud tenga el formato correcto.
        
        Returns:
            Tupla (válido, mensaje_error)
        """
        # Validar campos obligatorios
        if 'UUID' not in request_data:
            return False, "Falta el campo 'UUID'"
        
        if 'ACTION' not in request_data:
            return False, "Falta el campo 'ACTION'"
        
        action = request_data['ACTION'].lower()
        
        # Validar acción
        if action not in ['get', 'set', 'list']:
            return False, f"Acción inválida: {action}. Debe ser 'get', 'set' o 'list'"
        
        # Validar ID para get y set
        if action in ['get', 'set'] and 'ID' not in request_data:
            return False, f"La acción '{action}' requiere el campo 'ID'"
        
        # Para SET: el ID es obligatorio, pero los demás campos son opcionales
        # Si no se informan, no se modificarán (si existe) o quedarán en blanco (si es nuevo)
        
        return True, ""


def load_input_file(filename: str) -> Optional[Dict[str, Any]]:
    """
    Carga el archivo JSON de entrada.
    
    Args:
        filename: Nombre del archivo de entrada
        
    Returns:
        Diccionario con los datos del archivo o None si hay error
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{filename}'", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: El archivo '{filename}' no es un JSON válido: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error al leer el archivo '{filename}': {e}", file=sys.stderr)
        return None


def save_output_file(filename: str, data: Dict[str, Any]) -> bool:
    """
    Guarda la respuesta en un archivo JSON.
    
    Args:
        filename: Nombre del archivo de salida
        data: Datos a guardar
        
    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, default=str, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error al escribir el archivo '{filename}': {e}", file=sys.stderr)
        return False


def print_response(data: Dict[str, Any], verbose: bool = False):
    """
    Imprime la respuesta en formato legible.
    
    Args:
        data: Datos a imprimir
        verbose: Si es True, imprime información adicional
    """
    if verbose:
        print("=" * 70)
        print("RESPUESTA DEL SERVIDOR")
        print("=" * 70)
    
    print(json.dumps(data, indent=4, default=str, ensure_ascii=False))
    
    if verbose:
        print("=" * 70)


def main():
    """Función principal del cliente"""
    
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(
        description='Cliente para interactuar con CorporateData',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python singletonclient.py -i=input.json
  python singletonclient.py -i=input.json -o=output.json
  python singletonclient.py -i=input.json -o=output.json -v
  python singletonclient.py -i=input.json --host=192.168.1.100 --port=9090
        """
    )
    
    parser.add_argument('-i', '--input', required=True,
                        help='Archivo JSON de entrada (obligatorio)')
    parser.add_argument('-o', '--output', required=False,
                        help='Archivo JSON de salida (opcional, si no se indica se usa stdout)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Modo verbose, muestra información adicional')
    parser.add_argument('--host', default='localhost',
                        help='Host del servidor (default: localhost)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Puerto del servidor (default: 8080)')
    
    args = parser.parse_args()
    
    # Modo verbose
    if args.verbose:
        print(f"SingletonClient - Cliente de CorporateData")
        print(f"Conectando a {args.host}:{args.port}")
        print(f"Leyendo archivo de entrada: {args.input}")
        print()
    
    # Cargar archivo de entrada
    request_data = load_input_file(args.input)
    if request_data is None:
        sys.exit(1)
    
    # Crear instancia del cliente (Singleton)
    client = SingletonClient()
    client.set_connection(args.host, args.port)
    
    # Agregar UUID si no está presente
    if 'UUID' not in request_data:
        request_data['UUID'] = client.get_machine_uuid()
        if args.verbose:
            print(f"UUID de la máquina: {request_data['UUID']}")
    
    # Validar solicitud
    valid, error_msg = client.validate_request(request_data)
    if not valid:
        print(f"Error de validación: {error_msg}", file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print(f"Acción solicitada: {request_data['ACTION']}")
        if 'ID' in request_data:
            print(f"ID del registro: {request_data['ID']}")
        print()
    
    # Enviar solicitud
    if args.verbose:
        print("Enviando solicitud al servidor...")
    
    response = client.send_request(request_data)
    
    if args.verbose:
        print("Respuesta recibida.")
        print()
    
    # Procesar respuesta
    if args.output:
        # Guardar en archivo
        if save_output_file(args.output, response):
            if args.verbose:
                print(f"Respuesta guardada en: {args.output}")
            else:
                print(f"OK: Respuesta guardada en {args.output}")
        else:
            sys.exit(1)
    else:
        # Imprimir en stdout
        print_response(response, args.verbose)
    
    # Verificar si hubo error
    if "Error" in response:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()