from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

account_sid      = os.getenv("TWILIO_ACCOUNT_SID")
auth_token       = os.getenv("TWILIO_AUTH_TOKEN")
sms_number       = os.getenv("TWILIO_PHONE_NUMBER")
whatsapp_number  = os.getenv("TWILIO_WHATSAPP_NUMBER")
alert_number     = os.getenv("ALERT_PHONE_NUMBER")

client = Client(account_sid, auth_token)

def enviar_sms_alerta(mensaje: str):
    try:
        message = client.messages.create(
            body=mensaje,
            from_=sms_number,
            to=alert_number
        )
        print(f"SMS enviado: {message.sid}")
        return True
    except Exception as e:
        print(f"Error enviando SMS: {e}")
        return False

def enviar_whatsapp_alerta(mensaje: str):
    try:
        message = client.messages.create(
            body=mensaje,
            from_=f"whatsapp:{whatsapp_number}",
            to=f"whatsapp:{alert_number}"
        )
        print(f"WhatsApp enviado: {message.sid}")
        return True
    except Exception as e:
        print(f"Error enviando WhatsApp: {e}")
        return False

def disparar_alerta_incendio(sensor_nombre: str, ubicacion: str, temperatura: float, humo_ppm: float):
    mensaje = (
        f"🔥 ALERTA INCENDIO FORESTAL\n"
        f"Sensor: {sensor_nombre}\n"
        f"Ubicación: {ubicacion}\n"
        f"Temperatura: {temperatura}°C\n"
        f"Humo: {humo_ppm} PPM\n"
        f"⚠️ Requiere atención INMEDIATA"
    )
    enviar_sms_alerta(mensaje)
    enviar_whatsapp_alerta(mensaje)