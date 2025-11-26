#!/usr/bin/env python3
"""
MySQL Non-Root Installation Script
Works on systems without root access (e.g., Koyeb, Render)
"""

import os
import subprocess
import time
import urllib.request
import tarfile
import sys
import platform
import psutil
import socket
from pathlib import Path

# Configuration
MYSQL_VERSION = "8.0.35"
HOME = Path.home()
INSTALL_DIR = HOME / "mysql"
DATA_DIR = HOME / "mysql_data"
TMP_DIR = HOME / "mysql_tmp"
MYSQL_PORT = 3306

# Database configuration
DB_NAME = "myapp_db"
DB_USER = "appuser"
DB_PASSWORD = "SecurePass123!"  # CHANGE THIS!

def print_section(message):
    """Print a formatted section header"""
    print(f"\n{'='*50}")
    print(f"  {message}")
    print(f"{'='*50}\n")

def get_system_info():
    """Gather and display system information"""
    info = {}
    
    # Basic system info
    info['os'] = platform.system()
    info['os_release'] = platform.release()
    info['os_version'] = platform.version()
    info['machine'] = platform.machine()
    info['processor'] = platform.processor()
    info['hostname'] = socket.gethostname()
    info['python_version'] = platform.python_version()
    
    # CPU info
    info['cpu_count_physical'] = psutil.cpu_count(logical=False)
    info['cpu_count_logical'] = psutil.cpu_count(logical=True)
    info['cpu_freq'] = psutil.cpu_freq()
    
    # Memory info
    mem = psutil.virtual_memory()
    info['memory_total'] = mem.total
    info['memory_available'] = mem.available
    info['memory_percent'] = mem.percent
    
    # Disk info
    disk = psutil.disk_usage('/')
    info['disk_total'] = disk.total
    info['disk_used'] = disk.used
    info['disk_free'] = disk.free
    info['disk_percent'] = disk.percent
    
    # User info
    info['username'] = os.getenv('USER', 'unknown')
    info['home_dir'] = str(Path.home())
    
    return info

def print_system_info(info):
    """Display system information in a formatted way"""
    print_section("System Information")
    
    print("📊 Operating System:")
    print(f"   OS:            {info['os']} {info['os_release']}")
    print(f"   Version:       {info['os_version']}")
    print(f"   Architecture:  {info['machine']}")
    print(f"   Processor:     {info['processor'] or 'N/A'}")
    print(f"   Hostname:      {info['hostname']}")
    print(f"   Python:        {info['python_version']}")
    
    print("\n💻 CPU:")
    print(f"   Physical Cores: {info['cpu_count_physical']}")
    print(f"   Logical Cores:  {info['cpu_count_logical']}")
    if info['cpu_freq']:
        print(f"   Frequency:      {info['cpu_freq'].current:.2f} MHz")
        print(f"   Max Frequency:  {info['cpu_freq'].max:.2f} MHz")
    
    print("\n🧠 Memory:")
    print(f"   Total:      {info['memory_total'] / (1024**3):.2f} GB")
    print(f"   Available:  {info['memory_available'] / (1024**3):.2f} GB")
    print(f"   Used:       {info['memory_percent']:.1f}%")
    
    print("\n💾 Disk (Root):")
    print(f"   Total:      {info['disk_total'] / (1024**3):.2f} GB")
    print(f"   Used:       {info['disk_used'] / (1024**3):.2f} GB ({info['disk_percent']:.1f}%)")
    print(f"   Free:       {info['disk_free'] / (1024**3):.2f} GB")
    
    print("\n👤 User:")
    print(f"   Username:   {info['username']}")
    print(f"   Home Dir:   {info['home_dir']}")
    print()
    
    # Check if system meets minimum requirements
    print("⚙️  MySQL Requirements Check:")
    
    min_memory_gb = 1
    min_disk_gb = 2
    
    memory_ok = info['memory_available'] / (1024**3) >= min_memory_gb
    disk_ok = info['disk_free'] / (1024**3) >= min_disk_gb
    
    print(f"   Memory (>= {min_memory_gb}GB):  {'✅' if memory_ok else '❌'}")
    print(f"   Disk (>= {min_disk_gb}GB):    {'✅' if disk_ok else '❌'}")
    
    if not memory_ok or not disk_ok:
        print("\n⚠️  WARNING: System may not meet minimum requirements for MySQL!")
        if not memory_ok:
            print(f"   - Need at least {min_memory_gb}GB available memory")
        if not disk_ok:
            print(f"   - Need at least {min_disk_gb}GB free disk space")
    else:
        print("\n✅ System meets minimum requirements for MySQL")
    print()

