import os, hmac
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from fixed_assets.models import register_models
from fixed_assets.routes import create_fixed_assets_blueprint

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder='templates', static_folder='static')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config['SECRET_KEY'] = os.environ.get('FAR_SECRET_KEY') or 'dev-only-change-this-secret-before-deployment'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'

# This is intentionally independent of CETTP. Configure FAR_DATABASE_URL with a
# dedicated database. Local development falls back to a separate SQLite file.
database_url = os.environ.get('FAR_DATABASE_URL')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif database_url.startswith('postgresql://') and '+psycopg' not in database_url:
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
else:
    database_url = 'sqlite:///' + os.path.join(BASE_DIR, 'far_governance_dev.db')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)
models = register_models(db)
app.register_blueprint(create_fixed_assets_blueprint(db, models))

@app.context_processor
def inject_shell_context():
    return {'current_role': session.get('role'), 'current_user_name': session.get('actor_name')}

@app.route('/')
def home():
    if session.get('role') in ('asset_admin', 'asset_accountant', 'asset_auditor', 'tax'):
        return redirect(url_for('fixed_assets.dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        expected_email = os.environ.get('FAR_ADMIN_EMAIL', '').strip().lower()
        expected_password = os.environ.get('FAR_ADMIN_PASSWORD', '')
        if not expected_email or not expected_password:
            flash('Portal administrator credentials have not been configured. Set FAR_ADMIN_EMAIL and FAR_ADMIN_PASSWORD.', 'danger')
        elif hmac.compare_digest(email, expected_email) and hmac.compare_digest(password, expected_password):
            session.clear()
            session['role'] = 'asset_admin'
            session['actor_name'] = email
            session.permanent = True
            return redirect(url_for('fixed_assets.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.get('/health')
def health():
    return {'status': 'ok', 'application': 'Fixed Asset Governance Portal'}

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
