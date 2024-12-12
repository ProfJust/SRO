# SQL-Datenbank aus Python steuern
#-------------------------------------------------------
# XAMPP- DB installieren
# https://www.apachefriends.org/de/index.html
# Tutorial 
# https://www.w3schools.com/python/python_mysql_getstarted.asp
# 
# ggf.  python -m pip install mysql-connector-python 
# last edidet by OJ on 11.12.2024
#--------------------------------------------------------
import mysql.connector

# Code nur 1mal am Anfang ausführen
"""
mydb1 = mysql.connector.connect(
  host="localhost",
  user="SRO",
  password="youbot"
)

print(mydb1) 

mycursor1 = mydb1.cursor()

# --- Creating a Database --
# mycursor1.execute("CREATE DATABASE sro_db")

# --- Check if Database Exists ---
mycursor1.execute("SHOW DATABASES")

for x in mycursor1:
  print(x) 
"""
# --- Connect to Database  ---
mydb = mysql.connector.connect(
  host="localhost",
  user="SRO",
  password="youbot",
  database="sro_db"
) 

mycursor = mydb.cursor()
# --- Create Table  ---
# mycursor.execute("CREATE TABLE customers (name VARCHAR(255), address VARCHAR(255))")
# mycursor.execute("CREATE TABLE customers (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), address VARCHAR(255))") 
"""
# --- Insert Into Table ---
sql = "INSERT INTO customers (name, address) VALUES (%s, %s)"
val = ("John", "Highway 21")
mycursor.execute(sql, val)

mydb.commit()

print(mycursor.rowcount, "record inserted.")

# -- Insert Multiple Rows --
sql = "INSERT INTO customers (name, address) VALUES (%s, %s)"
val = [
  ('Peter', 'Lowstreet 4'),
  ('Amy', 'Apple st 652'),
  ('Hannah', 'Mountain 21'),
  ('Michael', 'Valley 345'),
  ('Sandy', 'Ocean blvd 2'),
  ('Betty', 'Green Grass 1'),
  ('Richard', 'Sky st 331'),
  ('Susan', 'One way 98'),
  ('Vicky', 'Yellow Garden 2'),
  ('Ben', 'Park Lane 38'),
  ('William', 'Central st 954'),
  ('Chuck', 'Main Road 989'),
  ('Viola', 'Sideway 1633')
]

mycursor.executemany(sql, val)

mydb.commit()

print(mycursor.rowcount, "was inserted.") 
"""
"""
# --- Fetch Data from Database ---
mycursor.execute("SELECT * FROM customers")
myresult = mycursor.fetchall()

for x in myresult:
  print(x)
"""
# --- Fetch 2 Columns from Database ---
mycursor.execute("SELECT name  FROM customers")

myresult = mycursor.fetchall()

for x in myresult:
  print(x) 


#--- Select record(s) where the address is "Park Lane 38": result: ---
sql = "SELECT * FROM customers WHERE address ='Park Lane 38'"
mycursor.execute(sql)
myresult = mycursor.fetchall()
for x in myresult:
  print(x)
