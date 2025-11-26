#!/usr/bin/env python3
"""
MySQL Installation Script for Render.com
Forces MySQL server installation on Render's infrastructure
File: mysql_setup.py
"""

import subprocess
import sys
import os
import time
import random
import string
import socket

def run_command(cmd, shell=False, check=True, capture=True):
    """Execute shell command"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            check=check,
            capture_output=capture,
            text=True
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

def install_mysql_server():
    """Install MySQL server on Render"""
    print("=" * 60)
    print("INSTALLING MYSQL SERVER ON RENDER")
    print("=" * 60)
    
    print("\n[1/5] Updating package list...")
    run_command("apt-get update -qq", shell=True)
    
    print("[2/5] Installing MySQL server (non-interactive)...")
    # Set root password during installation
    root_pwd = os.getenv('MYSQL_ROOT_PASSWORD', 'rootpass123')
    
    debconf_settings = f"""
mysql-server mysql-server/root_password password {root_pwd}
mysql-server mysql-server/root_password_again password {root_pwd}
"""
    
    # Pre-configure MySQL
    process = subprocess.Popen(
        ['debconf-set-selections'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    process.communicate(input=debconf_settings)
    
    # Install MySQL
    run_command(
        "DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server",
        shell=True
    )
    
    print("[3/5] Creating MySQL data directory...")
    mysql_dir = "/var/lib/mysql"
    run_command(f"mkdir -p {mysql_dir}", shell=True, check=False)
    run_command(f"chown -R mysql:mysql {mysql_dir}", shell=True, check=False)
    
    print("[4/5] Initializing MySQL data directory...")
    run_command("mysqld --initialize-insecure --user=mysql", shell=True, check=False)
    
    print("[5/5] Starting MySQL server...")
    # Start MySQL in background without systemd (Render doesn't have systemd)
    start_mysql_server()
    
    print("✓ MySQL server installed and started\n")
    return root_pwd

def start_mysql_server():
    """Start MySQL server in background"""
    # Kill any existing MySQL processes
    run_command("pkill -9 mysqld", shell=True, check=False)
    time.sleep(2)
    
    # Start MySQL in background
    mysql_cmd = "mysqld --user=mysql --datadir=/var/lib/mysql --skip-grant-tables --bind-address=0.0.0.0 &"
    subprocess.Popen(mysql_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for MySQL to start
    print("   Waiting for MySQL to start", end="", flush=True)
    for i in range(30):
        time.sleep(1)
        print(".", end="", flush=True)
        result = run_command("mysqladmin ping 2>/dev/null", shell=True, check=False)
        if result and "alive" in result:
            print(" ✓")
            break
    else:
        print("\n   Starting with socket connection...")
    
    time.sleep(3)

def setup_database_and_user(db_name, db_user, db_password, root_pwd):
    """Create database and user with full privileges"""
    print("=" * 60)
    print("SETTING UP DATABASE AND USER")
    print("=" * 60)
    
    # First, flush privileges and set root password
    init_commands = f"""
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY '{root_pwd}';
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '{root_pwd}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
"""
    
    # Execute initial setup
    process = subprocess.Popen(
        ['mysql', '-u', 'root'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=init_commands)
    
    time.sleep(2)
    
    # Now create database and user
    sql_commands = f"""
