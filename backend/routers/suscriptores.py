# backend/routers/suscriptores.py
# Webhook de Twilio + gestión de suscriptores WhatsApp

import os
import datetime
from fastapi import APIRouter, Depends, Form, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse

from backend.database import get_db
from backend.models.suscriptor import Suscriptor

router = APIRouter()


# ══════════════════════════════════════════════════════════════
# WEBHOOK — Twilio llama aquí cuando alguien escribe al número
#
# Configurar en Twilio Console → WhatsApp Senders → tu número
#   → Webhook URL: https://tu-backend.onrender.com/api/suscriptores/webhook
# ══════════════════════════════════════════════════════════════
@router.post("/webhook")
def webhook_whatsapp(
    From: str = Form(...),   # "whatsapp:+56937247294"
    Body: str = Form(...),   # texto que escribió el usuario
    db: Session = Depends(get_db)
):
    numero  = From.replace("whatsapp:", "").strip()
    mensaje = Body.strip().upper()
    resp    = MessagingResponse()

    if "SUSCRIBIR" in mensaje or "SUBSCRIBIR" in mensaje:
        existente = db.query(Suscriptor).filter(Suscriptor.numero_wa == numero).first()
        if existente:
            existente.activo     = True
            existente.fecha_baja = None
        else:
            db.add(Suscriptor(numero_wa=numero))
        db.commit()
        resp.message(
            "✅ *Suscrito a Forest Fire*\n"
            "Recibirás alertas automáticas cuando se detecte un incendio forestal.\n\n"
            "Escribe *SALIR* para cancelar en cualquier momento."
        )

    elif "SALIR" in mensaje or "BAJA" in mensaje or "CANCELAR" in mensaje:
        suscriptor = db.query(Suscriptor).filter(Suscriptor.numero_wa == numero).first()
        if suscriptor:
            suscriptor.activo     = False
            suscriptor.fecha_baja = datetime.datetime.now()
            db.commit()
        resp.message(
            "❌ Te diste de baja de las alertas Forest Fire.\n"
            "Escribe *SUSCRIBIR* para volver a activarlas."
        )

    elif "INFO" in mensaje or "AYUDA" in mensaje:
        resp.message(
            "🌲 *Forest Fire* — Detección temprana de incendios forestales\n\n"
            "Comandos:\n"
            "  *SUSCRIBIR* — Activar alertas automáticas\n"
            "  *SALIR*     — Cancelar suscripción\n"
            "  *INFO*      — Ver este mensaje\n\n"
            "Las alertas llegan en segundos desde que el sensor detecta fuego."
        )

    else:
        resp.message(
            "🌲 *Forest Fire*\n\n"
            "Escribe *SUSCRIBIR* para recibir alertas de incendio.\n"
            "Escribe *INFO* para más información."
        )

    return Response(content=str(resp), media_type="application/xml")


# ══════════════════════════════════════════════════════════════
# ADMIN — Ver lista de suscriptores activos
# GET /api/suscriptores/
# ══════════════════════════════════════════════════════════════
@router.get("/")
def listar_suscriptores(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db)
):
    query = db.query(Suscriptor)
    if solo_activos:
        query = query.filter(Suscriptor.activo == True)
    rows = query.order_by(Suscriptor.fecha_registro.desc()).all()

    return {
        "total": len(rows),
        "suscriptores": [
            {
                "id":              s.id,
                "numero_wa":       s.numero_wa,
                "nombre":          s.nombre,
                "zona":            s.zona,
                "activo":          s.activo,
                "fecha_registro":  str(s.fecha_registro),
            }
            for s in rows
        ]
    }


# ══════════════════════════════════════════════════════════════
# ADMIN — Agregar número manualmente (sin esperar que escriban)
# POST /api/suscriptores/agregar?numero=+56912345678
# ══════════════════════════════════════════════════════════════
@router.post("/agregar")
def agregar_suscriptor(
    numero: str = Query(..., description="Número en formato +56XXXXXXXXX"),
    nombre: str = Query(None),
    zona:   str = Query("General"),
    db: Session = Depends(get_db)
):
    existente = db.query(Suscriptor).filter(Suscriptor.numero_wa == numero).first()
    if existente:
        existente.activo     = True
        existente.fecha_baja = None
        existente.nombre     = nombre or existente.nombre
        existente.zona       = zona
        db.commit()
        return {"status": "reactivado", "numero": numero}

    db.add(Suscriptor(numero_wa=numero, nombre=nombre, zona=zona))
    db.commit()
    return {"status": "agregado", "numero": numero}