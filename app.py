from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from init_db import init_db, DB_PATH
import sqlite3
import os
import hashlib
from datetime import datetime, date
import random

app = Flask(__name__)
app.secret_key = 'feed_manufacturing_secret_key_2024'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def login_required(role_ids=None):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role_ids and session.get('role_id') not in role_ids:
                return render_template('message.html', msg='ليس لديك صلاحية للوصول إلى هذه الصفحة', type='danger')
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

def get_user_info():
    if 'user_id' not in session: return None
    return {
        'user_id': session['user_id'],
        'username': session['username'],
        'full_name': session['full_name'],
        'role_id': session['role_id'],
        'role_name': session['role_name'],
        'company_id': session['company_id'],
        'company_name': session['company_name']
    }

def generate_request_number():
    today = date.today().strftime('%Y%m%d')
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM feed_requests WHERE request_number LIKE ?", (f'FR-{today}-%',)).fetchone()[0]
    conn.close()
    return f'FR-{today}-{count+1:03d}'

def get_setting(key, default=''):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def system_password_correct(password):
    stored = get_setting('system_password_hash')
    if not stored:
        return True
    return hashlib.sha256(password.encode()).hexdigest() == stored

def require_system_password():
    enabled = get_setting('system_protection_enabled', '0')
    if enabled == '1' and not session.get('system_verified'):
        return True
    return False

def get_status_badge(status):
    badges = {
        'pending': '<span class="badge badge-pending">قيد الانتظار</span>',
        'approved': '<span class="badge badge-approved">مقبول</span>',
        'rejected': '<span class="badge badge-rejected">مرفوض</span>',
        'completed': '<span class="badge badge-completed">مكتمل</span>',
        'partially_completed': '<span class="badge badge-partial">مكتمل جزئياً</span>'
    }
    return badges.get(status, status)

# ------ Routes ------

