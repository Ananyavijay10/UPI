"""
=============================================================================
UPI Fraud Detection System - Production Flask Application (app.py)
=============================================================================
Enterprise Full-Stack Architecture:
- Framework: Flask RESTful Web Service
- Database: SQLite with SQLAlchemy ORM (User, Transaction, Prediction, ModelMetrics)
- Security: Werkzeug Password Hashing, Session Authentication, RBAC (USER / ADMIN)
- Machine Learning: Pre-trained Random Forest Pipeline (fraud_model.pkl)
- Analytics: Live aggregations feeding Chart.js visualizations
=============================================================================
"""

import os
import json
import logging
from functools import wraps
from datetime import datetime, timezone

from flask import (
    Flask, request, jsonify, render_template, redirect, url_for, session, flash
)
from sqlalchemy import func, desc

from config import Config
from models import db, User, Transaction, Prediction, ModelMetrics
from predict import load_model, predict_fraud_risk, validate_transaction_input
from train_model import train_and_compare_models

# Configure Application Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database
db.init_app(app)

# Cached In-Memory Model
active_model = None


# ---------------------------------------------------------------------------
# Authentication Decorators
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required. Please login.'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required.'}), 401
            flash('Please log in with an administrator account.', 'warning')
            return redirect(url_for('login', next=request.path))
        if session.get('user_role') != 'ADMIN':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Administrator privileges required.'}), 403
            flash('Access denied: Administrator privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Database & Model Bootstrap Helper
# ---------------------------------------------------------------------------
def bootstrap_database_and_models():
    """
    Initializes database schema, seeds default accounts and sample transactions,
    and loads the trained Random Forest model.
    """
    global active_model
    with app.app_context():
        db.create_all()

        # Migrate SQLite columns if not present
        try:
            with db.engine.connect() as conn:
                cols = [row[1] for row in conn.execute(db.text("PRAGMA table_info(transactions)"))]
                if 'high_tx_reason' not in cols:
                    conn.execute(db.text("ALTER TABLE transactions ADD COLUMN high_tx_reason TEXT"))
                if 'upi_id' not in cols:
                    conn.execute(db.text("ALTER TABLE transactions ADD COLUMN upi_id TEXT"))
                if 'payment_mode' not in cols:
                    conn.execute(db.text("ALTER TABLE transactions ADD COLUMN payment_mode TEXT"))
                conn.commit()
        except Exception as e:
            logging.warning("SQLite column migration notice: %s", str(e))

        # Seed Default Admin Account
        admin = User.query.filter_by(email='admin@upi.bank').first()
        if not admin:
            admin = User(name='Security Administrator', email='admin@upi.bank', role='ADMIN')
            admin.set_password('Admin@123')
            db.session.add(admin)
            logging.info("Default Admin account seeded: admin@upi.bank / Admin@123")

        # Seed Default User Account
        demo_user = User.query.filter_by(email='user@upi.bank').first()
        if not demo_user:
            demo_user = User(name='Rohan Sharma', email='user@upi.bank', role='USER')
            demo_user.set_password('User@123')
            db.session.add(demo_user)
            logging.info("Default User account seeded: user@upi.bank / User@123")

        db.session.commit()

        # Ensure Model File Exists
        if not os.path.exists(Config.MODEL_PATH):
            logging.info("Model file not found. Triggering initial training...")
            try:
                active_model, _ = train_and_compare_models(Config.DATASET_PATH, save_production=True)
            except Exception as e:
                logging.error("Failed to train model at startup: %s", str(e), exc_info=True)
        else:
            try:
                active_model = load_model(Config.MODEL_PATH)
                logging.info("Loaded pre-trained model from: %s", Config.MODEL_PATH)
            except Exception as e:
                logging.error("Failed to load model: %s", str(e))

        # Seed Sample Historical Transactions if database is empty
        if Transaction.query.count() == 0 and demo_user:
            seed_sample_transactions(demo_user.id)

        # Seed ModelMetrics table from model_metrics.json if empty
        if ModelMetrics.query.count() == 0 and os.path.exists(Config.METRICS_JSON_PATH):
            try:
                with open(Config.METRICS_JSON_PATH, 'r') as f:
                    data = json.load(f)
                    for m_name, m_vals in data.get('comparison', {}).items():
                        metric_row = ModelMetrics(
                            model_name=m_name,
                            accuracy=m_vals.get('accuracy', 0),
                            precision=m_vals.get('precision', 0),
                            recall=m_vals.get('recall', 0),
                            f1_score=m_vals.get('f1_score', 0),
                            roc_auc=m_vals.get('roc_auc', 0),
                            pr_auc=m_vals.get('pr_auc')
                        )
                        db.session.add(metric_row)
                db.session.commit()
                logging.info("Model metrics seeded into SQLite database.")
            except Exception as e:
                logging.warning("Failed to seed model metrics: %s", str(e))


def seed_sample_transactions(user_id: int):
    """Populates baseline transactions for system analytics."""
    sample_data = [
        # (amount, time, type, freq, avg_amt, is_new, dev_chg, loc_chg, failed, ben_freq)
        (450.0, 13, 'Food', 1, 600.0, 0, 0, 0, 0, 12),
        (1200.0, 11, 'Shopping', 2, 1000.0, 0, 0, 0, 0, 6),
        (350.0, 9, 'Travel', 1, 500.0, 0, 0, 0, 0, 4),
        (5200.0, 22, 'Shopping', 3, 1400.0, 1, 0, 0, 0, 1),
        (8500.0, 20, 'Bills', 2, 2500.0, 0, 0, 0, 0, 3),
        (25.0, 3, 'Other', 4, 1200.0, 1, 1, 0, 2, 1),
        (48000.0, 2, 'Money Transfer', 5, 2000.0, 1, 1, 1, 3, 1),
        (2800.0, 15, 'Education', 1, 2500.0, 0, 0, 0, 0, 5),
        (150.0, 18, 'Recharge', 1, 200.0, 0, 0, 0, 0, 8),
        (32000.0, 1, 'Money Transfer', 3, 3000.0, 1, 1, 0, 1, 1),
        (750.0, 16, 'Food', 2, 800.0, 0, 0, 0, 0, 9),
        (18500.0, 23, 'Shopping', 4, 1500.0, 1, 0, 1, 1, 1),
    ]

    for item in sample_data:
        amt, hr, ttype, tfreq, avgamt, isnew, devchg, locchg, failed, benfreq = item
        tx = Transaction(
            user_id=user_id,
            amount=amt,
            time=hr,
            transaction_type=ttype,
            transaction_frequency=tfreq,
            avg_transaction_amount=avgamt,
            is_new_beneficiary=isnew,
            device_changed=devchg,
            location_changed=locchg,
            failed_attempts=failed,
            beneficiary_frequency=benfreq
        )
        db.session.add(tx)
        db.session.flush()

        # Run prediction
        res = predict_fraud_risk({
            'amount': amt,
            'time': hr,
            'transaction_type': ttype,
            'transaction_frequency': tfreq,
            'avg_transaction_amount': avgamt,
            'is_new_beneficiary': isnew,
            'device_changed': devchg,
            'location_changed': locchg,
            'failed_attempts': failed,
            'beneficiary_frequency': benfreq
        }, model=active_model)

        pred = Prediction(
            transaction_id=tx.id,
            fraud_probability=res['fraud_probability'],
            risk_score=res['risk_score'],
            risk_level=res['risk_level'],
            status=res['status'],
            action_status='PENDING' if res['status'] != 'SAFE' else 'VERIFIED'
        )
        db.session.add(pred)

    db.session.commit()
    logging.info("Sample transactions successfully seeded.")


# ---------------------------------------------------------------------------
# PUBLIC / MARKETING / LANDING ROUTES
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """Landing Page showcasing overview, architecture steps, and entry points."""
    return render_template('index.html')


# ---------------------------------------------------------------------------
# AUTHENTICATION ROUTES
# ---------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    # Handle POST
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    next_url = request.args.get('next') or request.form.get('next')

    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        session.clear()
        session.permanent = True
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        session['user_role'] = user.role

        flash(f'Welcome back, {user.name}!', 'success')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('admin_dashboard' if user.is_admin() else 'dashboard'))

    flash('Invalid email or password. Please verify your credentials.', 'danger')
    return render_template('login.html', email=email), 401


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('register.html')

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not name or not email or not password:
        flash('All fields are required.', 'danger')
        return render_template('register.html', name=name, email=email), 400

    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return render_template('register.html', name=name, email=email), 400

    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'danger')
        return render_template('register.html', name=name, email=email), 400

    if User.query.filter_by(email=email).first():
        flash('An account with this email already exists.', 'warning')
        return render_template('register.html', name=name), 409

    # Create new standard user
    user = User(name=name, email=email, role='USER')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash('Registration successful! Please log in with your credentials.', 'success')
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been securely logged out.', 'info')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# USER DASHBOARD & ANALYSIS PAGES
# ---------------------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    """Main user dashboard presenting real-time stats from SQLite."""
    user_id = session['user_id']
    is_admin = session.get('user_role') == 'ADMIN'

    # Filter by user unless admin
    base_query = db.session.query(Transaction, Prediction).join(Prediction, Transaction.id == Prediction.transaction_id)
    if not is_admin:
        base_query = base_query.filter(Transaction.user_id == user_id)

    total_count = base_query.count()
    safe_count = base_query.filter(Prediction.status == 'SAFE').count()
    suspicious_count = base_query.filter(Prediction.status == 'SUSPICIOUS').count()
    fraud_count = base_query.filter(Prediction.status == 'FRAUD LIKELY').count()

    high_risk_count = base_query.filter(Prediction.risk_level.in_(['HIGH', 'CRITICAL'])).count()

    # Average transaction amount
    avg_amt_row = db.session.query(func.avg(Transaction.amount))
    if not is_admin:
        avg_amt_row = avg_amt_row.filter(Transaction.user_id == user_id)
    avg_amount = avg_amt_row.scalar() or 0.0

    fraud_rate = (fraud_count / total_count * 100) if total_count > 0 else 0.0

    # Recent 5 transactions
    recent_transactions = (
        base_query
        .order_by(desc(Transaction.created_at))
        .limit(5)
        .all()
    )

    stats = {
        'total': total_count,
        'safe': safe_count,
        'suspicious': suspicious_count,
        'fraud': fraud_count,
        'high_risk': high_risk_count,
        'avg_amount': round(avg_amount, 2),
        'fraud_rate': round(fraud_rate, 1)
    }

    return render_template(
        'dashboard.html',
        stats=stats,
        recent_transactions=recent_transactions,
        categories=Config.TRANSACTION_TYPES
    )


