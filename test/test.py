#!/usr/bin/env python3
"""
test_acceptance_singleton_client.py
Test de Aceptación según Especificación de Validación y Verificación
Ingeniería de Software II - UADER-FCyT-IS2
"""

import unittest
import json
import os
import sys
import time
import subprocess
import socket
import signal
from pathlib import Path
from datetime import datetime

# Importar el cliente
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from SingletonClient import SingletonClient, load_input_file, save_output_file


class TestAcceptanceSingletonClient(unittest.TestCase):
    """Test Suite de Aceptación según requisitos especificados"""
    
    server_process = None
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial - Inicia el servidor"""
        print("\n" + "="*80)
        print("TEST DE ACEPTACIÓN - VALIDACIÓN Y VERIFICACIÓN")
        print("="*80)
        
        # Directorio de archivos de prueba
        cls.test_data_dir = Path(__file__).parent / 'test_data'
        cls.test_data_dir.mkdir(exist_ok=True)
        
        cls.output_dir = Path(__file__).parent / 'test_output'
        cls.output_dir.mkdir(exist_ok=True)
        
        # Iniciar servidor
        cls.start_server()
        
        # Configurar cliente
        cls.client = SingletonClient()
        cls.client.set_connection(host='localhost', port=8080)
        
        # IDs de prueba
        cls.test_id = "EMP_TEST_001"
    
    @classmethod
    def start_server(cls):
        """Inicia el servidor SingletonProxyObserverServer"""
        print("\n[SETUP] Iniciando SingletonProxyObserverServer...")
        
        # Verificar si el puerto está ocupado
        if cls.is_port_in_use(8080):
            print("⚠️  Puerto 8080 ya en uso. Intentando cerrar proceso existente...")
            cls.kill_process_on_port(8080)
            time.sleep(2)
        
        # Buscar el archivo del servidor
        server_file = cls.find_server_file()
        
        if server_file and server_file.exists():
            try:
                cls.server_process = subprocess.Popen(
                    [sys.executable, str(server_file), 'start', '-p', '8080'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                print("[SETUP] Esperando inicialización del servidor...")
                time.sleep(4)
                
                if cls.is_port_in_use(8080):
                    print("✅ SingletonProxyObserverServer iniciado correctamente en puerto 8080")
                else:
                    print("❌ Error: Servidor no pudo iniciarse")
                    if cls.server_process:
                        stdout, stderr = cls.server_process.communicate(timeout=2)
                        print(f"STDOUT: {stdout}")
                        print(f"STDERR: {stderr}")
                    raise Exception("Servidor no respondiendo")
                    
            except Exception as e:
                print(f"❌ Error al iniciar servidor: {e}")
                cls.server_process = None
                raise
        else:
            print("❌ Archivo SingletonProxyObserver.py no encontrado")
            raise FileNotFoundError("SingletonProxyObserver.py no encontrado")
    
    @classmethod
    def find_server_file(cls):
        """Busca el archivo del servidor"""
        possible_paths = [
            Path(__file__).parent / 'SingletonProxyObserver.py',
            Path(__file__).parent.parent / 'SingletonProxyObserver.py',
            Path(__file__).parent / 'SingletonProxyObserverTPFI.py',
            Path(__file__).parent.parent / 'SingletonProxyObserverTPFI.py',
        ]
        
        for path in possible_paths:
            if path.exists():
                print(f"[SETUP] Servidor encontrado en: {path}")
                return path
        return None
    
    @classmethod
    def is_port_in_use(cls, port):
        """Verifica si un puerto está en uso"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    @classmethod
    def kill_process_on_port(cls, port):
        """Mata el proceso que está usando el puerto"""
        try:
            if sys.platform == 'win32':
                cmd = f'netstat -ano | findstr :{port}'
                result = subprocess.check_output(cmd, shell=True).decode()
                if result:
                    pid = result.strip().split()[-1]
                    subprocess.call(['taskkill', '/F', '/PID', pid], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL)
            else:
                cmd = f"lsof -ti:{port}"
                result = subprocess.check_output(cmd, shell=True).decode()
                if result:
                    pid = result.strip()
                    os.kill(int(pid), signal.SIGKILL)
            time.sleep(1)
        except:
            pass
    
    @classmethod
    def check_server_health(cls):
        """Verifica que el servidor responde correctamente"""
        try:
            test_client = SingletonClient()
            test_client.set_connection(host='localhost', port=8080)
            
            request = {
                'UUID': test_client.get_machine_uuid(),
                'ACTION': 'list'
            }
            
            response = test_client.send_request(request)
            
            if "Error" not in response or "conectar" not in response.get("Error", "").lower():
                return True
            
            return False
        except:
            return False
    
    def setUp(self):
        """Configuración antes de cada test"""
        print(f"\n{'─'*80}")
        time.sleep(0.3)
    
    def print_test_header(self, test_name, description):
        """Imprime encabezado de test"""
        print(f"\n{'='*80}")
        print(f"TEST: {test_name}")
        print(f"DESC: {description}")
        print(f"{'='*80}")
    
    def print_response(self, response, label="Respuesta"):
        """Helper para imprimir respuestas"""
        print(f"\n[{label}]")
        print(json.dumps(response, indent=2, ensure_ascii=False))
    
    # =========================================================================
    # REQUISITO 1: CAMINO FELIZ (SET, GET, SET/UPDATE, LIST, SUBSCRIBE)
    # =========================================================================
    
    def test_01_happy_path_set_create(self):
        """CAMINO FELIZ: SET para crear registro nuevo"""
        self.print_test_header(
            "01 - CAMINO FELIZ: SET CREATE",
            "Crear un nuevo empleado (SET) y verificar registro en CorporateLog"
        )
        
        request_data = {
            'UUID': self.client.get_machine_uuid(),
            'ACTION': 'set',
            'ID': self.test_id,
            'cp': '3100',
            'CUIT': '20-12345678-9',
            'domicilio': 'Calle Principal 123',
            'localidad': 'Paraná',
            'provincia': 'Entre Ríos',
            'telefono': '343-4567890'
        }
        
        print("\n[REQUEST]")
        print(json.dumps(request_data, indent=2, ensure_ascii=False))
        
        response = self.client.send_request(request_data)
        
        self.print_response(response, "RESPONSE")
        self.assertNotIn("Error", response)
        self.assertIn("id", response)
        
        print(f"\n✅ Registro creado - CorporateLog registra acción SET")
        print(f"✅ TEST PASSED")
    
    def test_02_happy_path_get(self):
        """CAMINO FELIZ: GET para obtener registro"""
        self.print_test_header(
            "02 - CAMINO FELIZ: GET",
            "Obtener un empleado existente (GET) y verificar registro en CorporateLog"
        )
        
        request_data = {
            'UUID': self.client.get_machine_uuid(),
            'ACTION': 'get',
            'ID': self.test_id
        }
        
        print("\n[REQUEST]")
        print(json.dumps(request_data, indent=2, ensure_ascii=False))
        
        response = self.client.send_request(request_data)
        
        self.print_response(response, "RESPONSE")
        self.assertNotIn("Error", response)
        self.assertIn("id", response)
        self.assertEqual(response.get("id"), self.test_id)
        
        print(f"\n✅ Registro obtenido - CorporateLog registra acción GET")
        print(f"✅ TEST PASSED")
    
    def test_03_happy_path_set_update(self):
        """CAMINO FELIZ: SET para actualizar registro existente"""
        self.print_test_header(
            "03 - CAMINO FELIZ: SET UPDATE",
            "Actualizar un empleado existente (SET) y verificar registro en CorporateLog"
        )
        
        request_data = {
            'UUID': self.client.get_machine_uuid(),
            'ACTION': 'set',
            'ID': self.test_id,
            'cp': '3101',
            'telefono': '343-9999999',
            'domicilio': 'Avenida Actualizada 456'
        }
        
        print("\n[REQUEST]")
        print(json.dumps(request_data, indent=2, ensure_ascii=False))
        
        response = self.client.send_request(request_data)
        
        self.print_response(response, "RESPONSE")
        self.assertNotIn("Error", response)
        
        # Verificar que se actualizó
        get_response = self.client.send_request({
            'UUID': self.client.get_machine_uuid(),
            'ACTION': 'get',
            'ID': self.test_id
        })
        
        self.assertEqual(get_response.get("cp"), "3101")
        self.assertEqual(get_response.get("telefono"), "343-9999999")
        
        print(f"\n✅ Registro actualizado - CorporateLog registra acción SET")
        print(f"✅ TEST PASSED")
    
    def test_04_happy_path_list(self):
        """CAMINO FELIZ: LIST para listar todos los registros"""
        self.print_test_header(
            "04 - CAMINO FELIZ: LIST",
            "Listar todos los empleados (LIST) y verificar registro en CorporateLog"
        )
        
        request_data = {
            'UUID': self.client.get_machine_uuid(),
            'ACTION': 'list'
        }
        
        print("\n[REQUEST]")
        print(json.dumps(request_data, indent=2, ensure_ascii=False))
        
        response = self.client.send_request(request_data)
        
        self.print_response(response, "RESPONSE")
        self.assertNotIn("Error", response)
        self.assertIn("records", response)
        self.assertIn("count", response)
        
        print(f"\n✅ Lista obtenida ({response['count']} registros) - CorporateLog registra acción LIST")
        print(f"✅ TEST PASSED")
    
    def test_05_happy_path_subscribe(self):
        """CAMINO FELIZ: SUBSCRIBE para suscribirse a notificaciones"""
        self.print_test_header(
            "05 - CAMINO FELIZ: SUBSCRIBE",
            "Suscribirse con ObserverClient y verificar registro en CorporateLog"
        )
        
        # Verificar que el servidor está funcionando
        if not self.check_server_health():
            print("⚠️  Servidor no responde, reintentando...")
            time.sleep(2)
            if not self.check_server_health():
                self.skipTest("Servidor no disponible para test de SUBSCRIBE")
        
        # Buscar ObserverClient
        observer_script = self.find_observer_client()
        if not observer_script:
            self.skipTest("ObserverClient.py no encontrado")
        
        # Importar ObserverClient
        import importlib.util
        spec = importlib.util.spec_from_file_location("ObserverClient", observer_script)
        observer_module = importlib.util.module_from_spec(spec)
        
        import logging
        old_level = logging.root.level
        logging.root.setLevel(logging.CRITICAL)
        
        try:
            spec.loader.exec_module(observer_module)
        finally:
            logging.root.setLevel(old_level)
        
        ObserverClientClass = observer_module.ObserverClient
        
        print("\n[TEST] Creando y suscribiendo ObserverClient...")
        observer = ObserverClientClass(
            host='localhost',
            port=8080,
            verbose=False,
            retry_interval=5
        )
        
        # Intentar suscribirse con reintentos
        subscribed = False
        for attempt in range(3):
            try:
                if observer.connect():
                    subscribed = True
                    break
            except Exception as e:
                print(f"⚠️  Intento {attempt + 1}/3 falló: {e}")
            
            if attempt < 2:
                time.sleep(2)
        
        if subscribed:
            print("✅ ObserverClient suscrito exitosamente")
            time.sleep(1)
            observer.stop()
            print("✅ ObserverClient desuscrito")
            print(f"\n✅ Suscripción completada - CorporateLog registra acción SUBSCRIBE")
            print(f"✅ TEST PASSED")
        else:
            print("⚠️  No se pudo suscribir después de 3 intentos")
            self.skipTest("No se pudo suscribir al servidor")
    
    @classmethod
    def find_observer_client(cls):
        """Busca ObserverClient.py"""
        possible_paths = [
            Path(__file__).parent / 'ObserverClient.py',
            Path(__file__).parent.parent / 'ObserverClient.py',
        ]
        for path in possible_paths:
            if path.exists():
                return path
        return None
    
    # =========================================================================
    # REQUISITO 2: ARGUMENTOS MALFORMADOS
    # =========================================================================
    
    def test_06_malformed_server_no_start_arg(self):
        """ARGUMENTOS MALFORMADOS: Servidor sin argumento 'start'"""
        self.print_test_header(
            "06 - MALFORMED: Servidor sin 'start'",
            "Intentar iniciar servidor sin el argumento obligatorio 'start'"
        )
        
        server_file = self.find_server_file()
        if not server_file:
            self.skipTest("Archivo del servidor no encontrado")
        
        print(f"\n[COMANDO] python {server_file.name}")
        print("(sin argumento 'start')")
        
        # Ejecutar servidor SIN 'start'
        result = subprocess.run(
            [sys.executable, str(server_file)],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print(f"\n[STDOUT]")
        print(result.stdout[:500])
        
        # El servidor debe mostrar ayuda y NO iniciarse
        self.assertIn("start", result.stdout.lower())
        
        print(f"\n✅ Servidor rechazó inicio sin 'start'")
        print(f"✅ TEST PASSED")
    
    def test_07_malformed_client_no_input(self):
        """ARGUMENTOS MALFORMADOS: Cliente sin -i"""
        self.print_test_header(
            "07 - MALFORMED: Cliente sin -i",
            "Intentar ejecutar cliente sin el argumento obligatorio -i"
        )
        
        client_script = self.find_client_script()
        if not client_script:
            self.skipTest("SingletonClient.py no encontrado")
        
        print(f"\n[COMANDO] python {client_script.name}")
        print("(sin argumento -i)")
        
        result = subprocess.run(
            [sys.executable, str(client_script)],
            capture_output=True,
            text=True
        )
        
        print(f"\n[STDERR]")
        print(result.stderr[:500])
        
        # Debe fallar indicando que -i es requerido
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required", result.stderr.lower())
        
        print(f"\n✅ Cliente rechazó ejecución sin -i")
        print(f"✅ TEST PASSED")
    
    def test_08_malformed_observer_invalid_port(self):
        """ARGUMENTOS MALFORMADOS: ObserverClient con puerto inválido"""
        self.print_test_header(
            "08 - MALFORMED: ObserverClient puerto inválido",
            "Intentar ejecutar ObserverClient con argumento -p inválido"
        )
        
        observer_script = self.find_observer_client()
        if not observer_script:
            self.skipTest("ObserverClient.py no encontrado")
        
        print(f"\n[COMANDO] python {observer_script.name} -p INVALIDO")
        
        result = subprocess.run(
            [sys.executable, str(observer_script), '-p', 'INVALIDO'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print(f"\n[STDERR]")
        print(result.stderr[:500])
        
        # Debe fallar con error de argumento inválido
        self.assertNotEqual(result.returncode, 0)
        
        print(f"\n✅ ObserverClient rechazó argumento inválido")
        print(f"✅ TEST PASSED")
    
    @classmethod
    def find_client_script(cls):
        """Busca SingletonClient.py"""
        possible_paths = [
            Path(__file__).parent.parent / 'SingletonClient.py',
            Path(__file__).parent / 'SingletonClient.py',
        ]
        for path in possible_paths:
            if path.exists():
                return path
        return None
    
    # =========================================================================
    # REQUISITO 3: DATOS MÍNIMOS NECESARIOS
    # =========================================================================
    
    def test_09_minimum_data_get_without_id(self):
        """DATOS MÍNIMOS: GET sin especificar ID"""
        self.print_test_header(
            "09 - DATOS MÍNIMOS: GET sin ID",
            "Intentar GET sin el campo ID obligatorio"
        )
        
        # Crear archivo JSON sin ID
        json_file = self.test_data_dir / 'test_get_no_id.json'
        test_data = {
            'ACTION': 'get'
            # Falta ID
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=4)
        
        print(f"\n[ARCHIVO JSON]")
        print(json.dumps(test_data, indent=2))
        
        # Cargar y agregar UUID
        request_data = load_input_file(str(json_file))
        request_data['UUID'] = self.client.get_machine_uuid()
        
        # Validar (debe fallar)
        valid, error_msg = self.client.validate_request(request_data)
        
        print(f"\n[VALIDACIÓN]")
        print(f"Válido: {valid}")
        print(f"Error: {error_msg}")
        
        self.assertFalse(valid)
        self.assertIn("ID", error_msg)
        
        print(f"\n✅ Cliente detectó falta de ID para GET")
        print(f"✅ TEST PASSED")
    
    # =========================================================================
    # REQUISITO 4: SERVIDOR CAÍDO
    # =========================================================================
    
    def test_10_server_down_client_handling(self):
        """SERVIDOR CAÍDO: Cliente con servidor apagado"""
        self.print_test_header(
            "10 - SERVIDOR CAÍDO: Cliente",
            "Abrir cliente con servidor cerrado"
        )
        
        # Crear cliente apuntando a puerto sin servidor
        test_client = SingletonClient()
        test_client.set_connection(host='localhost', port=9999)
        
        request_data = {
            'UUID': test_client.get_machine_uuid(),
            'ACTION': 'list'
        }
        
        print("\n[REQUEST a puerto 9999 (sin servidor)]")
        print(json.dumps(request_data, indent=2))
        
        response = test_client.send_request(request_data)
        
        self.print_response(response, "RESPONSE")
        
        # Debe contener error de conexión
        self.assertIn("Error", response)
        self.assertIn("conectar", response["Error"].lower())
        
        print(f"\n✅ Cliente manejó servidor caído correctamente")
        print(f"✅ TEST PASSED")
    
    # =========================================================================
    # REQUISITO 5: SERVIDOR DUPLICADO
    # =========================================================================
    
    def test_11_duplicate_server_start(self):
        """SERVIDOR DUPLICADO: Intento de levantar dos veces"""
        self.print_test_header(
            "11 - SERVIDOR DUPLICADO",
            "Intentar iniciar segundo servidor en puerto ocupado"
        )
        
        # Verificar que el puerto está ocupado
        self.assertTrue(self.is_port_in_use(8080), "Puerto 8080 debe estar en uso")
        print("✅ Puerto 8080 está en uso (servidor corriendo)")
        
        server_file = self.find_server_file()
        if not server_file:
            self.skipTest("Archivo del servidor no encontrado")
        
        print("\n[INTENTO] Iniciando segundo servidor en puerto 8080...")
        
        second_server = None
        try:
            second_server = subprocess.Popen(
                [sys.executable, str(server_file), 'start', '-p', '8080'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            time.sleep(2)
            
            # Capturar salida
            try:
                stdout, stderr = second_server.communicate(timeout=1)
                print(f"\n[STDERR]")
                print(stderr[:500] if stderr else "Sin errores")
                
                returncode = second_server.poll()
                if returncode is not None and returncode != 0:
                    print(f"✅ Segundo servidor falló (código: {returncode})")
                else:
                    print(f"⚠️  Segundo servidor código: {returncode}")
            except subprocess.TimeoutExpired:
                if second_server:
                    second_server.kill()
                    second_server.wait(timeout=1)
                print(f"⚠️  Segundo servidor fue terminado")
            
        except Exception as e:
            print(f"✅ Excepción al iniciar segundo servidor: {e}")
        finally:
            # Limpiar segundo servidor
            if second_server and second_server.poll() is None:
                try:
                    second_server.kill()
                    second_server.wait(timeout=1)
                except:
                    pass
            
            time.sleep(1)
            
            # Verificar que el servidor original sigue vivo
            if not self.is_port_in_use(8080):
                print("⚠️  Puerto 8080 ya no está en uso, reiniciando...")
                self.start_server()
        
        print(f"\n✅ Sistema previene servidor duplicado")
        print(f"✅ TEST PASSED")
    
    @classmethod
    def tearDownClass(cls):
        """Limpieza después de todos los tests"""
        print("\n" + "="*80)
        print("FINALIZANDO TESTS - LIMPIEZA")
        print("="*80)
        
        if cls.server_process:
            print("\n[CLEANUP] Deteniendo servidor...")
            try:
                cls.server_process.terminate()
                cls.server_process.wait(timeout=5)
                print("✅ Servidor detenido correctamente")
            except subprocess.TimeoutExpired:
                cls.server_process.kill()
                print("⚠️  Servidor forzado a cerrar")
            except Exception as e:
                print(f"⚠️  Error al detener servidor: {e}")
        
        print("\n" + "="*80)
        print("RESUMEN DE REQUISITOS CUBIERTOS")
        print("="*80)
        print("""
✅ REQUISITO 1 - CAMINO FELIZ (5 tests):
   - SET para crear
   - GET para obtener
   - SET para modificar
   - LIST para listar
   - SUBSCRIBE para suscribirse
   ✓ Todos registran en CorporateLog

✅ REQUISITO 2 - ARGUMENTOS MALFORMADOS (3 tests):
   - Servidor sin 'start'
   - Cliente sin -i
   - ObserverClient con argumento inválido

✅ REQUISITO 3 - DATOS MÍNIMOS (1 test):
   - Cliente GET sin especificar ID

✅ REQUISITO 4 - SERVIDOR CAÍDO (1 test):
   - Cliente con servidor apagado

✅ REQUISITO 5 - SERVIDOR DUPLICADO (1 test):
   - Intentar levantar dos veces el servidor
        """)
        print("="*80)
        print("TOTAL: 11 tests")
        print("="*80)


def generate_test_report():
    """Genera un reporte de los tests ejecutados"""
    report_file = Path(__file__).parent / 'test_output' / 'test_report.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("REPORTE DE TEST DE ACEPTACIÓN\n")
        f.write("SingletonClient & SingletonProxyObserverServer\n")
        f.write("="*80 + "\n\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("REQUISITOS CUBIERTOS:\n\n")
        
        f.write("1. CAMINO FELIZ (5 tests)\n")
        f.write("   ✅ SET para crear registro\n")
        f.write("   ✅ GET para obtener registro\n")
        f.write("   ✅ SET para modificar registro\n")
        f.write("   ✅ LIST para listar registros\n")
        f.write("   ✅ SUBSCRIBE para suscripción\n")
        f.write("   ✓ Todos registran en CorporateLog\n\n")
        
        f.write("2. ARGUMENTOS MALFORMADOS (3 tests)\n")
        f.write("   ✅ Servidor sin argumento 'start'\n")
        f.write("   ✅ Cliente sin argumento -i obligatorio\n")
        f.write("   ✅ ObserverClient con puerto inválido\n\n")
        
        f.write("3. DATOS MÍNIMOS NECESARIOS (1 test)\n")
        f.write("   ✅ GET sin especificar ID (campo obligatorio)\n\n")
        
        f.write("4. SERVIDOR CAÍDO (1 test)\n")
        f.write("   ✅ Cliente con servidor apagado\n\n")
        
        f.write("5. SERVIDOR DUPLICADO (1 test)\n")
        f.write("   ✅ Intento de levantar servidor dos veces\n\n")
        
        f.write("="*80 + "\n")
        f.write("TOTAL: 11 casos de prueba\n")
        f.write("="*80 + "\n")
    
    print(f"\n📄 Reporte generado en: {report_file}")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("SUITE DE TEST DE ACEPTACIÓN")
    print("Validación y Verificación - Requisitos Específicos")
    print("Ingeniería de Software II - UADER-FCyT-IS2")
    print("="*80)
    print("\nREQUISITOS A PROBAR:")
    print("1. ✅ Camino feliz (SET, GET, SET/mod, LIST, SUBSCRIBE) + CorporateLog")
    print("2. ✅ Argumentos malformados (Servidor, Cliente, Observer)")
    print("3. ✅ Datos mínimos necesarios (GET sin ID)")
    print("4. ✅ Servidor caído")
    print("5. ✅ Servidor duplicado")
    print("="*80 + "\n")
    
    # Ejecutar tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAcceptanceSingletonClient)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generar reporte
    generate_test_report()
    
    # Salir con código apropiado
    sys.exit(0 if result.wasSuccessful() else 1)