def run_command(cmd, shell=False, check=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            check=check,
            capture_output=True,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"stderr: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def download_mysql():
    """Download MySQL binary if not already present"""
    mysql_filename = f"mysql-{MYSQL_VERSION}-linux-glibc2.28-x86_64.tar.xz"
    mysql_url = f"https://dev.mysql.com/get/Downloads/MySQL-8.0/{mysql_filename}"
    mysql_path = INSTALL_DIR / mysql_filename
    
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    
    if mysql_path.exists():
        print(f"MySQL archive already exists: {mysql_path}")
        return mysql_path
    
    print(f"Downloading MySQL {MYSQL_VERSION}...")
    print(f"URL: {mysql_url}")
    print("This may take a few minutes...")
    
    try:
        urllib.request.urlretrieve(mysql_url, mysql_path)
        print(f"Downloaded successfully to {mysql_path}")
        return mysql_path
    except Exception as e:
        print(f"Error downloading MySQL: {e}")
        sys.exit(1)

def extract_mysql(archive_path):
    """Extract MySQL archive"""
    extract_dir = INSTALL_DIR / f"mysql-{MYSQL_VERSION}-linux-glibc2.28-x86_64"
    
    if extract_dir.exists():
        print(f"MySQL already extracted: {extract_dir}")
        return extract_dir
    
    print("Extracting MySQL archive...")
    with tarfile.open(archive_path, 'r:xz') as tar:
        tar.extractall(path=INSTALL_DIR)
    
    print(f"Extracted to {extract_dir}")
    return extract_dir

def initialize_database(mysql_home):
    """Initialize MySQL data directory"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    
    mysql_data_check = DATA_DIR / "mysql"
    if mysql_data_check.exists():
        print("MySQL data directory already initialized")
        return
    
    print("Initializing MySQL data directory...")
    mysqld = mysql_home / "bin" / "mysqld"
    
    cmd = [
        str(mysqld),
        "--initialize-insecure",
        f"--basedir={mysql_home}",
        f"--datadir={DATA_DIR}",
        f"--user={os.getenv('USER', 'user')}"
    ]
    
    run_command(cmd)
    print("MySQL data directory initialized")

def create_config_file(mysql_home):
    """Create MySQL configuration file"""
    config_path = HOME / "my.cnf"
    
    config_content = f"""[mysqld]
basedir={mysql_home}
datadir={DATA_DIR}
socket={TMP_DIR}/mysql.sock
pid-file={TMP_DIR}/mysql.pid
port={MYSQL_PORT}
bind-address=0.0.0.0
tmpdir={TMP_DIR}

# Performance settings
max_connections=50
key_buffer_size=16M
max_allowed_packet=16M
thread_stack=192K
thread_cache_size=8

# Logging
log_error={TMP_DIR}/mysql_error.log

# Skip some checks for compatibility
skip-name-resolve
skip-host-cache

[client]
socket={TMP_DIR}/mysql.sock
port={MYSQL_PORT}

[mysql]
socket={TMP_DIR}/mysql.sock
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"Configuration file created: {config_path}")
    return config_path

def start_mysql(mysql_home, config_path):
    """Start MySQL server"""
    print("Starting MySQL server...")
    
    mysqld = mysql_home / "bin" / "mysqld"
    cmd = [str(mysqld), f"--defaults-file={config_path}"]
    
    # Start MySQL in background
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print(f"MySQL server started with PID: {process.pid}")
    
    # Wait for MySQL to be ready
    print("Waiting for MySQL to start...")
    socket_path = TMP_DIR / "mysql.sock"
    
    for i in range(30):
        if socket_path.exists():
            print("MySQL is ready!")
            time.sleep(2)  # Give it a bit more time
            return process
        time.sleep(1)
    
    print("ERROR: MySQL failed to start within 30 seconds")
    print(f"Check error log: {TMP_DIR}/mysql_error.log")
    sys.exit(1)

