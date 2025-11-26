#!/usr/bin/env python3
"""
MySQL Non-Root Installation Script - Fixed for Render/Koyeb
Addresses socket connection issues and improves error handling
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
import shutil
from pathlib import Path

# Configuration
MYSQL_VERSION = "8.0.35"
HOME = Path.home()
INSTALL_DIR = HOME / "mysql"
DATA_DIR = HOME / "mysql_data"
TMP_DIR = HOME / "mysql_tmp"
LIB_DIR = HOME / "mysql_libs"
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
    sys.stdout.flush()

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
    sys.stdout.flush()

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
    sys.stdout.flush()
    
    try:
        urllib.request.urlretrieve(mysql_url, mysql_path)
        print(f"Downloaded successfully to {mysql_path}")
        sys.stdout.flush()
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
    sys.stdout.flush()
    with tarfile.open(archive_path, 'r:xz') as tar:
        # Use filter parameter to avoid deprecation warning
        if sys.version_info >= (3, 12):
            tar.extractall(path=INSTALL_DIR, filter='data')
        else:
            tar.extractall(path=INSTALL_DIR)
    
    print(f"Extracted to {extract_dir}")
    sys.stdout.flush()
    return extract_dir

def install_libaio():
    """Download and install libaio library to user space"""
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    
    libaio_so = LIB_DIR / "libaio.so.1"
    
    if libaio_so.exists():
        print(f"libaio already installed: {libaio_so}")
        return LIB_DIR
    
    print("Installing libaio library to user space...")
    sys.stdout.flush()
    
    # Try to find libaio in system first
    try:
        result = subprocess.run(
            ["find", "/usr", "-name", "libaio.so.1", "2>/dev/null"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout.strip():
            system_lib = result.stdout.strip().split('\n')[0]
            print(f"Found system libaio at: {system_lib}")
            shutil.copy2(system_lib, libaio_so)
            print(f"Copied to: {libaio_so}")
            sys.stdout.flush()
            return LIB_DIR
    except:
        pass
    
    # Download libaio from Ubuntu package
    print("Downloading libaio from package repository...")
    sys.stdout.flush()
    
    # URL for libaio package (Ubuntu 20.04 compatible)
    libaio_url = "http://archive.ubuntu.com/ubuntu/pool/main/liba/libaio/libaio1_0.3.112-5_amd64.deb"
    deb_file = LIB_DIR / "libaio.deb"
    
    try:
        urllib.request.urlretrieve(libaio_url, deb_file)
        print("Downloaded libaio package")
        
        # Extract .deb file
        print("Extracting library...")
        sys.stdout.flush()
        subprocess.run(["ar", "x", str(deb_file)], cwd=LIB_DIR, check=True)
        
        # Extract data.tar.xz
        data_tar = LIB_DIR / "data.tar.xz"
        if data_tar.exists():
            with tarfile.open(data_tar) as tar:
                for member in tar.getmembers():
                    if 'libaio.so.1' in member.name:
                        tar.extract(member, path=LIB_DIR)
                        # Move to lib directory
                        extracted = LIB_DIR / member.name
                        if extracted.exists():
                            shutil.move(str(extracted), str(libaio_so))
                            print(f"Installed libaio to: {libaio_so}")
                            sys.stdout.flush()
                            break
        
        # Cleanup
        for f in LIB_DIR.glob("*.deb"):
            f.unlink()
        for f in LIB_DIR.glob("*.tar.*"):
            f.unlink()
        for f in LIB_DIR.glob("control*"):
            f.unlink()
        for d in LIB_DIR.glob("lib"):
            shutil.rmtree(d, ignore_errors=True)
        for d in LIB_DIR.glob("usr"):
            shutil.rmtree(d, ignore_errors=True)
            
        if libaio_so.exists():
            return LIB_DIR
        else:
            print("⚠️  Warning: Could not install libaio automatically")
            return None
            
    except Exception as e:
        print(f"Error installing libaio: {e}")
        return None

def initialize_database(mysql_home):
    """Initialize MySQL data directory"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    
    mysql_data_check = DATA_DIR / "mysql"
    if mysql_data_check.exists():
        print("MySQL data directory already initialized")
        return
    
    print("Initializing MySQL data directory...")
    sys.stdout.flush()
    mysqld = mysql_home / "bin" / "mysqld"
    
    # Set LD_LIBRARY_PATH to include our lib directory
    env = os.environ.copy()
    if LIB_DIR.exists():
        env['LD_LIBRARY_PATH'] = f"{LIB_DIR}:{env.get('LD_LIBRARY_PATH', '')}"
    
    cmd = [
        str(mysqld),
        "--initialize-insecure",
        f"--basedir={mysql_home}",
        f"--datadir={DATA_DIR}",
        f"--user={os.getenv('USER', 'user')}"
    ]
    
    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error initializing database:")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    
    print("MySQL data directory initialized")
    sys.stdout.flush()

