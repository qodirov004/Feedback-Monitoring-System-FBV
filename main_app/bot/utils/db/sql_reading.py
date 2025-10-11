import sqlite3

def read_f():
    try:
        with sqlite3.connect('db.sqlite3') as con:
            cur = con.cursor()
            query = '''
                SELECT * FROM ?
            '''
            cur.execute(query)
            read = cur.fetchall()
            return read
    except (Exception, sqlite3.Error) as er:
        print('table error', er)