@app.route('/analyze')
@login_required
def analyze():
    """Interactive transaction analysis page."""
    return render_template('analyze.html', categories=Config.TRANSACTION_TYPES)


@app.route('/history')
@login_required
def history():
    """Transaction history page with search, filters, and pagination."""
    return render_template('history.html', categories=Config.TRANSACTION_TYPES)


@app.route('/transaction/<int:tx_id>')
@login_required
def transaction_detail(tx_id):
    """Detailed view for a single transaction with verification actions."""
    user_id = session['user_id']
    is_admin = session.get('user_role') == 'ADMIN'

    tx = Transaction.query.get_or_404(tx_id)
    if not is_admin and tx.user_id != user_id:
        flash('Unauthorized access to transaction record.', 'danger')
        return redirect(url_for('history'))

    pred = Prediction.query.filter_by(transaction_id=tx.id).first()

    # Generate explainable indicators for this transaction
    tx_dict = tx.to_dict()
    indicators = predict_fraud_risk(tx_dict, model=active_model).get('system_reasons', [])

    return render_template(
        'transaction.html',
        tx=tx,
        pred=pred,
        indicators=indicators
    )


@app.route('/analytics')
@login_required
def analytics():
    """Analytics charts powered by Chart.js."""
    return render_template('analytics.html')


