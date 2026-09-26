#!/usr/bin/env python3
"""
Credential & Connectivity Verification Tool for Microservices Infrastructure.
Supports custom parameter overrides via CLI flags or reads automatically from service .env / .env.example.
"""

import os
import sys
import argparse
import socket
import struct
import urllib.request
import urllib.error
import subprocess
from pathlib import Path

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

def load_env_file(filepath):
    """Loads key-value pairs from a .env file into a dict."""
    env = {}
    if not os.path.isfile(filepath):
        return env
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env

def find_service_env(script_dir):
    service_dir = Path(script_dir).parent
    env_path = service_dir / ".env"
    example_path = service_dir / ".env.example"
    
    env_vars = {}
    if example_path.is_file():
        env_vars.update(load_env_file(example_path))
    if env_path.is_file():
        env_vars.update(load_env_file(env_path))
    return env_vars, service_dir.name

def print_check(name, success, message, details=None):
    badge = f"{GREEN}[PASS]{RESET}" if success else f"{RED}[FAIL]{RESET}"
    print(f"  {badge} {BOLD}{name}{RESET} -> {message}")
    if details and not success:
        print(f"         {YELLOW}Details:{RESET} {details}")
    return success

def test_postgres(host, port, user, password, dbname, container_name=None):
    # 1. First test TCP connectivity
    try:
        s = socket.create_connection((host, int(port)), timeout=3)
        s.close()
    except Exception as e:
        return print_check("PostgreSQL / AlloyDB", False, f"Cannot connect to {host}:{port}", str(e))

    # 2. Try testing query via local psql or docker container exec
    # Try psql directly if installed
    if subprocess.run(["which", "psql"], capture_output=True).returncode == 0:
        env = os.environ.copy()
        env["PGPASSWORD"] = password
        cmd = ["psql", "-h", host, "-p", str(port), "-U", user, "-d", dbname, "-c", "SELECT 1;"]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return print_check("PostgreSQL / AlloyDB", True, f"Authentication succeeded on {host}:{port}/{dbname} (User: '{user}')")
        else:
            return print_check("PostgreSQL / AlloyDB", False, f"Authentication failed on {host}:{port}/{dbname}", res.stderr.strip())

    # Fallback to docker exec if container_name is provided or running
    if container_name:
        cmd = [
            "docker", "exec", "-e", f"PGPASSWORD={password}", container_name,
            "psql", "-U", user, "-d", dbname, "-c", "SELECT 'AUTH_OK' as status;"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and "AUTH_OK" in res.stdout:
            return print_check("PostgreSQL / AlloyDB", True, f"Authentication & Query succeeded on {host}:{port}/{dbname} (User: '{user}')")
        else:
            return print_check("PostgreSQL / AlloyDB", False, f"Query failed on container {container_name}", res.stderr.strip() or res.stdout.strip())

    return print_check("PostgreSQL / AlloyDB", True, f"Port {host}:{port} reachable (TCP level confirmed)")

def test_redis(host, port, password):
    try:
        s = socket.create_connection((host, int(port)), timeout=3)
        if password:
            auth_cmd = f"*2\r\n$4\r\nAUTH\r\n${len(password)}\r\n{password}\r\n".encode()
            s.sendall(auth_cmd)
            resp = s.recv(1024).decode(errors="ignore")
            if "+OK" not in resp:
                s.close()
                return print_check("Redis Ledger", False, f"AUTH failed on {host}:{port}", resp.strip())

        # Test PING
        s.sendall(b"*1\r\n$4\r\nPING\r\n")
        resp = s.recv(1024).decode(errors="ignore")
        if "+PONG" not in resp:
            s.close()
            return print_check("Redis Ledger", False, f"PING failed on {host}:{port}", resp.strip())

        # Test SET & GET
        s.sendall(b"*3\r\n$3\r\nSET\r\n$11\r\nverify_cred\r\n$2\r\nOK\r\n")
        s.recv(1024)
        s.sendall(b"*2\r\n$3\r\nGET\r\n$11\r\nverify_cred\r\n")
        resp = s.recv(1024).decode(errors="ignore")
        s.sendall(b"*2\r\n$3\r\nDEL\r\n$11\r\nverify_cred\r\n")
        s.recv(1024)
        s.close()

        if "OK" in resp:
            return print_check("Redis Ledger", True, f"Authenticated and read/write verified on {host}:{port}")
        else:
            return print_check("Redis Ledger", False, f"Read/write check failed on {host}:{port}")
    except Exception as e:
        return print_check("Redis Ledger", False, f"Connection error to {host}:{port}", str(e))

def test_kafka(host, port, client_id="verify-client"):
    try:
        s = socket.create_connection((host, int(port)), timeout=3)
        # Kafka ApiVersions Request v0 (API Key = 18, API Version = 0, Correlation ID = 1)
        cid_bytes = client_id.encode("utf-8")
        req_body = struct.pack(">hhih", 18, 0, 1, len(cid_bytes)) + cid_bytes
        req = struct.pack(">i", len(req_body)) + req_body
        s.sendall(req)

        resp_len_bytes = s.recv(4)
        if len(resp_len_bytes) == 4:
            resp_len = struct.unpack(">i", resp_len_bytes)[0]
            resp_data = s.recv(resp_len)
            corr_id = struct.unpack(">i", resp_data[:4])[0]
            s.close()
            if corr_id == 1:
                return print_check("Kafka Event Broker", True, f"Protocol handshake succeeded on {host}:{port} (client_id: '{client_id}')")
        s.close()
        return print_check("Kafka Event Broker", False, f"Unexpected response from {host}:{port}")
    except Exception as e:
        return print_check("Kafka Event Broker", False, f"Connection error to {host}:{port}", str(e))

def test_otel_http(host, port):
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for scheme in ["https", "http"]:
        url = f"{scheme}://{host}:{port}/v1/traces"
        try:
            req = urllib.request.Request(url, data=b'{"resourceSpans":[]}', headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=3, context=ctx if scheme == "https" else None) as response:
                    return print_check("OpenTelemetry HTTP", True, f"OTLP {scheme.upper()} endpoint reachable on {url} (HTTP {response.status})")
            except urllib.error.HTTPError as e:
                if e.code in [200, 400]:
                    return print_check("OpenTelemetry HTTP", True, f"OTLP {scheme.upper()} endpoint reachable on {url} (HTTP {e.code})")
            except (urllib.error.URLError, ConnectionResetError):
                continue
        except Exception:
            continue
    return print_check("OpenTelemetry HTTP", False, f"Could not establish HTTP/HTTPS connection to {host}:{port}/v1/traces")

def test_otel_grpc(host, port):
    try:
        s = socket.create_connection((host, int(port)), timeout=3)
        s.sendall(b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n")
        resp = s.recv(9)
        s.close()
        return print_check("OpenTelemetry gRPC", True, f"gRPC port reachable on {host}:{port}")
    except Exception as e:
        return print_check("OpenTelemetry gRPC", False, f"Connection error to {host}:{port}", str(e))

def test_service_registry(host, port):
    url = f"http://{host}:{port}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            return print_check("Service Registry", True, f"Health check passed on {url} (HTTP {response.status})")
    except Exception as e:
        return print_check("Service Registry", False, f"Connection error to {url}", str(e))

def main():
    script_dir = Path(__file__).resolve().parent
    env_vars, service_name = find_service_env(script_dir)

    # Detect service-specific prefix defaults from env
    # e.g. for user service: USER_DB_USER, USER_DB_PASSWORD, PORT_USER_DB, etc.
    prefix = service_name.upper().replace("-", "_")

    def get_var(*keys, default=""):
        for k in keys:
            if k in env_vars and env_vars[k]:
                return env_vars[k]
            if k in os.environ and os.environ[k]:
                return os.environ[k]
        return default

    # Database defaults
    default_db_user = get_var(f"{prefix}_DB_USER", "ALLOYDB_USER", "POSTGRES_USER", default="admin")
    default_db_pass = get_var(f"{prefix}_DB_PASSWORD", "ALLOYDB_PASSWORD", "POSTGRES_PASSWORD", default="llmobs_s3cret_2026")
    default_db_name = get_var(f"{prefix}_DB_NAME", f"{prefix}_DB", "ALLOYDB_DB", "POSTGRES_DB", default="llm_observability")
    default_db_port = get_var(f"PORT_{prefix}_DB", "PORT_ALLOYDB", default="5432")
    default_db_container = f"{service_name}-service-db"

    # Redis defaults
    default_redis_pass = get_var(f"{prefix}_REDIS_PASSWORD", "REDIS_PASSWORD", default="llmobs_redis_s3cret_2026")
    default_redis_port = get_var(f"PORT_{prefix}_REDIS", "PORT_REDIS", default="6379")

    # Kafka defaults
    default_kafka_port = get_var(f"PORT_{prefix}_KAFKA", "PORT_KAFKA", default="9092")

    # OTel defaults
    default_otel_http = get_var(f"PORT_{prefix}_OTEL_HTTP", "PORT_OTEL_HTTP", default="4318")
    default_otel_grpc = get_var(f"PORT_{prefix}_OTEL_GRPC", "PORT_OTEL_GRPC", default="4317")

    # Registry defaults
    default_registry_port = get_var(f"PORT_{prefix}_SERVICE_REGISTRY", "PORT_SERVICE_REGISTRY", default="31426")

    parser = argparse.ArgumentParser(
        description=f"Verify credentials and endpoints for {service_name.upper()} service stack.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Component filter
    parser.add_argument("--only", choices=["all", "db", "redis", "kafka", "otel", "registry"], default="all",
                        help="Filter verification to specific component")

    # DB arguments
    parser.add_argument("--db-host", default=os.getenv("AUTH_DB_HOST", "localhost"), help="Postgres / AlloyDB host")
    parser.add_argument("--db-port", default=default_db_port, help="Postgres / AlloyDB port")
    parser.add_argument("--db-user", default=default_db_user, help="Database username")
    parser.add_argument("--db-pass", "--db-password", dest="db_pass", default=default_db_pass, help="Database password")
    parser.add_argument("--db-name", default=default_db_name, help="Database name")
    parser.add_argument("--container-db", default=default_db_container, help="Docker DB container name for fallback exec")

    # Redis arguments
    parser.add_argument("--redis-host", default=os.getenv("AUTH_REDIS_HOST", "localhost"), help="Redis host")
    parser.add_argument("--redis-port", default=default_redis_port, help="Redis port")
    parser.add_argument("--redis-pass", "--redis-password", dest="redis_pass", default=default_redis_pass, help="Redis password")

    # Kafka arguments
    parser.add_argument("--kafka-host", default="localhost", help="Kafka host")
    parser.add_argument("--kafka-port", default=default_kafka_port, help="Kafka port")
    parser.add_argument("--kafka-client-id", default=f"{service_name}-verifier", help="Kafka client id")

    # OTel arguments
    parser.add_argument("--otel-host", default="localhost", help="OTel Collector host")
    parser.add_argument("--otel-http-port", default=default_otel_http, help="OTel Collector HTTP port")
    parser.add_argument("--otel-grpc-port", default=default_otel_grpc, help="OTel Collector gRPC port")

    # Registry arguments
    parser.add_argument("--registry-host", default="localhost", help="Service registry host")
    parser.add_argument("--registry-port", default=default_registry_port, help="Service registry port")

    args = parser.parse_args()

    print(f"\n{BLUE}===================================================={RESET}")
    print(f"{BOLD} CREDENTIAL VERIFICATION: {service_name.upper()} SERVICE{RESET}")
    print(f"{BLUE}===================================================={RESET}\n")

    results = []
    only = args.only

    if only in ["all", "db"]:
        print(f"{BOLD}1. Database (PostgreSQL / AlloyDB):{RESET}")
        print(f"   Target: {args.db_user}@{args.db_host}:{args.db_port}/{args.db_name}")
        results.append(test_postgres(args.db_host, args.db_port, args.db_user, args.db_pass, args.db_name, args.container_db))
        print()

    if only in ["all", "redis"]:
        print(f"{BOLD}2. Redis Ledger:{RESET}")
        print(f"   Target: {args.redis_host}:{args.redis_port} (auth: {'***' if args.redis_pass else 'none'})")
        results.append(test_redis(args.redis_host, args.redis_port, args.redis_pass))
        print()

    if only in ["all", "kafka"]:
        print(f"{BOLD}3. Apache Kafka Event Broker:{RESET}")
        print(f"   Target: {args.kafka_host}:{args.kafka_port}")
        results.append(test_kafka(args.kafka_host, args.kafka_port, args.kafka_client_id))
        print()

    if only in ["all", "otel"]:
        print(f"{BOLD}4. OpenTelemetry Collector:{RESET}")
        print(f"   HTTP Target: http://{args.otel_host}:{args.otel_http_port}/v1/traces")
        print(f"   gRPC Target: {args.otel_host}:{args.otel_grpc_port}")
        results.append(test_otel_http(args.otel_host, args.otel_http_port))
        results.append(test_otel_grpc(args.otel_host, args.otel_grpc_port))
        print()

    if only in ["all", "registry"]:
        print(f"{BOLD}5. Service Registry:{RESET}")
        print(f"   Target: http://{args.registry_host}:{args.registry_port}/health")
        results.append(test_service_registry(args.registry_host, args.registry_port))
        print()

    print(f"{BLUE}===================================================={RESET}")
    if all(results):
        print(f"{GREEN}{BOLD}✓ ALL {len(results)} VERIFICATION CHECKS PASSED!{RESET}")
        print(f"{BLUE}===================================================={RESET}\n")
        sys.exit(0)
    else:
        failed = results.count(False)
        print(f"{RED}{BOLD}✗ {failed} OF {len(results)} CHECKS FAILED!{RESET}")
        print(f"{BLUE}===================================================={RESET}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
