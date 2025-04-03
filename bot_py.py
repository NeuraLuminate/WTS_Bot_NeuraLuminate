# -*- coding: utf-8 -*-
"""bot.py

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1k29mS16bo6JKiniPKl0TehWta4SbCtXt
"""

# Commented out IPython magic to ensure Python compatibility.
# %%writefile requirements.txt
# flask
# requests
# google-generativeai
# gunicorn

import sqlite3

# Conectar a la base de datos
def conectar_db():
    return sqlite3.connect("clientes.db")

# Crear las tablas de servicios y citas
def crear_tablas():
    conn = conectar_db()
    cursor = conn.cursor()

    # Crear tabla de clientes (si no existe)
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        numero TEXT UNIQUE NOT NULL,
                        nombre TEXT NOT NULL,
                        historial TEXT)''')

    # Crear tabla de servicios (si no existe)
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        descripcion TEXT NOT NULL)''')

    # Crear tabla de citas (si no existe)
    cursor.execute('''CREATE TABLE IF NOT EXISTS citas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        numero TEXT NOT NULL,
                        servicio_id INTEGER NOT NULL,
                        fecha TEXT NOT NULL,
                        hora TEXT NOT NULL,
                        estado TEXT DEFAULT 'pendiente',
                        FOREIGN KEY (numero) REFERENCES clientes (numero),
                        FOREIGN KEY (servicio_id) REFERENCES servicios (id))''')

    conn.commit()
    conn.close()
    print("✅ Tablas creadas correctamente.")

# Función para insertar varios servicios
def insertar_varios_servicios(servicios_lista):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.executemany("INSERT INTO servicios (nombre, descripcion) VALUES (?, ?)", servicios_lista)
    conn.commit()
    conn.close()
    print("✅ Servicios insertados correctamente.")

# Lista de servicios con nombre y descripción
servicios_a_insertar = [
    ("Atención al cliente automatizado", "Automatizamos la atención al cliente via Whatsapp de manera personalizada, servicios, productos, citas e incluso consultas con respuestas inteligentes. 1000€ +IVA"),
    ("Autoclasificación de facturas y datos de clientes", "Clasificamos de forma personalizada tanto los datos de clientes como las facturas de manera automatica. 1500€ +IVA"),
    ("Marketing automatizado vía mail", "Interpretación de base de datos de clientes, personalización y automatización de cada mail dependiendo del cliente. 2000€ +IVA"),
    ("Redes Neuronales Integrales", "Pide una cita y le informaremos del funcionamiento y la implementación de las RNI en tu empresa. En Desarrollo..."),
    ("Pack de varios servicios", "Pide una cita y consulta con nuestros profesionales cualquier conjunto de nuestros servicios y su posible implementación para tu negocio."),
]

# 🔹 EJECUTAR PRIMERO: Crear las tablas en la base de datos
crear_tablas()

# 🔹 EJECUTAR DESPUÉS: Insertar los servicios en la base de datos
insertar_varios_servicios(servicios_a_insertar)

requests.post(
    "https://waba.360dialog.io/v1/configs/webhook",
    headers={
        "D360-API-KEY": API_KEY_360,
        "Content-Type": "application/json"
    },
    json={"url": public_url.public_url + "/webhook"} # Access the public_url attribute
)

import os

os.environ["GEMINI_API_KEY"] = "AIzaSyDBHS8DuGYlO7gtvWHYp6XAIJAyGi2WFUk"
API_KEY_360 = "1h0BqZCBsONxZWfP4sAoOALLAK"

import sqlite3

conn = sqlite3.connect("clientes.db")
cursor = conn.cursor()

# Crear tabla para clientes
cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE,
        nombre TEXT,
        historial TEXT
    )
