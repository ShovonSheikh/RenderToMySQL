import subprocess

def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

# Update packages
run("sudo apt update -y")

# Install MySQL Server
run("sudo apt install mysql-server -y")

# Start and enable MySQL
run("sudo systemctl start mysql")
run("sudo systemctl enable mysql")

# Your custom values
db_name = "mydb"
db_user = "myuser"
db_pass = "mypassword"

# Allow MySQL to accept remote connections
# (We change bind-address in mysqld.cnf)
run("sudo sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf")

# Restart MySQL to apply remote access
run("sudo systemctl restart mysql")

# SQL commands for DB + user
sql = f"""
CREATE DATABASE IF NOT EXISTS {db_name};
CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_pass}';
GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'%';
FLUSH PRIVILEGES;
"""

# Execute SQL
run(f"sudo mysql -e \"{sql}\"")

# Get server IP
import socket
hostname = socket.gethostname()
server_ip = socket.gethostbyname(hostname)

# Print connection details
print("\n===== MySQL Remote Connection Info =====")
print(f"Host: {server_ip}")
print("Port: 3306")
print(f"Database: {db_name}")
print(f"User: {db_user}")
print(f"Password: {db_pass}")
print("========================================\n")