def create_config_file(mysql_home):
    """Create MySQL configuration file"""
    config_path = HOME / "my.cnf"
    
    config_content = f"""[mysqld]
basedir={mysql_home}
datadir={DATA_DIR}
socket={TMP_DIR}/mysql.sock
pid-file={TMP_DIR}/mysql.pid
port={MYSQL_PORT}
bind-address=127.0.0.1
tmpdir={TMP_DIR}

# Performance settings optimized for low memory
max_connections=20
key_buffer_size=8M
max_allowed_packet=4M
thread_stack=128K
thread_cache_size=4
table_open_cache=64
sort_buffer_size=256K
read_buffer_size=256K
read_rnd_buffer_size=256K
join_buffer_size=256K
innodb_buffer_pool_size=128M
innodb_log_buffer_size=4M
innodb_flush_method=O_DIRECT
innodb_flush_log_at_trx_commit=2
query_cache_size=0
query_cache_type=0

# Connection settings to prevent timeouts
connect_timeout=10
wait_timeout=28800
interactive_timeout=28800
net_read_timeout=30
net_write_timeout=60

# Logging
log_error={TMP_DIR}/mysql_error.log
log_error_verbosity=3

# Skip some checks for compatibility
skip-name-resolve
skip-host-cache
performance_schema=OFF

# Security settings
skip-networking=0
default_authentication_plugin=mysql_native_password

[client]
socket={TMP_DIR}/mysql.sock
port={MYSQL_PORT}
protocol=tcp

[mysql]
socket={TMP_DIR}/mysql.sock
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"Configuration file created: {config_path}")
    sys.stdout.flush()
    return config_path

def check_mysql_process_alive(process):
    """Check if MySQL process is still running and show errors if not"""
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print(f"\n❌ ERROR: MySQL process died!")
        print(f"Exit code: {process.returncode}")
        if stdout:
            print(f"\nstdout:\n{stdout.decode()}")
        if stderr:
            print(f"\nstderr:\n{stderr.decode()}")
        
        # Show error log
        error_log = TMP_DIR / "mysql_error.log"
        if error_log.exists():
            print(f"\n📋 MySQL Error Log ({error_log}):")
            print("="*50)
            with open(error_log) as f:
                print(f.read())
            print("="*50)
        sys.stdout.flush()
        return False
    return True

def start_mysql(mysql_home, config_path):
    """Start MySQL server"""
    print("Starting MySQL server...")
    sys.stdout.flush()
    
    mysqld = mysql_home / "bin" / "mysqld"
    
    # Set LD_LIBRARY_PATH to include our lib directory
    env = os.environ.copy()
    if LIB_DIR.exists():
        env['LD_LIBRARY_PATH'] = f"{LIB_DIR}:{env.get('LD_LIBRARY_PATH', '')}"
    
    # Use explicit output files for debugging
    stdout_log = TMP_DIR / "mysql_stdout.log"
    stderr_log = TMP_DIR / "mysql_stderr.log"
    
    cmd = [str(mysqld), f"--defaults-file={config_path}"]
    
    # Start MySQL in background with output logging
    with open(stdout_log, 'w') as out, open(stderr_log, 'w') as err:
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=out,
            stderr=err
        )
    
    print(f"MySQL server started with PID: {process.pid}")
    print(f"Output logs: {stdout_log}, {stderr_log}")
    sys.stdout.flush()
    
    # Wait for MySQL to be ready
    print("Waiting for MySQL to start...")
    socket_path = TMP_DIR / "mysql.sock"
    
    for i in range(90):  # Increased timeout
        if not check_mysql_process_alive(process):
            sys.exit(1)
        
        if socket_path.exists():
            print(f"✅ Socket file created at {socket_path}")
            # Give it more time to fully initialize
            print("Waiting for MySQL to fully initialize...")
            time.sleep(5)
            
            # Verify process is still alive
            if not check_mysql_process_alive(process):
                sys.exit(1)
            
            print("MySQL is ready!")
            sys.stdout.flush()
            return process
        
        if i % 10 == 0 and i > 0:
            print(f"Still waiting... ({i} seconds elapsed)")
            # Check error log for issues
            error_log = TMP_DIR / "mysql_error.log"
            if error_log.exists():
                with open(error_log) as f:
                    log_content = f.read()
                    if log_content:
                        print(f"Current error log:\n{log_content[-500:]}")
            sys.stdout.flush()
        
        time.sleep(1)
    
    print("❌ ERROR: MySQL failed to start within 90 seconds")
    check_mysql_process_alive(process)
    sys.stdout.flush()
    sys.exit(1)

def test_connection(mysql_home):
    """Test MySQL connection before attempting to create database"""
    print("Testing MySQL connection...")
    sys.stdout.flush()
    
    mysql_client = mysql_home / "bin" / "mysql"
    socket_path = TMP_DIR / "mysql.sock"
    
    # Set LD_LIBRARY_PATH
    env = os.environ.copy()
    if LIB_DIR.exists():
        env['LD_LIBRARY_PATH'] = f"{LIB_DIR}:{env.get('LD_LIBRARY_PATH', '')}"
    
    # Simple connection test
    cmd = [
        str(mysql_client),
        f"--socket={socket_path}",
        "-u", "root",
        "-e", "SELECT 'Connection successful' as status;"
    ]
    
    for attempt in range(5):
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ Connection test successful!")
                print(result.stdout)
                sys.stdout.flush()
                return True
            else:
                print(f"⚠️  Connection test failed (attempt {attempt + 1}/5)")
                print(f"stderr: {result.stderr}")
                if attempt < 4:
                    print("Retrying in 3 seconds...")
                    time.sleep(3)
        except subprocess.TimeoutExpired:
            print(f"⚠️  Connection test timed out (attempt {attempt + 1}/5)")
            if attempt < 4:
                print("Retrying in 3 seconds...")
                time.sleep(3)
        except Exception as e:
            print(f"⚠️  Connection test error: {e} (attempt {attempt + 1}/5)")
            if attempt < 4:
                print("Retrying in 3 seconds...")
                time.sleep(3)
        
        sys.stdout.flush()
    
    print("❌ Failed to establish MySQL connection after 5 attempts")
    return False

def setup_database(mysql_home):
    """Create database and user"""
    print("Creating database and user...")
    sys.stdout.flush()
    
    mysql_client = mysql_home / "bin" / "mysql"
    socket_path = TMP_DIR / "mysql.sock"
    
    # Set LD_LIBRARY_PATH
    env = os.environ.copy()
    if LIB_DIR.exists():
        env['LD_LIBRARY_PATH'] = f"{LIB_DIR}:{env.get('LD_LIBRARY_PATH', '')}"
    
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
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ Error creating database:")
            print(f"stderr: {result.stderr}")
            sys.exit(1)
        
        print(result.stdout)
        print("✅ Database and user created successfully!")
        sys.stdout.flush()
        
    except subprocess.TimeoutExpired:
        print("❌ Database creation timed out")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def create_helper_scripts(mysql_home):
    """Create convenience scripts for managing MySQL"""
    
    # Start script
    start_script = HOME / "mysql-start.sh"
    with open(start_script, 'w') as f:
        f.write(f"""#!/bin/bash
