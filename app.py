from flask import Flask, request, jsonify, redirect, render_template, send_file
import psycopg2
import sqlite3
import string
import random
import os
# import qrcode
from io import BytesIO

app = Flask(__name__)
DATABASE = 'urls.db'
DATABASE_URL = os.getenv('DATABASE_URL')

# Generate short code
def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Init DB
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        short_code TEXT UNIQUE NOT NULL,
        long_url TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        clicks INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

if os.getenv('DATABASE_URL'):
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    import psycopg2
    from urllib.parse import urlparse

    result = urlparse(DATABASE_URL)

    def get_db_connection():
        return psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
else:
    import sqlite3
    def get_db_connection():
        return sqlite3.connect('urls.db')


# API: Create short URL
@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    data = request.get_json()
    long_url = data.get ('url')

    if not long_url:
        return jsonify({'error': 'URL is required'}), 400

    # Generate code until we find one that is available
    while True:
        short_code = generate_short_code()
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('INSERT INTO urls (short_code, long_url) VALUES (?, ?)',(short_code, long_url))
            conn.commit()
            break
        except psycopg2.IntegrityError:
            continue # The code already exists, we are generation a new one
        finally:
            conn.close()

    return jsonify({
        'short_url': f'http://localhost:5000/{short_code}',
        'short_code': short_code,
        'long_url': long_url
    }), 201

# Redirect via short link
@app.route('/<short_code>')
def redirect_to_url(short_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT long_url FROM urls WHERE short_code = ?', (short_code,))
    result = cursor.fetchone()

    if result:
        long_url = result[0]
        #  Increasing the click counter
        cursor.execute('UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?', (short_code,))
        conn.commit()
        conn.close()
        return redirect(long_url)

    conn.close()
    return jsonify({'error': 'URL not found'}), 404

# API: Statistics via link
@app.route('/api/stats/<short_code>')
def get_stats(short_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM urls WHERE short_code = ?', (short_code,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return jsonify({
            'short_code': result[1],
            'long_url': result[2],
            'created_at': result[3],
            'clicks': result[4]
        })

    return jsonify({'error': 'Not found'}), 404

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/qr/<short_code>')
def generate_qr(short_code):
    short_url = f"https://yoursite.com/{short_code}"

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(short_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", black_color="white")

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    return send_file(buf, mimetype='image/png')

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    if os.getenv('DATABASE_URL'):
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            short_code VARCHAR(10) UNIQUE NOT NULL,
            long_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0
        )
        ''')
    else:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            long_url TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0
        )
        ''')

    conn.commit()
    conn.close()

with app.app_context():
    init_db()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)























