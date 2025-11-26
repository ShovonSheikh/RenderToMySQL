#!/usr/bin/env python3
"""
Sample Application that uses MySQL
File: your_app.py
This is a Flask web application that connects to MySQL
"""

from flask import Flask, jsonify, request
import mysql.connector
import os
from datetime import datetime

app = Flask(__name__)

# Database configuration - reads from environment or .mysql_credentials file
def get_db_config():
    """Get database configuration"""
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'database': os.getenv('DB_NAME', 'myapp_db'),
        'user': os.getenv('DB_USER', 'appuser'),
        'password': os.getenv('DB_PASSWORD', '')
    }
    
    # Try to read from credentials file if password not set
    if not config['password']:
        try:
            with open('.mysql_credentials', 'r') as f:
                for line in f:
                    if line.startswith('DB_PASSWORD='):
                        config['password'] = line.split('=')[1].strip()
                    elif line.startswith('DB_USER='):
                        config['user'] = line.split('=')[1].strip()
                    elif line.startswith('DB_NAME='):
                        config['database'] = line.split('=')[1].strip()
        except FileNotFoundError:
            pass
    
    return config

def get_db_connection():
    """Create database connection"""
    config = get_db_config()
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

def init_database():
    """Initialize database with sample table"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create a sample table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create another sample table for posts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                title VARCHAR(200) NOT NULL,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        print("✓ Database tables initialized successfully")
        return True
    except mysql.connector.Error as err:
        print(f"Error initializing database: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

@app.route('/')
def home():
    """Home page"""
    return jsonify({
        'message': 'MySQL on Render - Application Running!',
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            '/': 'Home page',
            '/health': 'Health check',
            '/users': 'List all users (GET) or create user (POST)',
            '/users/<id>': 'Get specific user',
            '/posts': 'List all posts (GET) or create post (POST)',
            '/db-info': 'Database information'
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/db-info')
def db_info():
    """Get database information"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get MySQL version
        cursor.execute("SELECT VERSION() as version")
        version = cursor.fetchone()
        
        # Get current database
        cursor.execute("SELECT DATABASE() as current_db")
        current_db = cursor.fetchone()
        
        # Get table list
        cursor.execute("SHOW TABLES")
        tables = [table[f"Tables_in_{current_db['current_db']}"] for table in cursor.fetchall()]
        
        # Get user count
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()
        
        # Get post count
        cursor.execute("SELECT COUNT(*) as count FROM posts")
        post_count = cursor.fetchone()
        
        return jsonify({
            'mysql_version': version['version'],
            'database': current_db['current_db'],
            'tables': tables,
            'user_count': user_count['count'],
            'post_count': post_count['count'],
            'connection': 'active'
        })
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/users', methods=['GET', 'POST'])
def users():
    """Handle users - GET to list, POST to create"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # List all users
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            users_list = cursor.fetchall()
            return jsonify({
                'users': users_list,
                'count': len(users_list)
            })
        
        elif request.method == 'POST':
            # Create new user
            data = request.get_json()
            name = data.get('name')
            email = data.get('email')
            
            if not name or not email:
                return jsonify({'error': 'Name and email are required'}), 400
            
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                (name, email)
            )
            conn.commit()
            
            return jsonify({
                'message': 'User created successfully',
                'user_id': cursor.lastrowid
            }), 201
    
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/users/<int:user_id>')
def get_user(user_id):
    """Get specific user by ID"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user:
            return jsonify(user)
        else:
            return jsonify({'error': 'User not found'}), 404
    
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/posts', methods=['GET', 'POST'])
def posts():
    """Handle posts - GET to list, POST to create"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            # List all posts with user information
            cursor.execute("""
                SELECT p.*, u.name as author_name, u.email as author_email 
                FROM posts p 
                JOIN users u ON p.user_id = u.id 
                ORDER BY p.created_at DESC
            """)
            posts_list = cursor.fetchall()
            return jsonify({
                'posts': posts_list,
                'count': len(posts_list)
            })
        
        elif request.method == 'POST':
            # Create new post
            data = request.get_json()
            user_id = data.get('user_id')
            title = data.get('title')
            content = data.get('content')
            
            if not user_id or not title:
                return jsonify({'error': 'user_id and title are required'}), 400
            
            cursor.execute(
                "INSERT INTO posts (user_id, title, content) VALUES (%s, %s, %s)",
                (user_id, title, content)
            )
            conn.commit()
            
            return jsonify({
                'message': 'Post created successfully',
                'post_id': cursor.lastrowid
            }), 201
    
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("STARTING APPLICATION")
    print("=" * 60)
    
    # Initialize database tables
    print("\nInitializing database...")
    if init_database():
        print("✓ Database ready\n")
    else:
        print("✗ Database initialization failed\n")
    
    # Get configuration
    config = get_db_config()
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}")
    print(f"Host: {config['host']}:{config['port']}")
    print("=" * 60 + "\n")
    
    # Start Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