@app.route('/model')
@login_required
def model_performance():
    """Model performance benchmarks, confusion matrix, and comparison table."""
    metrics_data = {}
    if os.path.exists(Config.METRICS_JSON_PATH):
        try:
            with open(Config.METRICS_JSON_PATH, 'r') as f:
                metrics_data = json.load(f)
        except Exception as e:
            logging.error("Failed to read metrics json: %s", str(e))

    return render_template('model.html', metrics=metrics_data)


# ---------------------------------------------------------------------------
# ADMIN ROUTES
# ---------------------------------------------------------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    """Administrator control center."""
    total_users = User.query.count()
    total_tx = Transaction.query.count()
    fraud_tx = Prediction.query.filter_by(status='FRAUD LIKELY').count()
    suspicious_tx = Prediction.query.filter_by(status='SUSPICIOUS').count()
    safe_tx = Prediction.query.filter_by(status='SAFE').count()
    fraud_rate = (fraud_tx / total_tx * 100) if total_tx > 0 else 0.0

    recent_all = (
        db.session.query(Transaction, Prediction, User)
        .join(Prediction, Transaction.id == Prediction.transaction_id)
        .outerjoin(User, Transaction.user_id == User.id)
        .order_by(desc(Transaction.created_at))
        .limit(10)
        .all()
    )

    metrics_data = {}
    if os.path.exists(Config.METRICS_JSON_PATH):
        try:
            with open(Config.METRICS_JSON_PATH, 'r') as f:
                metrics_data = json.load(f)
        except Exception:
            pass

    stats = {
        'total_users': total_users,
        'total_tx': total_tx,
        'fraud_tx': fraud_tx,
        'suspicious_tx': suspicious_tx,
        'safe_tx': safe_tx,
        'fraud_rate': round(fraud_rate, 2),
        'model_name': metrics_data.get('production_model', 'Random Forest Classifier'),
        'trained_at': metrics_data.get('trained_at', 'N/A')
    }

    return render_template('admin.html', stats=stats, recent_transactions=recent_all)