def setup_database(mysql_home):
    """Create database and user"""
    print("Creating database and user...")
    
    mysql_client = mysql_home / "bin" / "mysql"
    socket_path = TMP_DIR / "mysql.sock"
    
    sql_commands = f"""
CREATE DATABASE IF NOT EXISTS {DB_NAME};
CREATE USER IF NOT EXISTS '{DB_USER}'@'%' IDENTIFIED BY '{DB_PASSWORD}';
GRANT ALL PRIVILEGES ON {DB_NAME}.* TO '{DB_USER}'@'%';
FLUSH PRIVILEGES;
SELECT User, Host FROM mysql.user WHERE User='{DB_USER}';
SHOW DATABASES;
"""
    
    cmd = [
        str(mysql_client),
        f"--socket={socket_path}",
        "-u", "root",
        "-e", sql_commands
    ]
    
    result = run_command(cmd)
    print(result.stdout)
    print("Database and user created successfully!")

def create_helper_scripts(mysql_home):
    """Create convenience scripts for managing MySQL"""
    
    # Start script
    start_script = HOME / "mysql-start.sh"
    with open(start_script, 'w') as f:
        f.write(f"""#!/bin/bash
MYSQL_HOME="{mysql_home}"
"$MYSQL_HOME/bin/mysqld" --defaults-file="$HOME/my.cnf" &
echo "MySQL started. PID: $!"
""")
    start_script.chmod(0o755)
    
    # Stop script
    stop_script = HOME / "mysql-stop.sh"
    with open(stop_script, 'w') as f:
        f.write(f"""#!/bin/bash
MYSQL_HOME="{mysql_home}"
"$MYSQL_HOME/bin/mysqladmin" --socket="{TMP_DIR}/mysql.sock" -u root shutdown
echo "MySQL stopped."
""")
    stop_script.chmod(0o755)
    
    # Connect script
    connect_script = HOME / "mysql-connect.sh"
    with open(connect_script, 'w') as f:
        f.write(f"""#!/bin/bash
MYSQL_HOME="{mysql_home}"
"$MYSQL_HOME/bin/mysql" --socket="{TMP_DIR}/mysql.sock" -u root
""")
    connect_script.chmod(0o755)
    
    print("Helper scripts created:")
    print(f"  Start:   {start_script}")
    print(f"  Stop:    {stop_script}")
    print(f"  Connect: {connect_script}")

def print_summary(mysql_process):
    """Print installation summary"""
    print_section("Installation Complete!")
    print("MySQL is now running!")
    print(f"\nMySQL Process PID: {mysql_process.pid}")
    print("\nConnection Details:")
    print(f"  Host:     localhost")
    print(f"  Port:     {MYSQL_PORT}")
    print(f"  Socket:   {TMP_DIR}/mysql.sock")
    print(f"  Database: {DB_NAME}")
    print(f"  User:     {DB_USER}")
    print(f"  Password: {DB_PASSWORD}")
    print("\nConnection String:")
    print(f"  mysql://{DB_USER}:{DB_PASSWORD}@localhost:{MYSQL_PORT}/{DB_NAME}")
    print("\nManagement Scripts:")
    print(f"  Start MySQL: {HOME}/mysql-start.sh")
    print(f"  Stop MySQL:  {HOME}/mysql-stop.sh")
    print(f"  Connect:     {HOME}/mysql-connect.sh")
    print("\n⚠️  WARNING: Change the DB_PASSWORD before using in production!")
    print()

def main():
    """Main installation process"""
    print_section("MySQL Non-Root Installation")
    
    # Display system information first
    try:
        system_info = get_system_info()
        print_system_info(system_info)
    except Exception as e:
        print(f"⚠️  Could not gather complete system info: {e}")
        print("   (This won't affect the installation)\n")
    
    print(f"Installation directory: {INSTALL_DIR}")
    print(f"Data directory: {DATA_DIR}")
    
    try:
        # Download and extract MySQL
        archive_path = download_mysql()
        mysql_home = extract_mysql(archive_path)
        
        # Initialize and configure
        initialize_database(mysql_home)
        config_path = create_config_file(mysql_home)
        
        # Start MySQL
        mysql_process = start_mysql(mysql_home, config_path)
        
        # Setup database and user
        setup_database(mysql_home)
        
        # Create helper scripts
        create_helper_scripts(mysql_home)
        
        # Print summary
        print_summary(mysql_process)
        
        print("✅ Installation completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\nInstallation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