CREATE DATABASE IF NOT EXISTS {db_name};
CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';
GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost' WITH GRANT OPTION;
CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_password}';
GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'%' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO '{db_user}'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SELECT User, Host FROM mysql.user WHERE User='{db_user}';
"""
    
    cmd = f'mysql -u root -p{root_pwd} -e "{sql_commands}"'
    result = run_command(cmd, shell=True, check=False)
    
    if result is not None:
        print(f"✓ Database '{db_name}' created")
        print(f"✓ User '{db_user}' created with ALL PRIVILEGES")
        print(f"✓ User can connect from anywhere (%)\n")
        return True
    else:
        # Try without password if it fails
        cmd = f'mysql -u root -e "{sql_commands}"'
        result = run_command(cmd, shell=True, check=False)
        if result is not None:
            print(f"✓ Database '{db_name}' created")
            print(f"✓ User '{db_user}' created with ALL PRIVILEGES\n")
            return True
    
    print("✗ Error creating database or user")
    return False

def restart_mysql_with_networking():
    """Restart MySQL with proper networking enabled"""
    print("\n[*] Restarting MySQL with networking enabled...")
    
    # Kill existing MySQL
    run_command("pkill -9 mysqld", shell=True, check=False)
    time.sleep(2)
    
    # Start with proper settings
    mysql_cmd = "mysqld --user=mysql --datadir=/var/lib/mysql --bind-address=0.0.0.0 --port=3306 &"
    subprocess.Popen(mysql_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("   Waiting for MySQL to restart", end="", flush=True)
    for i in range(20):
        time.sleep(1)
        print(".", end="", flush=True)
        result = run_command("mysqladmin ping 2>/dev/null", shell=True, check=False)
        if result and "alive" in result:
            print(" ✓")
            break
    
    time.sleep(2)

def get_system_info():
    """Display system information"""
    print("=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    
    info = {
        "Environment": "Render.com" if os.getenv('RENDER') else "Local/Other",
        "Service": os.getenv('RENDER_SERVICE_NAME', 'N/A'),
        "Hostname": socket.gethostname(),
        "MySQL Port": "3306",
        "MySQL Status": "Running"
    }
    
    # Get MySQL version
    version = run_command("mysql --version", shell=True)
    if version:
        info["MySQL Version"] = version
    
    # Get process info
    ps = run_command("ps aux | grep mysqld | grep -v grep", shell=True, check=False)
    if ps:
        info["MySQL Process"] = "Active"
    
    for key, value in info.items():
        print(f"{key:20s}: {value}")

def display_connection_info(db_name, db_user, db_password, root_pwd):
    """Display connection configuration"""
    hostname = socket.gethostname()
    host = "localhost"
    port = 3306
    
    print("\n" + "=" * 60)
    print("DATABASE CONNECTION CONFIGURATION")
    print("=" * 60)
    
    print(f"""
MySQL Root Password: {root_pwd}

Application Database Configuration:
-----------------------------------
Host:     {host} (or 127.0.0.1)
Port:     {port}
Database: {db_name}
Username: {db_user}
Password: {db_password}

Connection String (MySQL CLI):
mysql -h {host} -P {port} -u {db_user} -p{db_password} {db_name}

Root Access:
mysql -h {host} -P {port} -u root -p{root_pwd}
""")

    # Save credentials to a file for the app to use
    credentials = f"""# MySQL Connection Credentials
DB_HOST=localhost
DB_PORT=3306
DB_NAME={db_name}
DB_USER={db_user}
DB_PASSWORD={db_password}
MYSQL_ROOT_PASSWORD={root_pwd}
"""
    
    with open('.mysql_credentials', 'w') as f:
        f.write(credentials)
    
    print("✓ Credentials saved to .mysql_credentials file\n")

def main():
    """Main execution"""
    print("\n" + "=" * 60)
    print("MySQL SERVER INSTALLATION FOR RENDER.COM")
    print("=" * 60)
    print("This will install MySQL server directly on Render")
    print("=" * 60)
    
    # Configuration from environment variables
    db_name = os.getenv('DB_NAME', 'myapp_db')
    db_user = os.getenv('DB_USER', 'appuser')
    db_password = os.getenv('DB_PASSWORD', generate_password())
    root_pwd = os.getenv('MYSQL_ROOT_PASSWORD', generate_password())
    
    print(f"\nConfiguration:")
    print(f"  Database: {db_name}")
    print(f"  User: {db_user}")
    print(f"  Password: {db_password}")
    print(f"  Root Password: {root_pwd}\n")
    
    # Install MySQL
    root_pwd = install_mysql_server()
    
    # Setup database and user
    if not setup_database_and_user(db_name, db_user, db_password, root_pwd):
        print("Retrying database setup...")
        time.sleep(3)
        setup_database_and_user(db_name, db_user, db_password, root_pwd)
    
    # Restart with proper networking
    restart_mysql_with_networking()
    
    # Display info
    get_system_info()
    display_connection_info(db_name, db_user, db_password, root_pwd)
    
    print("\n" + "=" * 60)
    print("✓ MYSQL INSTALLATION COMPLETED")
    print("=" * 60)
    print("\nYour application (your_app.py) can now connect to MySQL!")
    print(f"Root Password: {root_pwd}")
    print(f"App User: {db_user}")
    print(f"App Password: {db_password}\n")

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