''')

# Crear tabla para caché con fecha de almacenamiento
cursor.execute('''
    CREATE TABLE IF NOT EXISTS cache (
        pregunta TEXT PRIMARY KEY,
        respuesta TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()

from flask import Flask, request, jsonify
import requests
import os
import google.generativeai as genai
import sqlite3
import datetime

# Configurar Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
modelo = genai.GenerativeModel("gemini-pro")

app = Flask(__name__)

# Conectar a la base de datos
def conectar_db():
    return sqlite3.connect("clientes.db")

# Obtener usuario de la base de datos
def obtener_usuario(numero):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, historial FROM clientes WHERE numero = ?", (numero,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

# Guardar nuevo usuario
def guardar_usuario(numero, nombre):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO clientes (numero, nombre, historial) VALUES (?, ?, '')",
                   (numero, nombre))
    conn.commit()
    conn.close()

# Actualizar historial del usuario
def actualizar_historial(numero, mensaje):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT historial FROM clientes WHERE numero = ?", (numero,))
    resultado = cursor.fetchone()
    historial = resultado[0] if resultado else ""

    nuevo_historial = (historial + f"\n{mensaje}")[-2000:]  # Limita el historial a 2000 caracteres
    cursor.execute("UPDATE clientes SET historial = ? WHERE numero = ?", (nuevo_historial, numero))
    conn.commit()
    conn.close()

# Buscar respuesta en caché
def obtener_de_cache(pregunta):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT respuesta FROM cache WHERE pregunta = ?", (pregunta,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else None

# Guardar respuesta en caché
def guardar_en_cache(pregunta, respuesta):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO cache (pregunta, respuesta) VALUES (?, ?)", (pregunta, respuesta))
    conn.commit()
    conn.close()

# Limpiar caché de respuestas antiguas (más de 7 días)
def limpiar_cache():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cache WHERE fecha < datetime('now', '-7 days')")
    conn.commit()
    conn.close()

# Generar respuesta con Gemini optimizada
def generar_respuesta_gemini(texto, historial):
    # Buscar en caché antes de llamar a Gemini
    respuesta_cache = obtener_de_cache(texto)
    if respuesta_cache:
        print("✅ Respuesta obtenida de la caché")
        return respuesta_cache

    prompt = f"Historial del usuario:\n{historial}\n\nUsuario: {texto}\nAsistente:"

    try:
        respuesta = modelo.generate_content(prompt)
        respuesta_texto = respuesta.text.strip()[:500]  # Limita respuesta a 500 caracteres
        guardar_en_cache(texto, respuesta_texto)  # Guardar en caché
        return respuesta_texto
    except Exception:
        return "Lo siento, estoy teniendo problemas para responder en este momento."

# Webhook para recibir mensajes de WhatsApp
@app.route('/webhook', methods=['POST'])
def webhook():
    limpiar_cache()  # Limpia caché antes de procesar nuevos mensajes

    data = request.json
    if "messages" in data:
        for message in data["messages"]:
            if message.get("from"):
                chat_id = message["from"]
                texto = message.get("text", {}).get("body", "")
                nombre = message.get("sender", {}).get("name", "Cliente")

                usuario = obtener_usuario(chat_id)
                if not usuario:
                    guardar_usuario(chat_id, nombre)

                historial = usuario[1] if usuario else ""
                respuesta = generar_respuesta_gemini(texto, historial)
                actualizar_historial(chat_id, f"Cliente: {texto}\nBot: {respuesta}")
                enviar_mensaje(chat_id, respuesta)

    return jsonify({"status": "received"}), 200

# Función para enviar mensajes a WhatsApp
def enviar_mensaje(chat_id, mensaje):
    url = "https://waba.360dialog.io/v1/messages"
    headers = {
        "D360-API-KEY": os.getenv("API_KEY_360"),  # Cargar la API Key de una variable de entorno
        "Content-Type": "application/json"
    }
    data = {
        "recipient_type": "individual",
        "to": chat_id,
        "type": "text",
        "text": {"body": mensaje}
    }
    requests.post(url, json=data, headers=headers)

# Configuración para Render
port = int(os.environ.get("PORT", 5000))

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)