export LD_LIBRARY_PATH="{LIB_DIR}:$LD_LIBRARY_PATH"
MYSQL_HOME="{mysql_home}"
"$MYSQL_HOME/bin/mysqld" --defaults-file="$HOME/my.cnf" &
echo "MySQL started. PID: $!"
""")
    start_script.chmod(0o755)
    
    # Stop script
    stop_script = HOME / "mysql-stop.sh"
    with open(stop_script, 'w') as f:
        f.write(f"""#!/bin/bash
export LD_LIBRARY_PATH="{LIB_DIR}:$LD_LIBRARY_PATH"
MYSQL_HOME="{mysql_home}"
"$MYSQL_HOME/bin/mysqladmin" --socket="{TMP_DIR}/mysql.sock" -u root shutdown
echo "MySQL stopped."
""")
    stop_script.chmod(0o755)
    
    # Connect script
    connect_script = HOME / "mysql-connect.sh"
    with open(connect_script, 'w') as f:
        f.write(f"""#!/bin/bash
export LD_LIBRARY_PATH="{LIB_DIR}:$LD_LIBRARY_PATH"
MYSQL_HOME="{mysql_home}"
"$MYSQL_HOME/bin/mysql" --socket="{TMP_DIR}/mysql.sock" -u root
""")
    connect_script.chmod(0o755)
    
    print("Helper scripts created:")
    print(f"  Start:   {start_script}")
    print(f"  Stop:    {stop_script}")
    print(f"  Connect: {connect_script}")
    sys.stdout.flush()

def print_summary(mysql_process):
    """Print installation summary"""
    print_section("Installation Complete!")
    print("✅ MySQL is now running!")
    print(f"\nMySQL Process PID: {mysql_process.pid}")
    print("\nConnection Details:")
    print(f"  Host:     127.0.0.1")
    print(f"  Port:     {MYSQL_PORT}")
    print(f"  Socket:   {TMP_DIR}/mysql.sock")
    print(f"  Database: {DB_NAME}")
    print(f"  User:     {DB_USER}")
    print(f"  Password: {DB_PASSWORD}")
    print("\nConnection String:")
    print(f"  mysql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{MYSQL_PORT}/{DB_NAME}")
    print("\nManagement Scripts:")
    print(f"  Start MySQL: {HOME}/mysql-start.sh")
    print(f"  Stop MySQL:  {HOME}/mysql-stop.sh")
    print(f"  Connect:     {HOME}/mysql-connect.sh")
    print("\nLog Files:")
    print(f"  Error Log:  {TMP_DIR}/mysql_error.log")
    print(f"  Output Log: {TMP_DIR}/mysql_stdout.log")
    print("\n⚠️  IMPORTANT: Change DB_PASSWORD before using in production!")
    print()
    sys.stdout.flush()

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
    sys.stdout.flush()
    
    try:
        # Download and extract MySQL
        archive_path = download_mysql()
        mysql_home = extract_mysql(archive_path)
        
        # Install required libraries
        print_section("Installing Dependencies")
        lib_dir = install_libaio()
        if not lib_dir:
            print("⚠️  Warning: libaio not installed, MySQL may not start")
            print("   If MySQL fails, you'll need root access to install libaio")
        
        # Initialize and configure
        initialize_database(mysql_home)
        config_path = create_config_file(mysql_home)
        
        # Start MySQL
        mysql_process = start_mysql(mysql_home, config_path)
        
        # Test connection before trying to create database
        if not test_connection(mysql_home):
            print("❌ Cannot establish connection to MySQL")
            check_mysql_process_alive(mysql_process)
            sys.exit(1)
        
        # Setup database and user
        setup_database(mysql_home)
        
        # Create helper scripts
        create_helper_scripts(mysql_home)
        
        # Print summary
        print_summary(mysql_process)
        
        print("✅ Installation completed successfully!")
        print("\n💡 To keep MySQL running, this script must stay active.")
        print("   Press Ctrl+C to stop MySQL and exit.")
        
        # Keep the script running to maintain MySQL process
        try:
            while True:
                time.sleep(60)
                if not check_mysql_process_alive(mysql_process):
                    print("❌ MySQL process has died!")
                    sys.exit(1)
        except KeyboardInterrupt:
            print("\n\nShutting down MySQL...")
            mysql_process.terminate()
            mysql_process.wait(timeout=10)
            print("MySQL stopped.")
        
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
