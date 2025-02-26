from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import re
import psycopg2
from psycopg2.pool import SimpleConnectionPool
import ast

app = Flask(__name__)
CORS(app)
pool = psycopg2.pool.SimpleConnectionPool( 2, 50, database= "ip_database", user= "postgres", password= "postgres", host= "localhost" , port= 5432)
conn = pool.getconn()

# Database setup
def init_db():
    cursor = conn.cursor()
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_info (
            ip TEXT PRIMARY KEY,
            details TEXT
        )
    ''')
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
        return None
    finally:
        pool.putconn(conn)    
    
    

def ensure_table_exists():
    try:
        cursor = conn.cursor()
        print("ensure_table_exists")
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ip_info')")
        exists = cursor.fetchone()[0]
        if not exists:
            init_db()
    except Exception as e:
        conn.rollback()
        print(f"Error checking/creating table: {e}")    

# Validate IP address
def is_valid_ip(ip):
    pattern = re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
    return pattern.match(ip) is not None

# Fetch IP details from ipinfo.io
def fetch_ip_details(ip):
    response = requests.get(f'https://ipinfo.io/{ip}/geo')
    if response.status_code == 200:
        data = response.json()
        filtered_data = {key: value for key, value in data.items() if key != "ip"}
        return filtered_data
    return None

# Store IP details in the database
def store_ip_details(ip, details):
    cursor = conn.cursor()
    details =  ast.literal_eval(details)
    if details['loc'] :
        pass
    else :
        details = {"noData" : "No Data for the given IP address"}    
    cursor.execute('INSERT INTO ip_info (ip, details) VALUES (%s, %s)', (ip, str(details)))
    conn.commit()

# Fetch IP details from the database
def get_ip_details(ip):
    cursor = conn.cursor()
    cursor.execute('SELECT details FROM ip_info WHERE ip = %s', (ip,))
    result = cursor.fetchone()
    return result[0] if result else None

@app.route('/fetch-ip', methods=['POST'])
def fetch_ip():
    ensure_table_exists()
    ip = request.form.get('ip')
    ip = re.sub(r'[^0-9.]', '', ip)  # replace all the special characters from ip address
    if not is_valid_ip(ip):
        return jsonify({'error': 'Invalid IP address'}), 400

    details = get_ip_details(ip)
    if details:
        return jsonify({'ip': ip, 'details': details}), 200
    else:
        details = fetch_ip_details(ip)
        if details:
            store_ip_details(ip, str(details))
            return jsonify({'ip': ip, 'details': details}), 200
        else:
            return jsonify({'error': 'Could not fetch details from ipinfo.io'}), 500

@app.route('/store-ip', methods=['GET'])
def store_ip():
    ensure_table_exists()
    cursor = conn.cursor()
    cursor.execute('SELECT ip,details FROM ip_info')
    ips = cursor.fetchall()
    # conn.close()
    return jsonify({'stored_ips': [ip for ip in ips]}), 200

@app.route('/', methods=["GET"]) 
def home():
    return render_template('get_ip_tailwind.html')

if __name__ == '__main__':
    app.run(host = 'localhost',debug=True)