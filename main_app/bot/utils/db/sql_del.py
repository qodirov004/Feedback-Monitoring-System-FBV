import sqlite3

def report_fan_del(kod):
    try:
        with sqlite3.connect('db.sqlite3') as con:
            cur = con.cursor()
            rec = '''
            DELETE FROM REPORT_FAN WHERE TEST_KOD = ?
            '''
            cur.execute(rec, (kod,))
            con.commit()
            print('Start!')
    except sqlite3.Error as err:
        print(f'your mistake:{err}')

def delete_all():
    try:
        with sqlite3.connect('db.sqlite3') as con:
            cur = con.cursor()
            rec = '''
            DELETE FROM users
            '''
            cur.execute(rec)
            con.commit()
            print('Start!')
    except sqlite3.Error as err:
        print(f'your mistake:{err}')