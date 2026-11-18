import sqlite3
DB="craftoria.sqlite3"
def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,username TEXT,name TEXT,phone TEXT,
        photo_file_id TEXT,price TEXT,receipt_file_id TEXT,address TEXT,status TEXT,created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
def create_order(uid,username,name,phone,photo):
    with conn() as c:
        cur=c.execute("INSERT INTO orders(user_id,username,name,phone,photo_file_id,status) VALUES(?,?,?,?,?,'pending')",
                      (uid,username,name,phone,photo))
        return cur.lastrowid
def get_order(oid):
    with conn() as c:
        r=c.execute("SELECT * FROM orders WHERE id=?",(oid,)).fetchone()
        return dict(r) if r else None
def update_order(oid,**kw):
    allowed={"price","receipt_file_id","address","status"}
    fields={k:v for k,v in kw.items() if k in allowed}
    if not fields:return
    with conn() as c:
        c.execute("UPDATE orders SET "+",".join(k+"=?" for k in fields)+" WHERE id=?",
                  (*fields.values(),oid))
def recent_orders():
    with conn() as c:
        return [dict(x) for x in c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 20")]

def get_waiting_receipt_order(uid):
    with conn() as c:
        r=c.execute("SELECT * FROM orders WHERE user_id=? AND status='awaiting_receipt' ORDER BY id DESC LIMIT 1",(uid,)).fetchone()
        return dict(r) if r else None