@app.route('/')
def index():
    if 'user_id' in session:
        user = get_user_info()
        if user['role_id'] == 1: return redirect(url_for('new_request'))
        if user['role_id'] == 2: return redirect(url_for('pending_requests'))
        if user['role_id'] in [3,4,5]: return redirect(url_for('production_orders'))
        if user['role_id'] == 6: return redirect(url_for('completion_orders'))
        if user['role_id'] == 7: return redirect(url_for('top_dashboard'))
        if user['role_id'] == 8: return redirect(url_for('admin_users'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute('''
            SELECT u.*, r.role_name, r.role_name_ar, c.company_name_ar as company_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            JOIN companies c ON u.company_id = c.company_id
            WHERE u.username = ? AND u.password = ? AND u.is_active = 1
        ''', (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role_id'] = user['role_id']
            session['role_name'] = user['role_name_ar']
            session['company_id'] = user['company_id']
            session['company_name'] = user['company_name']
            return redirect(url_for('index'))
        return render_template('login.html', error='اسم المستخدم أو كلمة المرور غير صحيحة')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/new-request', methods=['GET','POST'])
@login_required([1])
def new_request():
    if request.method == 'POST':
        try:
            conn = get_db()
            feed_type_id = int(request.form['feed_type'])
            package_weight = float(request.form['package_weight'])
            quantity_tons = float(request.form['quantity_tons'])
            notes = request.form.get('notes', '')
            req_num = generate_request_number()
            conn.execute('''
                INSERT INTO feed_requests (request_number, feed_type_id, package_weight_kg, quantity_tons, requested_by, request_notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (req_num, feed_type_id, package_weight, quantity_tons, session['user_id'], notes))
            conn.commit()
            conn.close()
            return render_template('message.html', msg=f'تم إرسال الطلب {req_num} بنجاح', type='success')
        except Exception as e:
            return render_template('message.html', msg=f'حدث خطأ: {str(e)}', type='danger')
    conn = get_db()
    feed_types = conn.execute("SELECT * FROM feed_types", ()).fetchall()
    conn.close()
    return render_template('new_request.html', feed_types=feed_types)

@app.route('/my-requests')
@login_required([1])
def my_requests():
    conn = get_db()
    requests = conn.execute('''
        SELECT r.*, f.feed_name_ar, f.feed_code
        FROM feed_requests r
        JOIN feed_types f ON r.feed_type_id = f.feed_type_id
        WHERE r.requested_by = ?
        ORDER BY r.request_date DESC, r.request_time DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('my_requests.html', requests=requests, get_status_badge=get_status_badge)

@app.route('/pending-requests')
@login_required([2])
def pending_requests():
    conn = get_db()
    pending = conn.execute('''
        SELECT r.*, f.feed_name_ar, f.feed_code, u.full_name as requester_name
        FROM feed_requests r
        JOIN feed_types f ON r.feed_type_id = f.feed_type_id
        JOIN users u ON r.requested_by = u.user_id
        WHERE r.status = 'pending'
        ORDER BY r.request_date ASC, r.request_time ASC
    ''', ()).fetchall()
    conn.close()
    return render_template('pending_requests.html', requests=pending, get_status_badge=get_status_badge)

@app.route('/order/<int:order_id>')
@login_required([1,2,3,4,5,6,7])
def view_order(order_id):
    conn = get_db()
    order = conn.execute('''
        SELECT r.*, f.feed_name_ar, f.feed_code, f.protein_percent,
               u1.full_name as requester_name,
               u2.full_name as approver_name,
               u3.full_name as completer_name
        FROM feed_requests r
        JOIN feed_types f ON r.feed_type_id = f.feed_type_id
        LEFT JOIN users u1 ON r.requested_by = u1.user_id
        LEFT JOIN users u2 ON r.approved_by = u2.user_id
        LEFT JOIN users u3 ON r.completed_by = u3.user_id
        WHERE r.request_id = ?
    ''', (order_id,)).fetchone()
    if not order:
        return render_template('message.html', msg='الطلب غير موجود', type='danger')
    history = conn.execute('''
        SELECT h.*, u.full_name
        FROM approval_history h
        JOIN users u ON h.action_by = u.user_id
        WHERE h.request_id = ?
        ORDER BY h.action_at DESC
    ''', (order_id,)).fetchall()
    rejections = conn.execute('''
        SELECT re.*, u.full_name
        FROM rejection_reasons re
        JOIN users u ON re.rejected_by = u.user_id
        WHERE re.request_id = ?
        ORDER BY re.rejection_date DESC
    ''', (order_id,)).fetchall()
    pending_items = conn.execute('''
        SELECT p.*, f.feed_name_ar
        FROM pending_items p
        JOIN feed_types f ON p.feed_type_id = f.feed_type_id
        WHERE p.request_id = ?
    ''', (order_id,)).fetchall()
    conn.close()
    return render_template('view_order.html', order=order, get_status_badge=get_status_badge,
                          history=history, rejections=rejections, pending_items=pending_items)

@app.route('/approve/<int:order_id>', methods=['POST'])
@login_required([2])
def approve_order(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM feed_requests WHERE request_id = ? AND status = 'pending'", (order_id,)).fetchone()
    if not order:
        conn.close()
        return render_template('message.html', msg='الطلب غير موجود أو تمت معالجته مسبقاً', type='danger')
    notes = request.form.get('notes', '')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('''
        UPDATE feed_requests SET status='approved', approved_by=?, approved_at=?, approval_notes=?, sent_to_production=1, sent_at=?
        WHERE request_id=?
    ''', (session['user_id'], now, notes, now, order_id))
    conn.execute('''
        INSERT INTO approval_history (request_id, action, action_by, notes)
        VALUES (?, 'approved', ?, ?)
    ''', (order_id, session['user_id'], notes))
    conn.commit()
    conn.close()
    return render_template('message.html', msg='تم قبول الطلب وإرساله للإنتاج', type='success')

@app.route('/reject/<int:order_id>', methods=['POST'])
@login_required([2])
def reject_order(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM feed_requests WHERE request_id = ? AND status = 'pending'", (order_id,)).fetchone()
    if not order:
        conn.close()
        return render_template('message.html', msg='الطلب غير موجود أو تمت معالجته مسبقاً', type='danger')
    reason = request.form.get('reason', '')
    if not reason:
        conn.close()
        return render_template('message.html', msg='يجب كتابة سبب الرفض', type='danger')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("UPDATE feed_requests SET status='rejected', approved_by=?, approved_at=?, approval_notes=? WHERE request_id=?",
                 (session['user_id'], now, reason, order_id))
    conn.execute("INSERT INTO rejection_reasons (request_id, rejected_by, rejection_reason) VALUES (?, ?, ?)",
                 (order_id, session['user_id'], reason))
    conn.execute("INSERT INTO approval_history (request_id, action, action_by, notes) VALUES (?, 'rejected', ?, ?)",
                 (order_id, session['user_id'], reason))
    conn.commit()
    conn.close()
    return render_template('message.html', msg='تم رفض الطلب', type='info')

@app.route('/production-orders')
@login_required([3,4,5])
def production_orders():
    conn = get_db()
    orders = conn.execute('''
        SELECT r.*, f.feed_name_ar, f.feed_code, u.full_name as requester_name
        FROM feed_requests r
        JOIN feed_types f ON r.feed_type_id = f.feed_type_id
        JOIN users u ON r.requested_by = u.user_id
        WHERE r.status IN ('approved','completed','partially_completed')
        ORDER BY r.request_date DESC
    ''', ()).fetchall()
    conn.close()
    role = session.get('role_id')
    if role == 3: title = 'الإنتاج'
    elif role == 4: title = 'الجودة'
    else: title = 'المخازن'
    return render_template('production_orders.html', orders=orders, get_status_badge=get_status_badge, title=title)

@app.route('/completion-orders')
@login_required([6])
def completion_orders():
    conn = get_db()
    orders = conn.execute('''
        SELECT r.*, f.feed_name_ar, f.feed_code, u.full_name as requester_name
        FROM feed_requests r
        JOIN feed_types f ON r.feed_type_id = f.feed_type_id
        JOIN users u ON r.requested_by = u.user_id
        WHERE r.status IN ('approved','completed','partially_completed')
        ORDER BY r.request_date DESC
    ''', ()).fetchall()
    conn.close()
    return render_template('completion_orders.html', orders=orders, get_status_badge=get_status_badge)

@app.route('/complete-order/<int:order_id>', methods=['POST'])
@login_required([6])
def complete_order(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM feed_requests WHERE request_id = ? AND status = 'approved'", (order_id,)).fetchone()
    if not order:
        conn.close()
        return render_template('message.html', msg='الطلب غير موجود أو تم إنهاؤه مسبقاً', type='danger')
    completion_status = request.form['completion_status']
    notes = request.form.get('notes', '')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('''
        UPDATE feed_requests SET status=?, completed_by=?, completed_at=?, completion_status=?, completion_notes=?
        WHERE request_id=?
    ''', (completion_status, session['user_id'], now, completion_status, notes, order_id))
    conn.execute('''
        INSERT INTO approval_history (request_id, action, action_by, notes)
        VALUES (?, ?, ?, ?)
    ''', (order_id, completion_status, session['user_id'], notes))
    # add pending items if partial
    if completion_status == 'partially_completed' and request.form.get('has_pending'):
        conn.execute('''
            INSERT INTO pending_items (request_id, feed_type_id, package_weight_kg, pending_quantity, delay_reason, deviation_reason, expected_completion, created_by)
            VALUES (?,?,?,?,?,?,?,?)
        ''', (order_id, order['feed_type_id'], order['package_weight_kg'],
              float(request.form['pending_qty']), request.form['delay_reason'],
              request.form.get('deviation_reason', ''), request.form.get('expected_date', ''), session['user_id']))
    conn.commit()
    conn.close()
    return render_template('message.html', msg='تم تحديث حالة الطلب بنجاح', type='success')

@app.route('/top-dashboard')
@login_required([7])
def top_dashboard():
    conn = get_db()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    feed_type_id = request.args.get('feed_type', '')
    status_filter = request.args.get('status', '')
    month = request.args.get('month', '')

    filters = []
    params = []
    if date_from:
        filters.append("r.request_date >= ?")
        params.append(date_from)
    if date_to:
        filters.append("r.request_date <= ?")
        params.append(date_to)
    if feed_type_id:
        filters.append("r.feed_type_id = ?")
        params.append(int(feed_type_id))
    if status_filter:
        filters.append("r.status = ?")
        params.append(status_filter)
    if month:
        filters.append("strftime('%Y-%m', r.request_date) = ?")
        params.append(month)

    where = " WHERE " + " AND ".join(filters) if filters else ""

    def count_by_status(status):
        if filters:
            return conn.execute(f"SELECT COUNT(*) FROM feed_requests r{where} AND r.status = ?", params + [status]).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM feed_requests WHERE status = ?", (status,)).fetchone()[0]

    total = count_by_status('pending') + count_by_status('approved') + count_by_status('rejected') + count_by_status('completed') + count_by_status('partially_completed')
    pending = count_by_status('pending')
    approved = count_by_status('approved')
    rejected = count_by_status('rejected')
    completed = count_by_status('completed')
    partial = count_by_status('partially_completed')

    orders_query = f'''
        SELECT r.*, f.feed_name_ar, u.full_name as requester_name
        FROM feed_requests r
        JOIN feed_types f ON r.feed_type_id = f.feed_type_id
        JOIN users u ON r.requested_by = u.user_id
        {where + " AND" if where else " WHERE"} 1=1
        ORDER BY r.request_date DESC, r.request_time DESC
    '''
    if filters:
        filtered_orders = conn.execute(orders_query, params).fetchall()
    else:
        filtered_orders = conn.execute(orders_query.replace("WHERE 1=1", "")).fetchall()

    feed_types = conn.execute("SELECT * FROM feed_types ORDER BY feed_name_ar").fetchall()
    conn.close()
    return render_template('top_dashboard.html',
        total=total, pending=pending, approved=approved,
        rejected=rejected, completed=completed, partial=partial,
        filtered_orders=filtered_orders, get_status_badge=get_status_badge,
        feed_types=feed_types,
        date_from=date_from, date_to=date_to,
        selected_feed=feed_type_id, selected_status=status_filter,
        selected_month=month)

@app.route('/api/chart-data')
@login_required([7])
def api_chart_data():
    conn = get_db()
    monthly = conn.execute('''
        SELECT strftime('%Y-%m', request_date) as month,
               COUNT(*) as total,
               SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending,
               SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as approved,
               SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) as rejected,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
               SUM(CASE WHEN status='partially_completed' THEN 1 ELSE 0 END) as partial
        FROM feed_requests
        GROUP BY month ORDER BY month
    ''').fetchall()

    by_feed = conn.execute('''
        SELECT f.feed_name_ar, COUNT(*) as total
        FROM feed_requests r
        JOIN feed_types f ON r.feed_type_id = f.feed_type_id
        GROUP BY r.feed_type_id ORDER BY total DESC
    ''').fetchall()

    conn.close()

    labels = [r['month'] for r in monthly]
    pending_data = [r['pending'] for r in monthly]
    approved_data = [r['approved'] for r in monthly]
    rejected_data = [r['rejected'] for r in monthly]
    completed_data = [r['completed'] for r in monthly]
    partial_data = [r['partial'] for r in monthly]
    feed_labels = [r['feed_name_ar'] for r in by_feed]
    feed_data = [r['total'] for r in by_feed]

    return jsonify({
        'monthly': {'labels': labels, 'pending': pending_data, 'approved': approved_data,
                    'rejected': rejected_data, 'completed': completed_data, 'partial': partial_data},
        'by_feed': {'labels': feed_labels, 'data': feed_data}
    })

@app.route('/all-orders')
@login_required([1,2,3,4,5,6,7])
def all_orders():
    conn = get_db()
    orders = conn.execute('''
        SELECT r.*, f.feed_name_ar, f.feed_code, u.full_name as requester_name
        FROM feed_requests r
        JOIN feed_types f ON r.feed_type_id = f.feed_type_id
        JOIN users u ON r.requested_by = u.user_id
        ORDER BY r.request_date DESC, r.request_time DESC
    ''', ()).fetchall()
    conn.close()
    return render_template('production_orders.html', orders=orders, get_status_badge=get_status_badge, title='جميع الطلبات')

@app.route('/admin/users', methods=['GET','POST'])
@login_required([7, 8])
def admin_users():
    if require_system_password():
        return redirect(url_for('system_lock', redirect=url_for('admin_users')))
    conn = get_db()
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_password = request.form.get('new_password')
        if user_id and new_password:
            conn.execute("UPDATE users SET password = ? WHERE user_id = ?", (new_password, user_id))
            conn.commit()
            conn.close()
            return render_template('message.html', msg='تم تغيير كلمة المرور بنجاح', type='success')
        conn.close()
        return render_template('message.html', msg='بيانات غير صالحة', type='danger')
    users = conn.execute('''
        SELECT u.*, r.role_name_ar, c.company_name_ar
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        JOIN companies c ON u.company_id = c.company_id
        ORDER BY u.user_id
    ''').fetchall()
    roles = conn.execute("SELECT * FROM roles ORDER BY role_id").fetchall()
    companies = conn.execute("SELECT * FROM companies ORDER BY company_id").fetchall()
    conn.close()
    return render_template('admin_users.html', users=users, roles=roles, companies=companies)

@app.route('/admin/change-role', methods=['POST'])
@login_required([7, 8])
def change_role():
    if require_system_password():
        return render_template('system_lock.html', error=None, redirect=url_for('admin_users'))
    user_id = request.form.get('user_id')
    new_role = request.form.get('role_id')
    if user_id and new_role:
        conn = get_db()
        conn.execute("UPDATE users SET role_id = ? WHERE user_id = ?", (new_role, user_id))
        conn.commit()
        conn.close()
        return render_template('message.html', msg='تم تغيير الصلاحية بنجاح', type='success')
    return render_template('message.html', msg='بيانات غير صالحة', type='danger')

@app.route('/admin/add-user', methods=['POST'])
@login_required([7, 8])
def add_user():
    if require_system_password():
        return render_template('system_lock.html', error=None, redirect=url_for('admin_users'))
    username = request.form.get('username')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    role_id = request.form.get('role_id')
    company_id = request.form.get('company_id')
    if not all([username, password, full_name, role_id, company_id]):
        return render_template('message.html', msg='جميع الحقول مطلوبة', type='danger')
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO users (username, password, full_name, role_id, company_id, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (username, password, full_name, role_id, company_id))
        conn.commit()
        conn.close()
        return render_template('message.html', msg=f'تم إضافة المستخدم {full_name} بنجاح', type='success')
    except Exception as e:
        conn.close()
        return render_template('message.html', msg=f'خطأ: اسم المستخدم موجود مسبقاً', type='danger')

@app.route('/admin/clear-data', methods=['POST'])
@login_required([7, 8])
def clear_data():
    if require_system_password():
        return render_template('system_lock.html', error=None, redirect=url_for('admin_users'))
    conn = get_db()
    tables = ['pending_items', 'warehouse_info', 'quality_info', 'production_info',
              'approval_history', 'rejection_reasons', 'feed_requests']
    for t in tables:
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    conn.close()
    return render_template('message.html', msg='تم مسح جميع بيانات الطلبات بنجاح', type='success')

@app.route('/api/orders')
@login_required([1,2,3,4,5,6,7])
def api_orders():
    conn = get_db()
    orders = conn.execute('''
        SELECT r.request_id, r.request_number, r.request_date, r.status,
               f.feed_name_ar, r.quantity_tons, r.package_weight_kg
        FROM feed_requests r
        JOIN feed_types f ON r.feed_type_id = f.feed_type_id
        ORDER BY r.request_id DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])

@app.route('/system/lock')
@login_required([7, 8])
def system_lock():
    session['system_verified'] = False
    return render_template('system_lock.html', error=None, redirect=request.args.get('redirect', ''))

@app.route('/system/unlock', methods=['POST'])
@login_required([7, 8])
def system_unlock():
    password = request.form.get('password', '')
    redirect_to = request.form.get('redirect', '')
    if system_password_correct(password):
        session['system_verified'] = True
        if redirect_to:
            return redirect(redirect_to)
        return render_template('message.html', msg='✅ تم فتح النظام بنجاح', type='success')
    return render_template('system_lock.html', error='❌ الرقم السري غير صحيح', redirect=redirect_to)

@app.route('/system/set-password', methods=['GET', 'POST'])
@login_required([7, 8])
def set_system_password():
    if require_system_password():
        system_lock()
        return render_template('system_lock.html', error=None, redirect=url_for('set_system_password'))
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new_pass = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        if get_setting('system_password_hash') and not system_password_correct(current):
            return render_template('message.html', msg='❌ الرقم السري الحالي غير صحيح', type='danger')
        if len(new_pass) < 4:
            return render_template('message.html', msg='❌ الرقم السري يجب أن يكون 4 أحرف على الأقل', type='danger')
        if new_pass != confirm:
            return render_template('message.html', msg='❌ الرقم السري غير متطابق في التأكيد', type='danger')
        h = hashlib.sha256(new_pass.encode()).hexdigest()
        set_setting('system_password_hash', h)
        set_setting('system_protection_enabled', '1')
        session['system_verified'] = True
        return render_template('message.html', msg='✅ تم تعيين رقم الحماية السري للنظام بنجاح', type='success')
    has_password = bool(get_setting('system_password_hash'))
    return render_template('set_system_password.html', has_password=has_password)

@app.route('/system/disable', methods=['POST'])
@login_required([7, 8])
def disable_system_password():
    if require_system_password():
        return render_template('system_lock.html', error=None, redirect=url_for('admin_users'))
    password = request.form.get('password', '')
    if not system_password_correct(password):
        return render_template('message.html', msg='❌ الرقم السري غير صحيح', type='danger')
    set_setting('system_password_hash', '')
    set_setting('system_protection_enabled', '0')
    session['system_verified'] = False
    return render_template('message.html', msg='✅ تم إلغاء الحماية', type='success')

@app.route('/export/<export_type>')
@login_required([1,2,3,4,5,6,7])
def export_data(export_type):
    conn = get_db()

    queries = {
        'all_orders': "SELECT r.request_number as 'رقم الطلب', r.request_date as 'التاريخ', u.full_name as 'مقدم الطلب', f.feed_name_ar as 'نوع العلف', r.quantity_tons as 'الكمية (طن)', r.package_weight_kg as 'وزن الكيس (كجم)', r.status as 'الحالة' FROM feed_requests r JOIN feed_types f ON r.feed_type_id = f.feed_type_id JOIN users u ON r.requested_by = u.user_id ORDER BY r.request_date DESC",
        'my_requests': None,
        'pending': "SELECT r.request_number as 'رقم الطلب', r.request_date as 'التاريخ', u.full_name as 'مقدم الطلب', f.feed_name_ar as 'نوع العلف', r.quantity_tons as 'الكمية (طن)', r.request_notes as 'ملاحظات' FROM feed_requests r JOIN feed_types f ON r.feed_type_id = f.feed_type_id JOIN users u ON r.requested_by = u.user_id WHERE r.status='pending' ORDER BY r.request_date ASC",
        'approved': "SELECT r.request_number as 'رقم الطلب', r.request_date as 'التاريخ', u.full_name as 'مقدم الطلب', f.feed_name_ar as 'نوع العلف', r.quantity_tons as 'الكمية (طن)', r.approved_at as 'تاريخ القبول' FROM feed_requests r JOIN feed_types f ON r.feed_type_id = f.feed_type_id JOIN users u ON r.requested_by = u.user_id WHERE r.status IN ('approved','completed','partially_completed') ORDER BY r.request_date DESC",
        'order': None
    }

    if export_type == 'my_requests':
        if session['role_id'] != 1:
            conn.close()
            return render_template('message.html', msg='غير مصرح', type='danger')
        rows = conn.execute("SELECT r.request_number as 'رقم الطلب', r.request_date as 'التاريخ', f.feed_name_ar as 'نوع العلف', r.quantity_tons as 'الكمية (طن)', r.package_weight_kg as 'وزن الكيس (كجم)', r.status as 'الحالة' FROM feed_requests r JOIN feed_types f ON r.feed_type_id = f.feed_type_id WHERE r.requested_by = ? ORDER BY r.request_date DESC", (session['user_id'],)).fetchall()
    elif export_type == 'order':
        order_id = request.args.get('order_id', 0)
        rows = conn.execute("SELECT r.request_number as 'رقم الطلب', r.request_date as 'التاريخ', f.feed_name_ar as 'نوع العلف', r.quantity_tons as 'الكمية (طن)', r.package_weight_kg as 'وزن الكيس (كجم)', r.status as 'الحالة', u1.full_name as 'مقدم الطلب', u2.full_name as 'المقبل', r.approved_at as 'تاريخ القبول', r.request_notes as 'ملاحظات الطلب', r.approval_notes as 'ملاحظات القبول' FROM feed_requests r JOIN feed_types f ON r.feed_type_id = f.feed_type_id LEFT JOIN users u1 ON r.requested_by = u1.user_id LEFT JOIN users u2 ON r.approved_by = u2.user_id WHERE r.request_id = ?", (order_id,)).fetchall()
    else:
        q = queries.get(export_type)
        if not q:
            conn.close()
            return render_template('message.html', msg='نوع تصدير غير صحيح', type='danger')
        rows = conn.execute(q).fetchall()
    conn.close()

    dict_rows = [dict(r) for r in rows]

    from flask import send_file
    from export_utils import export_excel
    output = export_excel(dict_rows, export_type)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'{export_type}.xlsx')

init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
