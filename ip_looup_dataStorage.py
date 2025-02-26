from flask import Flask, request, jsonify
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_info (
            ip TEXT PRIMARY KEY,
            details TEXT
        )
    ''')
    conn.commit()

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
    ip = request.form.get('ip')
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
    cursor = conn.cursor()
    cursor.execute('SELECT ip,details FROM ip_info')
    ips = cursor.fetchall()
    # conn.close()
    return jsonify({'stored_ips': [ip for ip in ips]}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True)