import sqlite3
import pprint

conn = sqlite3.connect('test_cotte.db')
print("Tables:")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print(tables)

print("\nUsuarios:")
try:
    usuarios = conn.execute("SELECT id, nome, email, telefone, telefone_operador, ativo FROM usuario;").fetchall()
    pprint.pprint(usuarios)
except Exception as e:
    print(e)