@app.route('/admin/retrain', methods=['POST'])
@admin_required
def retrain_model_endpoint():
    """Triggers ML retraining on the current dataset."""
    global active_model
    try:
        logging.info("Admin initiated model retraining on: %s", Config.DATASET_PATH)
        active_model, metadata = train_and_compare_models(Config.DATASET_PATH, save_production=True)

        # Update database ModelMetrics table
        for m_name, m_vals in metadata.get('comparison', {}).items():
            metric_row = ModelMetrics(
                model_name=m_name,
                accuracy=m_vals.get('accuracy', 0),
                precision=m_vals.get('precision', 0),
                recall=m_vals.get('recall', 0),
                f1_score=m_vals.get('f1_score', 0),
                roc_auc=m_vals.get('roc_auc', 0),
                pr_auc=m_vals.get('pr_auc')
            )
            db.session.add(metric_row)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Model training completed successfully.',
            'metadata': metadata
        }), 200

    except Exception as e:
        logging.error("Retraining failed: %s", str(e), exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Model retraining failed: {str(e)}'
        }), 500


# ---------------------------------------------------------------------------
# REST API ENDPOINTS
# ---------------------------------------------------------------------------
@app.route('/predict', methods=['POST'])
def api_predict():
    """
    Direct prediction endpoint: validates payload, runs inference,
    returns risk scores and explainable indicators without storing in DB.
    """
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Request body must be valid application/json.'}), 400

    payload = request.get_json()
    result = predict_fraud_risk(payload, model=active_model)

    if not result.get('success'):
        return jsonify(result), 400

    return jsonify(result), 200


