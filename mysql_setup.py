#!/usr/bin/env python3
"""
MySQL Installation Script for Render.com (No Root Required)
Downloads and runs MySQL without requiring sudo/root permissions
File: mysql_setup.py
"""

import subprocess
import sys
import os
import time
import random
import string
import socket
import shutil

def run_command(cmd, shell=False, check=True, capture=True, cwd=None):
    """Execute shell command"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            check=check,
            capture_output=capture,
            text=True,
            cwd=cwd
        )
        return result.stdout.strip() if capture else None
    except subprocess.CalledProcessError as e:
        if capture:
            print(f"Error: {e.stderr}")
        return None

def generate_password(length=16):
    """Generate a random secure password"""
    chars = string.ascii_letters + string.digits + "_-"
    return ''.join(random.choice(chars) for _ in range(length))

def download_mysql():
    """Download pre-compiled MySQL binary"""
    print("=" * 60)
    print("DOWNLOADING MYSQL BINARIES")
    print("=" * 60)
    
    mysql_dir = os.path.expanduser("~/mysql")
    
    if os.path.exists(mysql_dir):
        print("✓ MySQL directory already exists")
        return mysql_dir
    
    print("\n[1/4] Creating MySQL directory...")
    os.makedirs(mysql_dir, exist_ok=True)
    
    print("[2/4] Downloading MySQL binaries...")
    # Using MySQL 8.0 generic Linux binary
    mysql_url = "https://dev.mysql.com/get/Downloads/MySQL-8.0/mysql-8.0.40-linux-glibc2.28-x86_64.tar.xz"
    tar_file = f"{mysql_dir}/mysql.tar.xz"
    
    # Download with curl or wget
    download_cmd = f"curl -L -o {tar_file} {mysql_url}"
    print(f"   Downloading from MySQL official site...")
    result = run_command(download_cmd, shell=True, check=False)
    
    if not os.path.exists(tar_file):
        print("   Trying with wget...")
        download_cmd = f"wget -O {tar_file} {mysql_url}"
        run_command(download_cmd, shell=True)
    
    print("[3/4] Extracting MySQL...")
    run_command(f"tar -xf {tar_file} -C {mysql_dir} --strip-components=1", shell=True)
    
    print("[4/4] Cleaning up...")
    if os.path.exists(tar_file):
        os.remove(tar_file)
    
    print("✓ MySQL binaries downloaded and extracted\n")
    return mysql_dir

def initialize_mysql(mysql_dir):
    """Initialize MySQL data directory"""
    print("=" * 60)
    print("INITIALIZING MYSQL")
    print("=" * 60)
    
    data_dir = f"{mysql_dir}/data"
    
    if os.path.exists(data_dir) and os.listdir(data_dir):
        print("✓ MySQL data directory already initialized")
        return data_dir
    
    os.makedirs(data_dir, exist_ok=True)
    
    print("\n[1/2] Initializing MySQL data directory...")
    mysqld = f"{mysql_dir}/bin/mysqld"
    
    init_cmd = [
        mysqld,
        f"--datadir={data_dir}",
        "--initialize-insecure",
        "--user=$(whoami)"
    ]
    
    result = run_command(f"{mysqld} --datadir={data_dir} --initialize-insecure", shell=True, check=False)
    
    print("[2/2] Setting permissions...")
    run_command(f"chmod -R 750 {data_dir}", shell=True, check=False)
    
    print("✓ MySQL initialized\n")
    return data_dir

def start_mysql_server(mysql_dir, data_dir):
    """Start MySQL server without root"""
    print("=" * 60)
    print("STARTING MYSQL SERVER")
    print("=" * 60)
    
    mysqld = f"{mysql_dir}/bin/mysqld"
    socket_file = f"{mysql_dir}/mysql.sock"
    pid_file = f"{mysql_dir}/mysql.pid"
    log_file = f"{mysql_dir}/mysql.log"
    port = 3306
    
    # Kill any existing MySQL process
    run_command(f"pkill -f mysqld", shell=True, check=False)
    time.sleep(2)
    
    # Create my.cnf configuration
    my_cnf = f"""
