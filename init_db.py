import sqlite3
import os
import sys

def get_db_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'feed_manufacturing.db')
    return os.path.join(os.path.dirname(__file__), 'feed_manufacturing.db')

DB_PATH = get_db_path()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS roles (
            role_id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_name VARCHAR(50) NOT NULL UNIQUE,
            role_name_ar VARCHAR(50) NOT NULL,
            description TEXT
        );
        INSERT OR IGNORE INTO roles VALUES (1,'quwisna_requester','طالب من قويسنا','يقوم بإرسال طلبات التصنيع');
        INSERT OR IGNORE INTO roles VALUES (2,'nema_approver','مسئول قبول - نماء','يقوم بقبول الطلبات');
        INSERT OR IGNORE INTO roles VALUES (3,'production_manager','مدير الإنتاج','مشاهدة الطلبات المقبولة');
        INSERT OR IGNORE INTO roles VALUES (4,'quality_manager','مدير الجودة','مشاهدة الطلبات المقبولة');
        INSERT OR IGNORE INTO roles VALUES (5,'warehouse_manager','مدير المخازن','مشاهدة الطلبات المقبولة');
        INSERT OR IGNORE INTO roles VALUES (6,'nema_completion','مسئول إنهاء - نماء','إنهاء الطلبات وتسجيل التأخيرات');
        INSERT OR IGNORE INTO roles VALUES (7,'top_management','الإدارة العليا','مشاهدة التقارير والإحصائيات');
        INSERT OR IGNORE INTO roles VALUES (8,'system_admin','مدير النظام','إدارة المستخدمين والصلاحيات');

        CREATE TABLE IF NOT EXISTS companies (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name VARCHAR(100) NOT NULL,
            company_name_ar VARCHAR(100) NOT NULL
        );
        INSERT OR IGNORE INTO companies VALUES (1,'Quwisna','شركة قويسنا');
        INSERT OR IGNORE INTO companies VALUES (2,'Nemaa','شركة نماء');

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            role_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (role_id) REFERENCES roles(role_id),
            FOREIGN KEY (company_id) REFERENCES companies(company_id)
        );
        INSERT OR IGNORE INTO users VALUES (1,'qwesna','123456','طالب قويسنا 1',1,1,1);
        INSERT OR IGNORE INTO users VALUES (2,'qwesna2','123456','طالب قويسنا 2',1,1,1);
        INSERT OR IGNORE INTO users VALUES (3,'nema_acc','123456','مسئول قبول نماء 1',2,2,1);
        INSERT OR IGNORE INTO users VALUES (4,'nema_acc2','123456','مسئول قبول نماء 2',2,2,1);
        INSERT OR IGNORE INTO users VALUES (5,'production','123456','مدير الإنتاج',3,2,1);
        INSERT OR IGNORE INTO users VALUES (6,'quality','123456','مدير الجودة',4,2,1);
        INSERT OR IGNORE INTO users VALUES (7,'warehouse','123456','مدير المخازن',5,2,1);
        INSERT OR IGNORE INTO users VALUES (8,'nema_end','123456','مسئول إنهاء نماء',6,2,1);
        INSERT OR IGNORE INTO users VALUES (9,'top_mgmt','123456','الإدارة العليا',7,2,1);
        INSERT OR IGNORE INTO users VALUES (10,'admin','123456','مدير النظام',8,2,1);

        CREATE TABLE IF NOT EXISTS feed_types (
            feed_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_code VARCHAR(20) NOT NULL UNIQUE,
            feed_name_ar VARCHAR(100) NOT NULL,
            protein_percent DECIMAL(5,2)
        );
        INSERT OR IGNORE INTO feed_types VALUES (1,'LAY14','بياض 14%',14);
        INSERT OR IGNORE INTO feed_types VALUES (2,'LAY10','بياض 10%',10);
        INSERT OR IGNORE INTO feed_types VALUES (3,'LAY25','بياض 25%',25);
        INSERT OR IGNORE INTO feed_types VALUES (4,'SPB23','سوبر بادى 23%',23);
        INSERT OR IGNORE INTO feed_types VALUES (5,'SPN21','سوبر نامى 21%',21);
        INSERT OR IGNORE INTO feed_types VALUES (6,'SPF19','سوبر ناهى 19%',19);
        INSERT OR IGNORE INTO feed_types VALUES (7,'SPBN21','سوبر بادى نامى 21%',21);
        INSERT OR IGNORE INTO feed_types VALUES (8,'HOM10','منزلى 10 ك',10);
        INSERT OR IGNORE INTO feed_types VALUES (9,'LAY16','بياض 16%',16);
        INSERT OR IGNORE INTO feed_types VALUES (10,'LAY18','بياض 18%',18);

        CREATE TABLE IF NOT EXISTS feed_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_number VARCHAR(20) NOT NULL UNIQUE,
            request_date DATE NOT NULL DEFAULT (date('now')),
            request_time TIME NOT NULL DEFAULT (time('now','localtime')),
            feed_type_id INTEGER NOT NULL,
            package_weight_kg DECIMAL(8,2) NOT NULL,
            quantity_tons DECIMAL(10,3) NOT NULL,
            requested_by INTEGER NOT NULL,
            request_notes TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            approved_by INTEGER,
            approved_at DATETIME,
            approval_notes TEXT,
            sent_to_production INTEGER DEFAULT 0,
            sent_at DATETIME,
            completed_by INTEGER,
            completed_at DATETIME,
            completion_status VARCHAR(20),
            completion_notes TEXT,
            FOREIGN KEY (feed_type_id) REFERENCES feed_types(feed_type_id),
            FOREIGN KEY (requested_by) REFERENCES users(user_id),
            FOREIGN KEY (approved_by) REFERENCES users(user_id),
            FOREIGN KEY (completed_by) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS rejection_reasons (
            rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            rejected_by INTEGER NOT NULL,
            rejection_reason TEXT NOT NULL,
            rejection_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES feed_requests(request_id),
            FOREIGN KEY (rejected_by) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS approval_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            action VARCHAR(20) NOT NULL,
            action_by INTEGER NOT NULL,
            action_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (request_id) REFERENCES feed_requests(request_id),
            FOREIGN KEY (action_by) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS production_info (
            production_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL UNIQUE,
            received_by INTEGER NOT NULL,
            received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_viewed INTEGER DEFAULT 0,
            FOREIGN KEY (request_id) REFERENCES feed_requests(request_id),
            FOREIGN KEY (received_by) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS quality_info (
            quality_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL UNIQUE,
            received_by INTEGER NOT NULL,
            received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            quality_status VARCHAR(20) DEFAULT 'pending',
            is_viewed INTEGER DEFAULT 0,
            FOREIGN KEY (request_id) REFERENCES feed_requests(request_id),
            FOREIGN KEY (received_by) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS warehouse_info (
            warehouse_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL UNIQUE,
            received_by INTEGER NOT NULL,
            received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_viewed INTEGER DEFAULT 0,
            FOREIGN KEY (request_id) REFERENCES feed_requests(request_id),
            FOREIGN KEY (received_by) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS pending_items (
            pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            feed_type_id INTEGER NOT NULL,
            package_weight_kg DECIMAL(8,2) NOT NULL,
            pending_quantity DECIMAL(10,3) NOT NULL,
            delay_reason TEXT NOT NULL,
            deviation_reason TEXT,
            expected_completion DATE,
            status VARCHAR(20) DEFAULT 'pending',
            created_by INTEGER NOT NULL,
            FOREIGN KEY (request_id) REFERENCES feed_requests(request_id),
            FOREIGN KEY (feed_type_id) REFERENCES feed_types(feed_type_id),
            FOREIGN KEY (created_by) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL
        );
    ''')
    # إضافة الإعدادات الافتراضية
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('system_password_hash', '74249e892c15e9755ca4d565ed9072ff3c5201831477cbef7a2f7dff9e4f4dd5')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('system_protection_enabled', '1')")
    conn.commit()
    conn.close()
    print('Database initialized successfully.')

if __name__ == '__main__':
    init_db()