@app.route('/api/transaction', methods=['POST'])
@login_required
def api_create_transaction():
    """
    Analyzes AND saves transaction into SQLite database for current user.
    """
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Expected JSON payload.'}), 400

    payload = request.get_json()
    is_valid, err_msg, clean_data = validate_transaction_input(payload)
    if not is_valid:
        return jsonify({'success': False, 'error': err_msg}), 400

    # 1. Run ML Prediction
    eval_result = predict_fraud_risk(clean_data, model=active_model)
    if not eval_result.get('success'):
        return jsonify(eval_result), 400

    # 2. Persist Transaction
    try:
        user_id = session.get('user_id')
        tx = Transaction(
            user_id=user_id,
            amount=clean_data['amount'],
            time=clean_data['time'],
            transaction_type=clean_data['transaction_type'],
            high_tx_reason=clean_data.get('high_tx_reason'),
            upi_id=clean_data.get('upi_id'),
            payment_mode=clean_data.get('payment_mode', 'UPI ID / VPA'),
            transaction_frequency=clean_data['transaction_frequency'],
            avg_transaction_amount=clean_data['avg_transaction_amount'],
            is_new_beneficiary=clean_data['is_new_beneficiary'],
            device_changed=clean_data['device_changed'],
            location_changed=clean_data['location_changed'],
            failed_attempts=clean_data['failed_attempts'],
            beneficiary_frequency=clean_data['beneficiary_frequency']
        )
        db.session.add(tx)
        db.session.flush()

        pred = Prediction(
            transaction_id=tx.id,
            fraud_probability=eval_result['fraud_probability'],
            risk_score=eval_result['risk_score'],
            risk_level=eval_result['risk_level'],
            status=eval_result['status'],
            action_status='PENDING' if eval_result['status'] != 'SAFE' else 'VERIFIED'
        )
        db.session.add(pred)
        db.session.commit()

        eval_result['transaction_id'] = tx.id
        return jsonify(eval_result), 201

    except Exception as e:
        db.session.rollback()
        logging.error("Failed to save transaction: %s", str(e), exc_info=True)
        return jsonify({'success': False, 'error': 'Database transaction storage error.'}), 500


