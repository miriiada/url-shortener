from flask import Flask, request, jsonify, redirect, render_template
import sqlite3
import string
import random

app = Flask(__name__)
DATABASE = 'urls.db'

# Generate short code
def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Init DB
def init_db():
    conn = sqlite3.connect(DATABASE)
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
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute('INSERT INTO urls (short_code, long_url) VALUES (?, ?)',(short_code, long_url))
            conn.commit()
            break
        except sqlite3.IntegrityError:
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
    conn = sqlite3.connect(DATABASE)
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
    conn = sqlite3.connect(DATABASE)
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)