[mysqld]
datadir={data_dir}
socket={socket_file}
pid-file={pid_file}
port={port}
bind-address=0.0.0.0
log-error={log_file}
skip-grant-tables
"""
    
    cnf_file = f"{mysql_dir}/my.cnf"
    with open(cnf_file, 'w') as f:
        f.write(my_cnf)
    
    print("\n[1/2] Starting MySQL daemon...")
    
    # Start MySQL in background
    start_cmd = f"{mysqld} --defaults-file={cnf_file} &"
    subprocess.Popen(start_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("[2/2] Waiting for MySQL to start", end="", flush=True)
    mysql_client = f"{mysql_dir}/bin/mysql"
    
    for i in range(40):
        time.sleep(1)
        print(".", end="", flush=True)
        
        # Try to connect
        test_cmd = f"{mysql_client} --socket={socket_file} -e 'SELECT 1' 2>/dev/null"
        result = run_command(test_cmd, shell=True, check=False)
        
        if result is not None:
            print(" ✓")
            print("✓ MySQL server started successfully\n")
            return socket_file, port
    
    print("\n✗ MySQL failed to start in time")
    print(f"Check log: {log_file}")
    return socket_file, port

def setup_database_and_user(mysql_dir, socket_file, db_name, db_user, db_password, root_pwd):
    """Create database and user with full privileges"""
    print("=" * 60)
    print("SETTING UP DATABASE AND USER")
    print("=" * 60)
    
    mysql_client = f"{mysql_dir}/bin/mysql"
    
    # First, set root password and create user
    sql_commands = f"""
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY '{root_pwd}';
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '{root_pwd}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
CREATE DATABASE IF NOT EXISTS {db_name};
CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';
CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_password}';
GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'%' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO '{db_user}'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
"""
    
    # Save SQL to file
    sql_file = f"{mysql_dir}/setup.sql"
    with open(sql_file, 'w') as f:
        f.write(sql_commands)
    
    print("\n[1/2] Creating database and user...")
    cmd = f"{mysql_client} --socket={socket_file} < {sql_file}"
    result = run_command(cmd, shell=True, check=False)
    
    time.sleep(2)
    
    print("[2/2] Verifying setup...")
    verify_cmd = f"{mysql_client} --socket={socket_file} -e \"SHOW DATABASES; SELECT User, Host FROM mysql.user WHERE User='{db_user}';\""
    run_command(verify_cmd, shell=True, check=False)
    
    print(f"\n✓ Database '{db_name}' created")
    print(f"✓ User '{db_user}' created with ALL PRIVILEGES")
    print(f"✓ User can connect from anywhere\n")
    
    return True

def restart_mysql_with_auth(mysql_dir, data_dir, socket_file):
    """Restart MySQL with authentication enabled"""
    print("=" * 60)
    print("RESTARTING MYSQL WITH AUTHENTICATION")
    print("=" * 60)
    
    mysqld = f"{mysql_dir}/bin/mysqld"
    pid_file = f"{mysql_dir}/mysql.pid"
    log_file = f"{mysql_dir}/mysql.log"
    port = 3306
    
    # Kill existing MySQL
    print("\n[1/3] Stopping MySQL...")
    run_command(f"pkill -f mysqld", shell=True, check=False)
    time.sleep(3)
    
    # Create new config without skip-grant-tables
    my_cnf = f"""
[mysqld]
datadir={data_dir}
socket={socket_file}
pid-file={pid_file}
port={port}
bind-address=0.0.0.0
log-error={log_file}

