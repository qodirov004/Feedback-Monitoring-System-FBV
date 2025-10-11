import sqlite3

def add_report_fan(user_id, kod, fan, name, last_name, correct, wrong, percent, date, time):
    try:
        with sqlite3.connect('db.sqlite3') as con:
            cur = con.cursor()
            add_user = '''INSERT INTO REPORT_FAN(USER_ID, TEST_KOD, FAN, FIRST_NAME, LAST_NAME, CORRECT, WRONG, PERCENT, DATA, TIME) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            cur.execute(add_user, (user_id, kod, fan, name, last_name, correct, wrong, percent, date, time))
            con.commit()
            print('all good user add')
    except sqlite3.Error as er:
        print('table error', er)