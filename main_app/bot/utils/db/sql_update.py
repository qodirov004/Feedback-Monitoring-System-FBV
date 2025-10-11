import sqlite3

def update_last_name(user_id, new_last_name):
    try:
        with sqlite3.connect('db.sqlite3') as con:
            cur = con.cursor()
            cur.execute("UPDATE name_table SET LAST_NAME = ? WHERE USER_ID = ?", (new_last_name, user_id))
            con.commit()
            print('Фамилия обновлена')
    except sqlite3.Error as err:
        print(f'Возникла ошибка при обновлении: {err}')