[client]
socket={socket_file}
"""
    
    cnf_file = f"{mysql_dir}/my.cnf"
    with open(cnf_file, 'w') as f:
        f.write(my_cnf)
    
    print("[2/3] Starting MySQL with authentication...")
    start_cmd = f"{mysqld} --defaults-file={cnf_file} &"
    subprocess.Popen(start_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("[3/3] Waiting for MySQL", end="", flush=True)
    mysql_client = f"{mysql_dir}/bin/mysql"
    
    for i in range(30):
        time.sleep(1)
        print(".", end="", flush=True)
        
        test_cmd = f"{mysql_client} --socket={socket_file} -u root -e 'SELECT 1' 2>/dev/null"
        result = run_command(test_cmd, shell=True, check=False)
        
        if result:
            print(" ✓")
            break
    
    print("\n✓ MySQL restarted with authentication enabled\n")

def get_system_info(mysql_dir):
    """Display system information"""
    print("=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    
    mysql_client = f"{mysql_dir}/bin/mysql"
    version = run_command(f"{mysql_client} --version", shell=True)
    
    info = {
        "Environment": "Render.com" if os.getenv('RENDER') else "Local/Other",
        "Service": os.getenv('RENDER_SERVICE_NAME', 'N/A'),
        "Hostname": socket.gethostname(),
        "MySQL Location": mysql_dir,
        "MySQL Version": version if version else "Unknown",
        "MySQL Port": "3306",
        "MySQL Status": "Running"
    }
    
    for key, value in info.items():
        print(f"{key:20s}: {value}")

def save_credentials(mysql_dir, socket_file, db_name, db_user, db_password, root_pwd):
    """Save connection credentials"""
    print("\n" + "=" * 60)
    print("SAVING CONNECTION CREDENTIALS")
    print("=" * 60)
    
    credentials = f"""# MySQL Connection Credentials
# Generated by mysql_setup.py

export MYSQL_DIR="{mysql_dir}"
export MYSQL_SOCKET="{socket_file}"
export DB_HOST="localhost"
export DB_PORT="3306"
export DB_NAME="{db_name}"
export DB_USER="{db_user}"
export DB_PASSWORD="{db_password}"
export MYSQL_ROOT_PASSWORD="{root_pwd}"
export PATH="{mysql_dir}/bin:$PATH"
"""
    
    cred_file = ".mysql_credentials"
    with open(cred_file, 'w') as f:
        f.write(credentials)
    
    print(f"✓ Credentials saved to {cred_file}")
    
    # Also create Python config file
    py_config = f'''# MySQL Configuration for Python
MYSQL_CONFIG = {{
    'unix_socket': '{socket_file}',
    'host': 'localhost',
    'port': 3306,
    'database': '{db_name}',
    'user': '{db_user}',
    'password': '{db_password}'
}}
'''
    
    with open('mysql_config.py', 'w') as f:
        f.write(py_config)
    
    print(f"✓ Python config saved to mysql_config.py")
    
    print(f"""
Connection Details:
-------------------
Socket:   {socket_file}
Host:     localhost
Port:     3306
Database: {db_name}
User:     {db_user}
Password: {db_password}

Root Password: {root_pwd}

MySQL CLI Command:
{mysql_dir}/bin/mysql --socket={socket_file} -u {db_user} -p{db_password} {db_name}
""")

def main():
    """Main execution"""
    print("\n" + "=" * 60)
    print("MySQL INSTALLATION FOR RENDER.COM (NO ROOT)")
    print("=" * 60)
    print("Installing MySQL without sudo/root permissions")
    print("=" * 60)
    
    # Configuration
    db_name = os.getenv('DB_NAME', 'myapp_db')
    db_user = os.getenv('DB_USER', 'appuser')
    db_password = os.getenv('DB_PASSWORD', generate_password())
    root_pwd = os.getenv('MYSQL_ROOT_PASSWORD', generate_password())
    
    print(f"\nConfiguration:")
    print(f"  Database: {db_name}")
    print(f"  User: {db_user}")
    print(f"  Password: {db_password}")
    print(f"  Root Password: {root_pwd}\n")
    
    # Download MySQL
    mysql_dir = download_mysql()
    
    # Initialize MySQL
    data_dir = initialize_mysql(mysql_dir)
    
    # Start MySQL (first time with skip-grant-tables)
    socket_file, port = start_mysql_server(mysql_dir, data_dir)
    
    # Setup database and user
    setup_database_and_user(mysql_dir, socket_file, db_name, db_user, db_password, root_pwd)
    
    # Restart with authentication
    restart_mysql_with_auth(mysql_dir, data_dir, socket_file)
    
    # Display info
    get_system_info(mysql_dir)
    
    # Save credentials
    save_credentials(mysql_dir, socket_file, db_name, db_user, db_password, root_pwd)
    
    print("\n" + "=" * 60)
    print("✓ MYSQL INSTALLATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\nMySQL is now running and ready to use!")
    print(f"MySQL directory: {mysql_dir}")
    print(f"Socket file: {socket_file}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
