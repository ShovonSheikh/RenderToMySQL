import subprocess
import psutil
import platform
import socket

def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

# Update system
run("sudo apt update -y")

# Install MySQL
run("sudo apt install mysql-server -y")

# Start MySQL
run("sudo systemctl start mysql")
run("sudo systemctl enable mysql")

# DB config
db_name = "mydb"
db_user = "myuser"
db_pass = "mypassword"

# Enable remote access
run("sudo sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf")
run("sudo systemctl restart mysql")

# Create DB + user
sql = f"""
CREATE DATABASE IF NOT EXISTS {db_name};
CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_pass}';
GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'%';
FLUSH PRIVILEGES;
"""

run(f"sudo mysql -e \"{sql}\"")

# System info
cpu_count = psutil.cpu_count(logical=True)
cpu_percent = psutil.cpu_percent(interval=1)
mem = psutil.virtual_memory()
disk = psutil.disk_usage("/")
os_name = platform.system()
os_ver = platform.release()

# Server IP
hostname = socket.gethostname()
server_ip = socket.gethostbyname(hostname)

print("\n===== MySQL Remote Connection Info =====")
print(f"Host: {server_ip}")
print("Port: 3306")
print(f"Database: {db_name}")
print(f"User: {db_user}")
print(f"Password: {db_pass}")
print("========================================\n")

print("===== System Information =====")
print(f"OS: {os_name} {os_ver}")
print(f"CPU Cores: {cpu_count}")
print(f"CPU Usage: {cpu_percent}%")
print(f"Memory: {mem.total // (1024**3)} GB total, {mem.available // (1024**3)} GB free")
print(f"Disk: {disk.total // (1024**3)} GB total, {disk.free // (1024**3)} GB free")
print("================================")
