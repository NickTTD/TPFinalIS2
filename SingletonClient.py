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
import logging
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
        logging.info(f"Configurada conexión a {self.host}:{self.port}")

    def get_machine_uuid(self) -> str:
        """Obtiene un identificador único aleatorio para la máquina."""
        uuid_str = str(uuid.uuid4().hex)
        logging.debug(f"Generado UUID de máquina: {uuid_str}")
        return uuid_str

    def send_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía una solicitud al servidor y espera respuesta.
        """
        logging.info(f"Enviando solicitud al servidor {self.host}:{self.port} -> {request_data.get('ACTION', '').upper()}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(30)
                sock.connect((self.host, self.port))
                request_json = json.dumps(request_data, default=str)
                sock.sendall(request_json.encode('utf-8'))

                response_data = b''
                while True:
                    chunk = sock.recv(self.buffer_size)
                    if not chunk:
                        break
                    response_data += chunk
                    try:
                        response = json.loads(response_data.decode('utf-8'))
                        logging.debug(f"Respuesta parcial recibida: {response}")
                        return response
                    except json.JSONDecodeError:
                        continue

                if response_data:
                    response = json.loads(response_data.decode('utf-8'))
                    logging.debug(f"Respuesta final recibida: {response}")
                    return response
                else:
                    logging.error("No se recibió respuesta del servidor")
                    return {"Error": "No se recibió respuesta del servidor"}

        except socket.timeout:
            logging.error("Timeout al conectar con el servidor")
            return {"Error": "Timeout al conectar con el servidor"}
        except ConnectionRefusedError:
            logging.error(f"No se pudo conectar al servidor en {self.host}:{self.port}")
            return {"Error": f"No se pudo conectar al servidor en {self.host}:{self.port}"}
        except Exception as e:
            logging.exception("Error de comunicación")
            return {"Error": f"Error de comunicación: {str(e)}"}

    def validate_request(self, request_data: Dict[str, Any]) -> tuple[bool, str]:
        """Valida que la solicitud tenga el formato correcto."""
        if 'UUID' not in request_data:
            return False, "Falta el campo 'UUID'"

        if 'ACTION' not in request_data:
            return False, "Falta el campo 'ACTION'"

        action = request_data['ACTION'].lower()
        if action not in ['get', 'set', 'list']:
            return False, f"Acción inválida: {action}. Debe ser 'get', 'set' o 'list'"

        if action in ['get', 'set'] and 'ID' not in request_data:
            return False, f"La acción '{action}' requiere el campo 'ID'"

        logging.debug(f"Solicitud validada correctamente: {action.upper()}")
        return True, ""


def load_input_file(filename: str) -> Optional[Dict[str, Any]]:
    """Carga el archivo JSON de entrada."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.info(f"Archivo de entrada '{filename}' cargado correctamente")
        return data
    except FileNotFoundError:
        logging.error(f"No se encontró el archivo '{filename}'")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"El archivo '{filename}' no es un JSON válido: {e}")
        return None
    except Exception as e:
        logging.exception(f"Error al leer el archivo '{filename}'")
        return None


def save_output_file(filename: str, data: Dict[str, Any]) -> bool:
    """Guarda la respuesta en un archivo JSON."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, default=str, ensure_ascii=False)
        logging.info(f"Archivo de salida '{filename}' guardado correctamente")
        return True
    except Exception as e:
        logging.exception(f"Error al escribir el archivo '{filename}'")
        return False


def print_response(data: Dict[str, Any], verbose: bool = False):
    """Imprime la respuesta en formato legible."""
    if verbose:
        logging.debug("Mostrando respuesta del servidor en modo verbose:")
        print("=" * 70)
        print("RESPUESTA DEL SERVIDOR")
        print("=" * 70)

    print(json.dumps(data, indent=4, default=str, ensure_ascii=False))

    if verbose:
        print("=" * 70)


def main():
    """Función principal del cliente"""

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

    parser.add_argument('-i', '--input', required=True, help='Archivo JSON de entrada (obligatorio)')
    parser.add_argument('-o', '--output', required=False, help='Archivo JSON de salida (opcional)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Modo verbose, muestra información adicional')
    parser.add_argument('--host', default='localhost', help='Host del servidor (default: localhost)')
    parser.add_argument('--port', type=int, default=8080, help='Puerto del servidor (default: 8080)')

    args = parser.parse_args()

    # Configurar logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info("=== Inicio de SingletonClient ===")
    logging.info(f"Host: {args.host} | Puerto: {args.port}")
    logging.info(f"Archivo de entrada: {args.input}")

    request_data = load_input_file(args.input)
    if request_data is None:
        sys.exit(1)

    client = SingletonClient()
    client.set_connection(args.host, args.port)

    if 'UUID' not in request_data:
        request_data['UUID'] = client.get_machine_uuid()
        logging.debug(f"UUID agregado a la solicitud: {request_data['UUID']}")

    valid, error_msg = client.validate_request(request_data)
    if not valid:
        logging.error(f"Error de validación: {error_msg}")
        sys.exit(1)

    logging.info(f"Ejecutando acción: {request_data['ACTION'].upper()}")
    if 'ID' in request_data:
        logging.debug(f"ID del registro: {request_data['ID']}")

    response = client.send_request(request_data)
    logging.info("Respuesta recibida del servidor")

    if args.output:
        if save_output_file(args.output, response):
            logging.info(f"Respuesta guardada en archivo: {args.output}")
        else:
            logging.error("Error al guardar la respuesta en archivo")
            sys.exit(1)
    else:
        print_response(response, args.verbose)

    if "Error" in response:
        logging.error(f"El servidor devolvió un error: {response['Error']}")
        sys.exit(1)

    logging.info("=== Ejecución finalizada correctamente ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
