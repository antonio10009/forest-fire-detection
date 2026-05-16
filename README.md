# 🔥 Forest Fire Detection System

> Sistema IoT de detección temprana de incendios forestales con alertas en tiempo real, dashboard web profesional e Inteligencia Artificial.

![Estado](https://img.shields.io/badge/estado-activo-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![License](https://img.shields.io/badge/licencia-MIT-orange)

---

## 🌍 El problema

Los incendios forestales en zonas como **Valparaíso, Chile** destruyen vidas, hogares y ecosistemas completos cada año. Los sistemas de detección existentes son costosos, centralizados y lentos.

Este proyecto propone una red de dispositivos IoT de **bajo costo**, distribuidos en zonas críticas de bosques, capaces de detectar el inicio de un incendio y alertar a las autoridades de forma **completamente automática**.

---

## ✨ Características

- 📡 Red de sensores IoT distribuidos en zonas forestales críticas
- 🔥 Detección temprana de humo, temperatura y llama en tiempo real
- 🚨 Alertas automáticas vía **WhatsApp y SMS** a bomberos y autoridades
- 🗺️ Mapa interactivo en tiempo real con ubicación GPS de cada nodo
- 📊 Dashboard profesional con estadísticas, gráficos e historial
- 🤖 Inteligencia Artificial para eliminar falsas alarmas *(en desarrollo)*
- ☀️ Energía autónoma con panel solar y batería LiPo
- 🌧️ Resistente al clima con carcasa IP67

---

## 🏗️ Arquitectura

```
[Sensores ESP32 en terreno]
         │
         │ HTTP / LoRaWAN
         ▼
[FastAPI Backend + PostgreSQL]
         │
    ┌────┴────┐
    ▼         ▼
[Dashboard] [Alertas]
Mapa Live   WhatsApp
Gráficos      SMS
Historial    Email
```

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| Firmware | C++ / Arduino IDE (ESP32) |
| Backend | Python 3.11 + FastAPI |
| Base de datos | PostgreSQL 16 + SQLAlchemy |
| Frontend | HTML + CSS + JavaScript |
| Mapas | Leaflet.js + OpenStreetMap |
| Gráficos | Chart.js |
| Alertas | Twilio (WhatsApp + SMS) |
| Deploy | Render.com |
| IA | scikit-learn *(en desarrollo)* |

---

## 📦 Dispositivo físico

| Componente | Función |
|---|---|
| ESP32 DevKit | Microcontrolador principal |
| Sensor MQ-2 | Detección de humo y gases |
| Sensor DHT22 | Temperatura y humedad |
| Sensor IR llama | Detección de fuego directo |
| GPS NEO-6M | Ubicación exacta del nodo |
| Panel solar + LiPo | Energía autónoma |
| Sirena 120dB | Alerta acústica local inmediata |
| Carcasa IP67 | Resistencia a lluvia y polvo |

> Costo estimado por nodo: **$30 USD** vs sistemas profesionales de $500+

---

## 🚀 Instalación local

### Requisitos previos

- Python 3.11+
- PostgreSQL 16
- Git

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/antonio10009/forest-fire-detection.git
cd forest-fire-detection

# 2. Crear entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp backend/.env.example backend/.env
# Editar backend/.env con tus credenciales

# 5. Iniciar servidor
uvicorn backend.main:app --reload

# 6. Abrir dashboard
# Abrir frontend/index.html en el navegador
```

---

## 🌐 Demo en producción

| Servicio | URL |
|---|---|
| API | https://forest-fire-detection-044r.onrender.com |
| Documentación API | https://forest-fire-detection-044r.onrender.com/docs |

---

## 📡 Endpoints principales

| Método | Endpoint | Descripción |
|---|---|---|
| GET | /api/sensors/ | Listar sensores activos |
| POST | /api/sensors/ | Registrar nuevo sensor |
| POST | /api/sensors/lectura | Recibir lectura del ESP32 |
| GET | /api/alerts/ | Alertas activas |
| GET | /api/alerts/historial | Historial completo |
| GET | /api/stats/resumen | Estadísticas generales |
| GET | /api/stats/zona-critica | Zona más crítica |

---

## 📁 Estructura del proyecto

```
forest-fire-detection/
├── backend/
│   ├── routers/
│   │   ├── sensors.py
│   │   ├── alerts.py
│   │   └── stats.py
│   ├── models/
│   │   └── sensor.py
│   ├── schemas/
│   │   └── schemas.py
│   ├── database.py
│   ├── notifications.py
│   └── main.py
├── firmware/
│   └── esp32_sensor.ino
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── map.js
│       ├── alerts.js
│       └── charts.js
├── simulator.py
├── requirements.txt
└── README.md
```

---

## 🗺️ Hoja de ruta

- [x] Backend FastAPI + PostgreSQL
- [x] Sistema de alertas WhatsApp + SMS automático
- [x] Dashboard web profesional en tiempo real
- [x] Mapa interactivo con ubicación GPS de sensores
- [x] Estadísticas y gráficos detallados
- [x] Simulador del ESP32 para pruebas
- [x] Deploy en producción con Render
- [ ] Firmware ESP32 completo con sensores físicos
- [ ] Red de nodos LoRaWAN para zonas sin WiFi
- [ ] Modelo IA para eliminar falsas alarmas
- [ ] Predicción de propagación del fuego
- [ ] Piloto real en zona crítica de Valparaíso
- [ ] Integración con CONAF y Bomberos Chile

---

## 🌱 Impacto social esperado

| Objetivo | Meta |
|---|---|
| Detectar incendios | En los primeros minutos |
| Costo por nodo | Menos de $30 USD |
| Zonas cubiertas | Cerros de Valparaíso y alrededores |
| Tiempo de respuesta | Reducir de horas a minutos |
| Vidas protegidas | Familias en zonas de interface urbano-forestal |

---

## 👨‍💻 Autor

**Antonio** — Ingeniería en Informática  
📍 Valparaíso, Chile  
🐙 GitHub: [@antonio10009](https://github.com/antonio10009)

---

## 📄 Licencia

MIT License — Libre para usar, modificar y distribuir con atribución.