@app.route('/api/history', methods=['GET'])
@login_required
def api_get_history():
    """
    Returns filtered and paginated transaction history records.
    Query params: search, status, type, page, per_page
    """
    user_id = session['user_id']
    is_admin = session.get('user_role') == 'ADMIN'

    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    type_filter = request.args.get('type', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(50, max(5, int(request.args.get('per_page', 10))))

    query = db.session.query(Transaction, Prediction).join(Prediction, Transaction.id == Prediction.transaction_id)
    if not is_admin:
        query = query.filter(Transaction.user_id == user_id)

    if status_filter:
        query = query.filter(Prediction.status == status_filter)
    if type_filter:
        query = query.filter(Transaction.transaction_type == type_filter)
    if search:
        query = query.filter(
            (Transaction.id.like(f"%{search}%")) |
            (Transaction.transaction_type.ilike(f"%{search}%")) |
            (Prediction.status.ilike(f"%{search}%"))
        )

    total_records = query.count()
    items = (
        query
        .order_by(desc(Transaction.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    data_list = []
    for tx, pred in items:
        data_list.append({
            'id': tx.id,
            'amount': tx.amount,
            'time': f"{tx.time:02d}:00",
            'transaction_type': tx.transaction_type,
            'risk_score': pred.risk_score,
            'risk_level': pred.risk_level,
            'status': pred.status,
            'action_status': pred.action_status,
            'created_at': tx.created_at.strftime('%Y-%m-%d %H:%M') if tx.created_at else ''
        })

    return jsonify({
        'success': True,
        'page': page,
        'per_page': per_page,
        'total': total_records,
        'total_pages': (total_records + per_page - 1) // per_page,
        'data': data_list
    }), 200


@app.route('/api/statistics', methods=['GET'])
@login_required
def api_get_statistics():
    """
    Returns aggregated data for Chart.js dashboards.
    """
    user_id = session['user_id']
    is_admin = session.get('user_role') == 'ADMIN'

    query = db.session.query(Transaction, Prediction).join(Prediction, Transaction.id == Prediction.transaction_id)
    if not is_admin:
        query = query.filter(Transaction.user_id == user_id)

    all_pairs = query.all()
    if not all_pairs:
        return jsonify({
            'success': True,
            'has_data': False,
            'message': 'Not enough data available.'
        }), 200

    # 1. Status Breakdown (Safe, Suspicious, Fraud)
    status_counts = {'SAFE': 0, 'SUSPICIOUS': 0, 'FRAUD LIKELY': 0}
    # 2. By Transaction Type
    type_counts = {}
    type_fraud_counts = {}
    # 3. By Hour of Day (0 to 23)
    hourly_counts = [0] * 24
    hourly_fraud = [0] * 24
    # 4. Risk Score distribution bins
    score_bins = {'0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0}

    for tx, pred in all_pairs:
        # Status
        st = pred.status
        if st in status_counts:
            status_counts[st] += 1

        # Type
        ttype = tx.transaction_type
        type_counts[ttype] = type_counts.get(ttype, 0) + 1
        if st == 'FRAUD LIKELY':
            type_fraud_counts[ttype] = type_fraud_counts.get(ttype, 0) + 1

        # Hourly
        if 0 <= tx.time <= 23:
            hourly_counts[tx.time] += 1
            if st == 'FRAUD LIKELY':
                hourly_fraud[tx.time] += 1

        # Bins
        s = pred.risk_score
        if s <= 20: score_bins['0-20'] += 1
        elif s <= 40: score_bins['21-40'] += 1
        elif s <= 60: score_bins['41-60'] += 1
        elif s <= 80: score_bins['61-80'] += 1
        else: score_bins['81-100'] += 1

    return jsonify({
        'success': True,
        'has_data': True,
        'total_transactions': len(all_pairs),
        'status_breakdown': status_counts,
        'type_distribution': type_counts,
        'type_fraud_distribution': type_fraud_counts,
        'hourly_totals': hourly_counts,
        'hourly_fraud': hourly_fraud,
        'score_bins': score_bins
    }), 200


@app.route('/api/model-info', methods=['GET'])
def api_get_model_info():
    """Returns model metrics and algorithm comparisons."""
    if os.path.exists(Config.METRICS_JSON_PATH):
        try:
            with open(Config.METRICS_JSON_PATH, 'r') as f:
                data = json.load(f)
            return jsonify({'success': True, 'data': data}), 200
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': False, 'error': 'Metrics not yet generated. Retrain model.'}), 404


@app.route('/api/transaction/<int:tx_id>/verify', methods=['POST'])
@login_required
def api_verify_transaction(tx_id):
    """
    Simulation Verification: Marks high-risk transaction as authorized by user.
    """
    user_id = session['user_id']
    is_admin = session.get('user_role') == 'ADMIN'

    tx = Transaction.query.get_or_404(tx_id)
    if not is_admin and tx.user_id != user_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    pred = Prediction.query.filter_by(transaction_id=tx.id).first()
    if pred:
        pred.action_status = 'VERIFIED'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Transaction verified successfully.'}), 200

    return jsonify({'success': False, 'error': 'Prediction record missing'}), 404


@app.route('/api/transaction/<int:tx_id>/cancel', methods=['POST'])
@login_required
def api_cancel_transaction(tx_id):
    """
    Simulation Cancellation: Halts flagged transaction.
    """
    user_id = session['user_id']
    is_admin = session.get('user_role') == 'ADMIN'

    tx = Transaction.query.get_or_404(tx_id)
    if not is_admin and tx.user_id != user_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    pred = Prediction.query.filter_by(transaction_id=tx.id).first()
    if pred:
        pred.action_status = 'CANCELLED'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Transaction cancelled.'}), 200

    return jsonify({'success': False, 'error': 'Prediction record missing'}), 404


# ---------------------------------------------------------------------------
# ERROR HANDLERS
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def error_404(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Endpoint not found.'}), 404
    return render_template('index.html'), 404


@app.errorhandler(500)
def error_500(e):
    logging.error("Server 500 error encountered: %s", str(e), exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error occurred.'}), 500
    return "<h3>Internal Server Error</h3><p>An unexpected server error occurred.</p>", 500


# Bootstrap Application Context on Startup
bootstrap_database_and_models()


if __name__ == '__main__':
    print("==================================================================")
    print(" UPI FRAUD DETECTION ENTERPRISE WEB APP")
    print(" Admin Access: admin@upi.bank / Admin@123")
    print(" User Access:  user@upi.bank  / User@123")
    print(" URL:          http://127.0.0.1:5000")
    print("==================================================================")
    app.run(host='127.0.0.1', port=5000, debug=False)
