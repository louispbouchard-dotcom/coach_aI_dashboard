# -*- coding: utf-8 -*-
import os
import re
import json
import requests
import datetime as dt

import streamlit as st
from streamlit.components.v1 import html

# ===================== PAGE CONFIG =====================
st.set_page_config(page_title="Coach IA – Serge Pro Edition", page_icon="🏋️", layout="wide")

# ===================== STYLE =====================
st.markdown("""
<style>
  * {font-family: 'Poppins', sans-serif;}
  .small-muted { color: #6b7280; font-size: 0.9rem; }
  .fc { font-family: 'Poppins', sans-serif; }
</style>
""", unsafe_allow_html=True)

# ===================== STATE =====================
def _init_state():
    defaults = {
        "step": "landing",
        "q_index": 0,
        "answers": {},
        "active_card": None,
        "plan_text": "",
        "plan_edit_mode": False,   # << NEW
        "api_key": "",
        "chat_messages": [
            {"role": "system", "content": (
                "Tu es Serge, un coach sportif professionnel. "
                "Tu aides les utilisateurs avec leurs questions sur l'entraînement, "
                "la nutrition, la récupération et la motivation. Réponds de façon "
                "concise, encourageante et professionnelle."
            )}
        ],
        # WhatsApp config
        "whatsapp_phone_number_id": "",
        "whatsapp_access_token": "",
        "whatsapp_api_version": "v18.0",
        "recipient_phone": "",
        "notifications_enabled": False,
        "reminder_days": [1, 3, 5],
        "message_template_name": "reminder_workout",
        # Nutrition
        "nutrition_plan": None,
        "nutrition_edit_mode": False,
        # Chat historique simple
        "chat_history": [],
        # Calendar
        "calendar_start_date": dt.date.today(),
        "calendar_events": [],
        "_last_plan_hash": None,
        # Workout history
        "workout_history": [],
        # Routing page courante
        "page": None,
        # Flash visual
        "flash_plan_updated": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init_state()

# ===================== WHATSAPP SENDER =====================
def send_whatsapp_text_message(to_number: str, message: str) -> bool:
    try:
        if not st.session_state.whatsapp_phone_number_id or not st.session_state.whatsapp_access_token:
            st.error("⚠️ Identifiants WhatsApp Business API manquants")
            return False
        url = f"https://graph.facebook.com/{st.session_state.whatsapp_api_version}/{st.session_state.whatsapp_phone_number_id}/messages"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {st.session_state.whatsapp_access_token}"}
        data = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": to_number,
                "type": "text", "text": {"preview_url": False, "body": message}}
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
        return response.status_code == 200
    except Exception as e:
        st.error(f"❌ Erreur lors de l'envoi: {str(e)}")
        return False

def send_whatsapp_template_message(to_number: str, template_name: str, template_params: list = None) -> bool:
    try:
        if not st.session_state.whatsapp_phone_number_id or not st.session_state.whatsapp_access_token:
            st.error("⚠️ Identifiants WhatsApp Business API manquants")
            return False
        url = f"https://graph.facebook.com/{st.session_state.whatsapp_api_version}/{st.session_state.whatsapp_phone_number_id}/messages"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {st.session_state.whatsapp_access_token}"}
        components = []
        if template_params:
            parameters = [{"type": "text", "text": param} for param in template_params]
            components.append({"type": "body", "parameters": parameters})
        data = {"messaging_product": "whatsapp", "to": to_number, "type": "template",
                "template": {"name": template_name, "language": {"code": "fr"}, "components": components}}
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
        return response.status_code == 200
    except Exception as e:
        st.error(f"❌ Erreur lors de l'envoi: {str(e)}")
        return False

def generate_reminder_params(day_number: int, profile: dict) -> list:
    nom = profile.get("nom", "Champion")
    duree = profile.get("duree_min", 30)
    return [nom, str(day_number), f"{duree} minutes"]

# ===================== SIDEBAR =====================
with st.sidebar:
    st.subheader("🔧 Paramètres")
    st.session_state.api_key = st.text_input("OpenAI API Key (optionnel)", value=st.session_state.api_key, type="password", key="sb_api_key")

with st.sidebar:
    st.divider()
    st.subheader("📱 Notifications WhatsApp")
    with st.expander("⚙️ Configuration API WhatsApp", expanded=False):
        st.info("Renseigne les identifiants de ton compte WhatsApp Business API.")
        st.session_state.whatsapp_phone_number_id = st.text_input("Phone Number ID", value=st.session_state.whatsapp_phone_number_id, type="password", key="sb_wa_phone_id")
        st.session_state.whatsapp_access_token   = st.text_input("Access Token", value=st.session_state.whatsapp_access_token, type="password", key="sb_wa_token")
        st.session_state.whatsapp_api_version    = st.text_input("Version de l'API", value=st.session_state.whatsapp_api_version, key="sb_wa_version")
        st.session_state.message_template_name   = st.text_input("Nom du template de rappel", value=st.session_state.message_template_name, key="sb_wa_tpl")

    st.session_state.notifications_enabled = st.toggle("🔔 Activer les rappels WhatsApp", value=st.session_state.notifications_enabled, key="sb_toggle_notify")
    if st.session_state.notifications_enabled:
        st.session_state.recipient_phone = st.text_input("📞 Numéro (sans +)", value=st.session_state.recipient_phone, key="sb_recipient")
        st.write("**Jours de rappel:**")
        cols = st.columns(4)
        selected_days = []
        for i in range(1, 8):
            with cols[(i-1) % 4]:
                if st.checkbox(f"J{i}", value=i in st.session_state.reminder_days, key=f"sb_day_{i}"):
                    selected_days.append(i)
        st.session_state.reminder_days = selected_days

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🧪 Test texte", use_container_width=True, key="sb_test_text"):
                if not st.session_state.recipient_phone:
                    st.warning("⚠️ Entre un numéro")
                else:
                    if send_whatsapp_text_message(st.session_state.recipient_phone, "🏋️ Test Coach Serge IA!\n\nLes notifications fonctionnent! 💪"):
                        st.success("✅ Message envoyé!")
        with c2:
            if st.button("🧪 Test template", use_container_width=True, key="sb_test_tpl"):
                if not st.session_state.recipient_phone:
                    st.warning("⚠️ Entre un numéro")
                else:
                    if send_whatsapp_template_message(st.session_state.recipient_phone, st.session_state.message_template_name, ["Champion", "1", "30 minutes"]):
                        st.success("✅ Template envoyé!")

# ===================== QUESTIONNAIRE =====================
QUESTIONS = [
    {"key":"age","label":"Quel est ton âge?","type":"number","min":13,"max":100},
    {"key":"sexe","label":"Quel est ton sexe?","type":"select","options":["Homme","Femme","Autre / Préfère ne pas dire"]},
    {"key":"taille_cm","label":"Quelle est ta taille (en cm)?","type":"number","min":120,"max":220},
    {"key":"poids_kg","label":"Quel est ton poids (en kg)?","type":"number","min":35,"max":220},
    {"key":"niveau_exp","label":"Quel est ton niveau d'expérience en entraînement?","type":"select","options":["Débutant","Intermédiaire","Expert"]},
    {"key":"blessures","label":"As-tu actuellement des blessures ou des limitations physiques?","type":"text"},
    {"key":"sante","label":"As-tu des problèmes de santé connus (asthme, hypertension, diabète, etc.)?","type":"text"},
    {"key":"activite","label":"Quel est ton niveau d'activité physique au quotidien (hors entraînements)?","type":"select","options":[
        "Peu actif (Travail de bureau)","Modérément actif (Marche régulière)","Actif (Travail physique)","Très actif (Sports fréquents)"]},
    {"key":"objectif_principal","label":"Quel est ton objectif principal d'entraînement?","type":"text"},
    {"key":"objectif_secondaire","label":"As-tu un objectif secondaire?","type":"text"},
    {"key":"horizon","label":"Dans combien de temps veux-tu atteindre ton objectif principal?","type":"select","options":["3 mois","6 mois","1 an ou plus"]},
    {"key":"motivation","label":"Quel est ton niveau de motivation sur 10?","type":"slider","min":1,"max":10},
    {"key":"types_exos","label":"Quel type d'exercices préfères-tu?","type":"multiselect","options":["Musculation","Cardio","Sports collectifs","Yoga / Pilates","Autre"]},
    {"key":"jours_sem","label":"Combien de jours par semaine veux-tu t'entrainer?","type":"slider","min":1,"max":7},
    {"key":"duree_min","label":"Combien de temps veux-tu consacrer à chaque séance (en min)?","type":"slider","min":10,"max":120,"step":5},
    {"key":"moment","label":"À quel moment de la journée préfères-tu t'entraîner?","type":"select","options":["Matin","Midi","Après-midi","Soir / Nuit"]},
    {"key":"lieu","label":"Préfères-tu t'entraîner à l'intérieur ou dehors?","type":"select","options":["Intérieur","Extérieur","Peu importe"]},
    {"key":"materiel","label":"Quel matériel d'entraînement as-tu à ta disposition?","type":"text"},
    {"key":"sommeil_h","label":"Combien d'heures dors-tu en moyenne par nuit?","type":"slider","min":4.0,"max":12.0,"step":0.5},
    {"key":"ville","label":"Dans quelle ville t'entraînes-tu (pour la météo)?","type":"text"},
    {"key":"nutrition","label":"Souhaite-tu recevoir des conseils de nutrition et/ou de récupération?","type":"select","options":["Oui","Non"]},
]
TOTAL_Q = len(QUESTIONS)

# ===================== OPENAI (optionnel) =====================
def call_openai_plan(api_key: str, profile: dict) -> str:
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        system_prompt = (
            "You are a certified fitness coach. Generate a safe, concise 7-day plan "
            "tailored to the JSON profile. Each day: Day X — Session; Duration; "
            "Exercises (Sets x Reps); RPE. Add short recovery/nutrition tips if requested."
        )
        body = {"model": "gpt-4o-mini","messages": [
                    {"role":"system","content":system_prompt},
                    {"role":"user","content":f"User profile (JSON): {json.dumps(profile, ensure_ascii=False)}"}
                ],
                "max_tokens": 700, "temperature": 0.7}
        r = requests.post(url, headers=headers, json=body, timeout=60)
        if r.status_code == 200:
            data = r.json()
            return data["choices"][0]["message"]["content"]
        return ""
    except Exception:
        return ""

def call_openai_chat(api_key: str, user_input: str, profile: dict) -> str:
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        system_prompt = (
            "Tu es un coach sportif personnel expert. Tu aides l'utilisateur avec ses questions "
            "sur l'entraînement, la nutrition et la santé. Réponds de manière concise et pratique. "
            f"Voici le profil de l'utilisateur: {json.dumps(profile, ensure_ascii=False)}"
        )
        body = {"model":"gpt-4o-mini","messages":[
            {"role":"system","content":system_prompt},
            {"role":"user","content": user_input}
        ],"max_tokens":500,"temperature":0.7}
        r = requests.post(url, headers=headers, json=body, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return "Je n'ai pas pu contacter le modèle pour une réponse détaillée."
    except Exception as e:
        return f"Erreur: {e}"

def call_openai_nutrition(api_key: str, profile: dict) -> str:
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        system_prompt = (
            "Tu es un nutritionniste certifié. Crée un plan de nutrition pour 7 jours "
            "basé sur le profil JSON de l'utilisateur. Inclure pour chaque jour : "
            "Petit-déjeuner, Dîner, Souper, Collations, et un total calorique estimé. "
            "Adapter selon l'objectif et le niveau d'activité. Présente le plan de façon lisible."
        )
        body = {"model":"gpt-4o-mini","messages":[
            {"role":"system","content":system_prompt},
            {"role":"user","content": f"Profil utilisateur : {json.dumps(profile, ensure_ascii=False)}"}
        ],"max_tokens":700,"temperature":0.7}
        r = requests.post(url, headers=headers, json=body, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return ""
    except Exception:
        return ""

# ===================== AI PLAN ADAPTATION (agent) =====================
def _extract_json_block(text: str):
    try:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if m: return json.loads(m.group(1))
        m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if m: return json.loads(m.group(1))
        return None
    except Exception:
        return None

def ai_edit_plan(api_key: str, instruction: str, plan_text: str, profile: dict) -> dict:
    """
    Adapte le plan complet sans besoin de dire 'par quoi'.
    Retour: {"ok": bool, "new_plan": str, "summary": str}
    """
    if not api_key:
        return {"ok": False, "new_plan": "", "summary": "Pas de clé API."}

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    system_prompt = (
        "Tu es un coach certifié. Tu reçois un 'plan d'entraînement' en Markdown "
        "(7 jours avec titres '**Jour X — Titre**' ou '**Day X: Title**'). "
        "Tu dois ADAPTER ce plan selon une instruction utilisateur (p.ex. plus de course, moins de HIIT, "
        "contraintes de blessures, durée, intensité, matériel dispo). "
        "Garde le format Markdown existant (jours, puces, RPE s'il y en a). "
        "Règles de sécurité: pas de mouvements risqués pour un débutant; respecter les blessures et le matériel. "
        "Réponds STRICTEMENT en JSON: "
        "{'new_plan': '<markdown complet>', 'summary': '<changements concis>', 'changed_days': [<ints>]}"
    )

    user_prompt = (
        "=== PROFIL JSON ===\n"
        f"{json.dumps(profile, ensure_ascii=False)}\n\n"
        "=== INSTRUCTION UTILISATEUR ===\n"
        f"{instruction}\n\n"
        "=== PLAN ACTUEL ===\n"
        f"{plan_text}\n\n"
        "=== FORMAT SORTIE ===\n"
        "{'new_plan': '...', 'summary': '...', 'changed_days': [1,2,3]}"
    )

    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
        "max_tokens": 1400,
        "temperature": 0.5
    }

    try:
        r = requests.post(url, headers=headers, json=body, timeout=60)
        if r.status_code != 200:
            return {"ok": False, "new_plan": "", "summary": f"Erreur API: {r.status_code}"}
        content = r.json()["choices"][0]["message"]["content"]
        obj = _extract_json_block(content) or {}
        new_plan = obj.get("new_plan", "").strip()
        summary  = obj.get("summary", "").strip()
        if new_plan and ("Jour 1" in new_plan or "Day 1" in new_plan):
            return {"ok": True, "new_plan": new_plan, "summary": summary or "Plan adapté."}
        return {"ok": False, "new_plan": "", "summary": "Réponse modèle non exploitable."}
    except Exception as e:
        return {"ok": False, "new_plan": "", "summary": f"Erreur: {e}"}

# ===================== FALLBACKS =====================
def fallback_plan(p: dict) -> str:
    obj = p.get("objectif_principal", "Condition générale") or "Condition générale"
    dur = int(p.get("duree_min", 30) or 30)
    jours = int(p.get("jours_sem", 3) or 3)
    niveau = p.get("niveau_exp", "Débutant") or "Débutant"
    return (
        f"**Plan d'entraînement 7 jours — Serge Coach**\n\n"
        f"**Objectif:** {obj}\n"
        f"**Niveau:** {niveau}\n"
        f"**Durée par séance:** ~{dur} min\n"
        f"**Fréquence recommandée:** {jours} jours/semaine\n\n"
        "---\n\n"
        "**Jour 1 — Full Body (RPE 6)**\n"
        "- Échauffement: 5 min mobilité\n"
        "- Squats: 3 x 12\n"
        "- Pompes: 3 x 10\n"
        "- Rowing haltères: 3 x 12\n"
        "- Planche: 3 x 30s\n\n"
        "**Jour 2 — Cardio léger (RPE 5)**\n"
        f"- Marche rapide / vélo: {dur} min\n\n"
        "**Jour 3 — Haut du corps (RPE 6)**\n"
        "- Développé haltères: 3 x 12\n"
        "- Tirage horizontal: 3 x 12\n"
        "- Élévations latérales: 3 x 15\n"
        "- Curl biceps: 3 x 12\n"
        "- Extension triceps: 3 x 12\n\n"
        "**Jour 4 — Mobilité & Core (RPE 3-4)**\n"
        "- Yoga/étirements: 15-20 min\n"
        "- Dead bug: 3 x 12\n"
        "- Side plank: 3 x 20s/side\n\n"
        "**Jour 5 — Bas du corps (RPE 6)**\n"
        "- Fentes alternées: 3 x 12/ jambe\n"
        "- Pont fessier: 3 x 15\n"
        "- Squat sumo: 3 x 12\n"
        "- Mollets debout: 3 x 15\n\n"
        "**Jour 6 — Intervalles (RPE 7)**\n"
        f"- 6 x (2 min effort / 1 min récup) — total ~{dur} min\n\n"
        "**Jour 7 — Repos actif**\n"
        "- Marche 20-30 min + mobilité\n\n"
        "---\n\n"
        "**Conseils:** Hydratation 2-3L, 7-9h de sommeil, protéines à chaque repas."
    )

def fallback_nutrition(profile: dict) -> str:
    objectif = profile.get("objectif_principal", "Condition générale") or "Condition générale"
    sexe = profile.get("sexe", "Homme") or "Homme"
    poids = float(profile.get("poids_kg", 70) or 70)
    taille = float(profile.get("taille_cm", 175) or 175)
    age = int(profile.get("age", 30) or 30)
    activite = profile.get("activite", "Modérément actif") or "Modérément actif"
    if sexe == "Homme":
        bmr = 10 * poids + 6.25 * taille - 5 * age + 5
    else:
        bmr = 10 * poids + 6.25 * taille - 5 * age - 161
    facteur_act = {
        "Peu actif (Travail de bureau)": 1.2,
        "Modérément actif (Marche régulière)": 1.4,
        "Actif (Travail physique)": 1.6,
        "Très actif (Sports fréquents)": 1.8
    }.get(activite, 1.4)
    calories = int(bmr * facteur_act)
    if "perte" in (objectif or "").lower():
        calories -= 400
    elif "masse" in (objectif or "").lower():
        calories += 400
    proteines = round(poids * 1.8)
    glucides = round((calories * 0.5) / 4)
    lipides = round((calories * 0.25) / 9)
    return f"""
**Plan nutritionnel - Objectif : {objectif}**

🔹 Apport cible : **{calories} kcal / jour**
🔹 Répartition :
- Protéines : {proteines} g
- Glucides : {glucides} g
- Lipides : {lipides} g

🍽️ Exemple de journée :
- **Petit-déjeuner :** Avoine, fruits rouges, yogourt grec
- **Dîner :** Poulet, riz brun, légumes vapeur
- **Souper :** Saumon, quinoa, brocoli
- **Collations :** Amandes, pomme, shake protéiné

💧 *Hydrate-toi 2-3 L/jour et limite les sucres ajoutés.*"""

# ===================== METEO (Open-Meteo) =====================
def geocode_city(city: str):
    try:
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": city, "count": 1, "language": "fr"}, timeout=10)
        res = r.json().get("results", [])
        if not res: return None
        x = res[0]
        return float(x["latitude"]), float(x["longitude"]), f'{x["name"]}, {x.get("country","")}'
    except:
        return None

def get_today_weather(lat: float, lon: float):
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
                         params={"latitude": lat, "longitude": lon,
                                 "hourly":"temperature_2m,precipitation_probability",
                                 "forecast_days":1,"timezone":"auto"}, timeout=10)
        return r.json()
    except:
        return None

def weather_advice(weather_json, planned_minutes: int):
    try:
        temps = weather_json["hourly"]["temperature_2m"][0]
        prec = weather_json["hourly"]["precipitation_probability"][0]
        if prec>50 or temps<0 or temps>28:
            return (f"Météo peu favorable ({temps}°C, pluie {prec}%). "
                    f"Alternative indoor ~{planned_minutes} min : circuit cardio / full body / yoga.")
        return f"Météo OK ({temps}°C, pluie {prec}%). Entraînement extérieur possible."
    except:
        return "Météo indisponible."

# ===================== CALENDRIER =====================
from datetime import datetime, timedelta
try:
    from streamlit_calendar import calendar as st_calendar
    CALENDAR_AVAILABLE = True
except Exception:
    CALENDAR_AVAILABLE = False

# --- Parser robuste des jours ---
def parse_workout_plan(plan_text: str) -> list:
    """
    Extrait les sessions du plan en détectant des titres de jour au format:
    **Jour X — Titre**, **Jour X: Titre**, **Day X - Title**, etc.
    Tolère espaces et variantes de tirets.
    """
    sessions = []
    lines = plan_text.splitlines()
    day_header_re = re.compile(r"^\s*\*\*\s*(Jour|Day)\s+(\d+)\s*(?:[—\-:]\s*(.*?))?\s*\*\*\s*$", re.IGNORECASE)

    current_day = None
    current_title = None
    current_description = []

    for raw in lines:
        line = raw.rstrip()
        m = day_header_re.match(line)
        if m:
            if current_day is not None:
                sessions.append({
                    "day": current_day,
                    "title": current_title or "Entraînement",
                    "description": "\n".join(current_description[:10]).strip()
                })
            current_day = int(m.group(2))
            current_title = (m.group(3) or "Entraînement").strip()
            current_description = []
        else:
            if current_day is not None and line.strip():
                current_description.append(line.strip())

    if current_day is not None:
        sessions.append({
            "day": current_day,
            "title": current_title or "Entraînement",
            "description": "\n".join(current_description[:10]).strip()
        })

    return sessions

def create_calendar_events(sessions: list, start_date=None) -> list:
    if start_date is None:
        start_date = datetime.now()
    if hasattr(start_date, 'hour'):
        start_date = datetime.combine(start_date.date(), datetime.min.time())
    else:
        start_date = datetime.combine(start_date, datetime.min.time())

    moment_pref = st.session_state.answers.get("moment", "Matin")
    time_map = {"Matin":"07:00","Midi":"12:00","Après-midi":"15:00","Soir / Nuit":"18:00"}
    start_time = time_map.get(moment_pref, "07:00")
    duree = int(st.session_state.answers.get("duree_min", 60) or 60)
    end_hour = int(start_time.split(':')[0])
    end_minute = int(start_time.split(':')[1]) + duree
    if end_minute >= 60:
        end_hour += end_minute // 60
        end_minute = end_minute % 60
    end_time = f"{end_hour:02d}:{end_minute:02d}"

    events = []
    for session in sessions:
        event_date = start_date + timedelta(days=session['day'] - 1)
        date_str = event_date.strftime("%Y-%m-%d")
        title_lower = (session['title'] or "").lower()
        is_rest = any(w in title_lower for w in ["repos","rest","récupération","recovery"])
        color = "#666666" if is_rest else "#3ea6ff"
        events.append({
            "title": f"Jour {session['day']}: {session['title']}",
            "start": f"{date_str}T{start_time}:00",
            "end": f"{date_str}T{end_time}:00",
            "extendedProps": {"description": session['description'], "day_number": session['day']},
            "backgroundColor": color, "borderColor": color, "textColor": "#ffffff"
        })
    return events

def recompute_calendar_events():
    """Recalcule et stocke les événements du calendrier selon le plan et la date choisie."""
    if "calendar_start_date" not in st.session_state or not st.session_state.calendar_start_date:
        st.session_state.calendar_start_date = dt.date.today()

    plan_text = st.session_state.get("plan_text", "") or ""
    sessions = parse_workout_plan(plan_text)
    if not sessions:
        st.session_state["calendar_events"] = []
        return

    start_date = st.session_state.calendar_start_date
    events = create_calendar_events(sessions, start_date)
    st.session_state["calendar_events"] = events

# ===================== AGENT / ORCHESTRATION (chat ↔ plan ↔ calendrier) =====================
def _get_day_bounds(plan_text: str, day_number: int):
    pattern_day = re.compile(rf"^\*\*(Jour|Day)\s+{day_number}\b.*$", re.MULTILINE)
    match = pattern_day.search(plan_text)
    if not match:
        return None, None
    start_idx = match.start()
    pattern_next = re.compile(r"^\*\*(Jour|Day)\s+\d+\b.*$", re.MULTILINE)
    next_match = pattern_next.search(plan_text, match.end())
    end_idx = next_match.start() if next_match else len(plan_text)
    return start_idx, end_idx

def replace_in_day(plan_text: str, day_number: int, old_term: str, new_term: str):
    start, end = _get_day_bounds(plan_text, day_number)
    if start is None:
        return plan_text, False
    before = plan_text[:start]; section = plan_text[start:end]; after = plan_text[end:]
    replaced_section, n = re.subn(re.escape(old_term), new_term, section, flags=re.IGNORECASE)
    if n == 0:
        synonyms = {
            "treadmill": ["tapis roulant","tapis","treadmill"],
            "course en plein air": ["course outdoor","course plein air","jogging dehors","course en plein air"]
        }
        candidates = [old_term]
        for k, arr in synonyms.items():
            if old_term.lower() in [x.lower() for x in arr+[k]]:
                candidates = arr+[k]; break
        found = False; tmp = section
        for cand in candidates:
            tmp, n2 = re.subn(re.escape(cand), new_term, tmp, flags=re.IGNORECASE)
            if n2>0: found=True
        if found:
            replaced_section = tmp
        else:
            return plan_text, False
    return before + replaced_section + after, True

def add_exercise_to_day(plan_text: str, day_number: int, line_text: str):
    start, end = _get_day_bounds(plan_text, day_number)
    if start is None: return plan_text, False
    before = plan_text[:start]; section = plan_text[start:end].rstrip(); after = plan_text[end:]
    if not line_text.strip().startswith("-"):
        line_text = "- " + line_text.strip()
    if not section.endswith("\n"):
        section += "\n"
    section += line_text + "\n"
    return before + section + after, True

def remove_line_in_day(plan_text: str, day_number: int, contains_text: str):
    start, end = _get_day_bounds(plan_text, day_number)
    if start is None: return plan_text, False
    before = plan_text[:start]; section = plan_text[start:end]; after = plan_text[end:]
    new_lines = []; removed=False
    for ln in section.splitlines():
        if re.search(re.escape(contains_text), ln, flags=re.IGNORECASE):
            removed=True; continue
        new_lines.append(ln)
    if not removed: return plan_text, False
    new_section = "\n".join(new_lines) + ("\n" if section.endswith("\n") else "")
    return before + new_section + after, True

def _set_moment_pref(moment_label: str):
    mapping = {
        "matin":"Matin","morning":"Matin","midi":"Midi","noon":"Midi",
        "après-midi":"Après-midi","apres-midi":"Après-midi","afternoon":"Après-midi",
        "soir":"Soir / Nuit","nuit":"Soir / Nuit","evening":"Soir / Nuit","night":"Soir / Nuit"
    }
    key = moment_label.strip().lower()
    st.session_state.answers["moment"] = mapping.get(key, st.session_state.answers.get("moment", "Matin"))

def _set_reminder_days_from_text(text: str):
    days = sorted({int(d) for d in re.findall(r"J\s*([1-7])", text, flags=re.IGNORECASE)})
    if days: st.session_state.reminder_days = days

def _parse_date_from_text(text: str):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m: y, M, d = map(int, m.groups()); return dt.date(y, M, d)
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if m:
        d, M, y = map(int, m.groups())
        try: return dt.date(y, M, d)
        except: return None
    return None

def _regenerate_plan_if_needed():
    a = st.session_state.answers
    profile = {
        "age": a.get("age"), "sexe": a.get("sexe"), "taille_cm": a.get("taille_cm"),
        "poids_kg": a.get("poids_kg"), "niveau_exp": a.get("niveau_exp"),
        "blessures": a.get("blessures"), "sante": a.get("sante"), "activite": a.get("activite"),
        "objectif_principal": a.get("objectif_principal"), "objectif_secondaire": a.get("objectif_secondaire"),
        "horizon": a.get("horizon"), "motivation": a.get("motivation"), "types_exos": a.get("types_exos"),
        "jours_sem": a.get("jours_sem"), "duree_min": a.get("duree_min"), "moment": a.get("moment"),
        "lieu": a.get("lieu"), "materiel": a.get("materiel"), "sommeil_h": a.get("sommeil_h"),
        "ville": a.get("ville"), "nutrition": a.get("nutrition")
    }
    plan_text = call_openai_plan(st.session_state.api_key, profile) if st.session_state.api_key else ""
    st.session_state.plan_text = plan_text or fallback_plan(profile)
    st.session_state._last_plan_hash = hash(st.session_state.plan_text)
    recompute_calendar_events()

ORDINALS_FR = {
    "premiere": 1, "première": 1, "premier": 1, "1ere": 1, "1ère": 1, "1er": 1,
    "deuxieme": 2, "deuxième": 2, "2eme": 2, "2ème": 2,
    "troisieme": 3, "troisième": 3, "3eme": 3, "3ème": 3,
    "quatrieme": 4, "quatrième": 4, "4eme": 4, "4ème": 4,
    "cinquieme": 5, "cinquième": 5, "5eme": 5, "5ème": 5,
    "sixieme": 6, "sixième": 6, "6eme": 6, "6ème": 6,
    "septieme": 7, "septième": 7, "7eme": 7, "7ème": 7,
}
def _extract_day_number(text: str):
    m = re.search(r"\b(?:jour|day)\s*(\d)\b", text, flags=re.IGNORECASE)
    if m: return int(m.group(1))
    m = re.search(r"\b(premi(?:er|ère|ere)|deuxi(?:eme|ème)|troisi(?:eme|ème)|quatri(?:eme|ème)|cinqui(?:eme|ème)|sixi(?:eme|ème)|septi(?:eme|ème))\b.*\b(?:jour|journée)\b", text, flags=re.IGNORECASE)
    if m:
        key = m.group(1).lower().replace("é","e")
        return ORDINALS_FR.get(key)
    return None

def handle_chat_command(user_text: str):
    """
    Retourne: {"feedback": str, "plan_changed": bool, "calendar_changed": bool}
    """
    text = user_text.strip()
    low  = text.lower()

    # (A) Régénérer
    if re.search(r"\b(régénère|regenere|regenerate)\b.*\bplan\b", low):
        _regenerate_plan_if_needed()
        return {"feedback":"🔄 J'ai régénéré ton plan.", "plan_changed":True, "calendar_changed":False}

    # (B) Ajout d'exo
    m = re.search(r"(?:ajout|ajoute|add)\w*.*?(?:jour|day)\s*(\d)\D+(.+)$", low, flags=re.IGNORECASE)
    if not m:
        dnum = _extract_day_number(low)
        if dnum:
            m2 = re.search(r"(?:ajout|ajoute|add)\w*\D+(.+)$", low, flags=re.IGNORECASE)
            if m2:
                to_add = m2.group(1).strip()
                st.session_state.plan_text, ok = add_exercise_to_day(st.session_state.plan_text or "", dnum, to_add)
                if ok:
                    st.session_state._last_plan_hash = hash(st.session_state.plan_text)
                    recompute_calendar_events()
                    return {"feedback": f"➕ Jour {dnum}: j'ai ajouté « {to_add} ».","plan_changed":True,"calendar_changed":True}
    else:
        dnum = int(m.group(1)); to_add = m.group(2).strip()
        st.session_state.plan_text, ok = add_exercise_to_day(st.session_state.plan_text or "", dnum, to_add)
        if ok:
            st.session_state._last_plan_hash = hash(st.session_state.plan_text)
            recompute_calendar_events()
            return {"feedback": f"➕ Jour {dnum}: j'ai ajouté « {to_add} ».","plan_changed":True,"calendar_changed":True}

    # (C) Remplacement explicite
    m = re.search(r"(?:remplac|chang|modif)\w*\s+(.+?)\s+(?:par|for)\s+(.+)$", low, flags=re.IGNORECASE)
    if m:
        old_term = m.group(1).strip(); new_term = m.group(2).strip()
        dnum = _extract_day_number(low) or 1
        st.session_state.plan_text, ok = replace_in_day(st.session_state.plan_text or "", dnum, old_term, new_term)
        if ok:
            st.session_state._last_plan_hash = hash(st.session_state.plan_text)
            recompute_calendar_events()
            return {"feedback": f"✏️ Jour {dnum}: « {old_term} » → « {new_term} ».","plan_changed":True,"calendar_changed":True}
        else:
            return {"feedback": f"⚠️ Je n'ai pas trouvé « {old_term} » au Jour {dnum}.","plan_changed":False,"calendar_changed":False}

    # (D) Suppression / remplacement implicite
    if re.search(r"\b(remplac|supprim|retir|enlev)\w*\b", low) and re.search(r"(jour|day|premi|deuxi|troisi|quatri|cinqui|sixi|septi)", low):
        dnum = _extract_day_number(low) or 1
        m = re.search(r"\b(remplac|supprim|retir|enlev)\w*\b\s+(les|des|du|de la|le|la|l'|d')?\s*([a-z0-9 \-\(\)\/]+)", low)
        if m:
            target = m.group(3).strip()
            st.session_state.plan_text, ok = remove_line_in_day(st.session_state.plan_text or "", dnum, target)
            if ok:
                st.session_state._last_plan_hash = hash(st.session_state.plan_text)
                recompute_calendar_events()
                return {"feedback": f"🗑️ Jour {dnum}: j'ai retiré « {target} ».","plan_changed":True,"calendar_changed":True}
            else:
                st.session_state.plan_text, ok2 = replace_in_day(st.session_state.plan_text or "", dnum, target, "High knees")
                if ok2:
                    st.session_state._last_plan_hash = hash(st.session_state.plan_text)
                    recompute_calendar_events()
                    return {"feedback": f"✏️ Jour {dnum}: j'ai remplacé « {target} » par « High knees ».","plan_changed":True,"calendar_changed":True}
                return {"feedback": f"⚠️ Impossible de trouver « {target} » au Jour {dnum}.","plan_changed":False,"calendar_changed":False}

    # (E) Préférence horaire
    if re.search(r"(matin|morning|midi|noon|après-midi|apres-midi|afternoon|soir|nuit|evening|night)", low) and re.search(r"(séance|seance|workout|entrain|entrainement)", low):
        m = re.search(r"(matin|morning|midi|noon|après-midi|apres-midi|afternoon|soir|nuit|evening|night)", low)
        _set_moment_pref(m.group(1))
        recompute_calendar_events()
        return {"feedback": f"⏰ Préférence horaire: **{st.session_state.answers.get('moment')}**.","plan_changed":False,"calendar_changed":True}

    # (F) Notifications
    if re.search(r"(active|enable)\w*.*(notification|rappel)", low):
        st.session_state.notifications_enabled = True; _set_reminder_days_from_text(low)
        return {"feedback": f"🔔 Notifications activées ({', '.join('J'+str(d) for d in st.session_state.reminder_days)})","plan_changed":False,"calendar_changed":False}
    if re.search(r"(désactive|desactive|disable)\w*.*(notification|rappel)", low):
        st.session_state.notifications_enabled = False
        return {"feedback":"🔕 Notifications désactivées.","plan_changed":False,"calendar_changed":False}

    # (G) Date de début
    if re.search(r"(date de début|start date|commence|début du programme)", low):
        maybe_date = _parse_date_from_text(low)
        if maybe_date:
            st.session_state["calendar_start_date"] = maybe_date
            recompute_calendar_events()
            return {"feedback": f"🗓️ Début fixé au {maybe_date.isoformat()}.",
                    "plan_changed": False, "calendar_changed": True}
        return {"feedback":"⚠️ Donne une date (YYYY-MM-DD ou DD/MM/YYYY).",
                "plan_changed":False,"calendar_changed":False}

    # (H) Ville
    m = re.search(r"(?:ville|city)\s*[:=]\s*(.+)$", text, flags=re.IGNORECASE)
    if m:
        city = m.group(1).strip()
        st.session_state.answers["ville"] = city
        return {"feedback": f"📍 Ville mise à « {city} ».","plan_changed":False,"calendar_changed":True}

    # (I) Fallback IA — adaptation libre
    if st.session_state.api_key:
        if not st.session_state.plan_text:
            _regenerate_plan_if_needed()
        result = ai_edit_plan(st.session_state.api_key, text, st.session_state.plan_text, st.session_state.answers)
        if result.get("ok"):
            st.session_state.plan_text = result["new_plan"]
            st.session_state.flash_plan_updated = True
            st.session_state._last_plan_hash = hash(st.session_state.plan_text)
            recompute_calendar_events()
            return {"feedback": f"🧠 J’ai adapté le plan automatiquement.\n\n**Résumé** — {result.get('summary','(modifications appliquées)')}",
                    "plan_changed": True, "calendar_changed": True}
        else:
            return {"feedback": f"⚠️ Je n’ai pas pu adapter automatiquement le plan. {result.get('summary','')}",
                    "plan_changed": False, "calendar_changed": False}

    return {"feedback":"Pour que j’adapte le plan automatiquement, ajoute une clé OpenAI dans la barre latérale.",
            "plan_changed":False, "calendar_changed":False}

# ===================== UI HELPERS =====================
def space(h=12):
    st.markdown(f"<div style='height:{h}px'></div>", unsafe_allow_html=True)

# ===================== VUES =====================
def view_landing():
    st.title("Serge est là pour vous coacher !")
    st.write("Votre plan personnalisé, conçu à partir de votre profil.")
    if st.button("Débutez votre programme", use_container_width=True, key="landing_start_btn"):
        st.session_state.step = "form"; st.rerun()

def render_input(q, default=None):
    t = q["type"]; label = q["label"]
    if t=="text":
        return st.text_input(label, value=default or "", key=f"in_{q['key']}")
    if t=="number":
        base = q.get("min", 0)
        val = base if default in (None, "") else int(default)
        return st.number_input(label, min_value=q.get("min",0), max_value=q.get("max",999), value=val, key=f"in_{q['key']}")
    if t=="select":
        opts = q["options"]; idx = opts.index(default) if default in opts else 0
        return st.selectbox(label, opts, index=idx, key=f"in_{q['key']}")
    if t=="multiselect":
        opts = q["options"]; default = default or []
        return st.multiselect(label, opts, default=default, key=f"in_{q['key']}")
    if t=="slider":
        return st.slider(label, q["min"], q["max"], value=default if default is not None else q["min"], step=q.get("step",1), key=f"in_{q['key']}")
    return st.text_input(label, value=default or "", key=f"in_{q['key']}")

def view_form():
    st.markdown("### Questionnaire — profil sportif")
    q_i = st.session_state.q_index
    pct = int((q_i+1)/TOTAL_Q*100)
    st.progress(pct/100.0, text=f"Question {q_i+1} / {TOTAL_Q}")

    q = QUESTIONS[q_i]
    prev_val = st.session_state.answers.get(q["key"], None)
    ans = render_input(q, default=prev_val)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅️ Précédent", disabled=(q_i==0), use_container_width=True, key=f"form_prev_{q_i}"):
            st.session_state.answers[q["key"]] = ans
            st.session_state.q_index = max(0, q_i-1); st.rerun()
    with c2:
        if q_i < TOTAL_Q-1:
            if st.button("Suivant ➡️", use_container_width=True, key=f"form_next_{q_i}"):
                st.session_state.answers[q["key"]] = ans
                st.session_state.q_index = min(TOTAL_Q-1, q_i+1); st.rerun()
        else:
            if st.button("✅ Générer mon plan", use_container_width=True, key="form_generate_plan"):
                st.session_state.answers[q["key"]] = ans
                a = st.session_state.answers
                profile = {
                    "age": a.get("age"), "sexe": a.get("sexe"), "taille_cm": a.get("taille_cm"),
                    "poids_kg": a.get("poids_kg"), "niveau_exp": a.get("niveau_exp"),
                    "blessures": a.get("blessures"), "sante": a.get("sante"),
                    "activite": a.get("activite"), "objectif_principal": a.get("objectif_principal"),
                    "objectif_secondaire": a.get("objectif_secondaire"), "horizon": a.get("horizon"),
                    "motivation": a.get("motivation"), "types_exos": a.get("types_exos"),
                    "jours_sem": a.get("jours_sem"), "duree_min": a.get("duree_min"),
                    "moment": a.get("moment"), "lieu": a.get("lieu"),
                    "materiel": a.get("materiel"), "sommeil_h": a.get("sommeil_h"),
                    "ville": a.get("ville"), "nutrition": a.get("nutrition")
                }
                plan_text = call_openai_plan(st.session_state.api_key, profile) if st.session_state.api_key else ""
                st.session_state.plan_text = plan_text or fallback_plan(profile)
                st.session_state._last_plan_hash = hash(st.session_state.plan_text)
                recompute_calendar_events()
                st.session_state.step = "dashboard"
                st.session_state.active_card = None
                st.rerun()

# ===================== PAGES INDIVIDUELLES =====================
def page_plan():
    col_menu, col_content = st.columns([1, 4])

    with col_menu:
        st.markdown("### 📊 Menu"); st.markdown("---")
        if st.button("🏠 Dashboard", key="menu_plan_home", use_container_width=True): 
            st.session_state.page=None; st.rerun()
        st.button("📋 Plan", key="menu_plan_plan", use_container_width=True, disabled=True)
        if st.button("🌤️ Météo", key="menu_plan_meteo", use_container_width=True): 
            st.session_state.page="meteo"; st.rerun()
        if st.button("💬 Chat", key="menu_plan_chat", use_container_width=True): 
            st.session_state.page="chat"; st.rerun()
        if st.button("📅 Calendrier", key="menu_plan_calendar", use_container_width=True): 
            st.session_state.page="calendar"; st.rerun()
        if st.button("🍎 Nutrition", key="menu_plan_nutri", use_container_width=True): 
            st.session_state.page="nutrition"; st.rerun()
        st.markdown("---")
        if st.button("↺ Refaire", key="menu_plan_reset", use_container_width=True):
            st.session_state.step = "form"; st.session_state.q_index = 0; st.session_state.page = None; st.rerun()

    with col_content:
        st.markdown("## 📋 Plan d'entraînement"); st.divider()

        # Barre d’actions
        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button("✏️ Modifier", use_container_width=True, key="plan_edit_btn"):
                st.session_state.plan_edit_mode = not st.session_state.plan_edit_mode
                st.rerun()
        with a2:
            if st.button("🔄 Régénérer (profil)", use_container_width=True, key="plan_regen_btn"):
                _regenerate_plan_if_needed()
                st.success("✅ Plan régénéré à partir du profil.")
                st.rerun()
        with a3:
            st.download_button(
                "💾 Télécharger", 
                data=st.session_state.plan_text or "", 
                file_name="plan_entrainement.md",
                mime="text/markdown",
                key="plan_download_btn",
                use_container_width=True
            )

        st.divider()

        # Affichage / édition
        if st.session_state.plan_edit_mode:
            edited = st.text_area(
                "Plan (Markdown)", 
                value=st.session_state.plan_text or "", 
                height=500, 
                key="plan_edit_area"
            )
            b1, b2 = st.columns(2)
            with b1:
                if st.button("💾 Enregistrer", use_container_width=True, key="plan_save_btn"):
                    st.session_state.plan_text = edited
                    st.session_state._last_plan_hash = hash(st.session_state.plan_text or "")
                    recompute_calendar_events()   # << important
                    st.session_state.plan_edit_mode = False
                    st.success("✅ Plan sauvegardé et calendrier mis à jour.")
                    st.rerun()
            with b2:
                if st.button("❌ Annuler", use_container_width=True, key="plan_cancel_btn"):
                    st.session_state.plan_edit_mode = False
                    st.rerun()
        else:
            st.markdown(st.session_state.plan_text or "_Pas de plan._")

        # Synchronise si plan modifié par ailleurs (ex: chat)
        current_hash = hash(st.session_state.plan_text or "")
        if st.session_state.get("_last_plan_hash") != current_hash:
            st.session_state._last_plan_hash = current_hash
            recompute_calendar_events()

def page_meteo():
    col_menu, col_content = st.columns([1, 4])
    with col_menu:
        st.markdown("### 📊 Menu"); st.markdown("---")
        if st.button("🏠 Dashboard", key="menu_met_home", use_container_width=True): st.session_state.page=None; st.rerun()
        if st.button("📋 Plan", key="menu_met_plan", use_container_width=True): st.session_state.page="plan"; st.rerun()
        st.button("🌤️ Météo", key="menu_met_meteo", use_container_width=True, disabled=True)
        if st.button("💬 Chat", key="menu_met_chat", use_container_width=True): st.session_state.page="chat"; st.rerun()
        if st.button("📅 Calendrier", key="menu_met_calendar", use_container_width=True): st.session_state.page="calendar"; st.rerun()
        if st.button("🍎 Nutrition", key="menu_met_nutri", use_container_width=True): st.session_state.page="nutrition"; st.rerun()
        st.markdown("---")
        if st.button("↺ Refaire", key="menu_met_reset", use_container_width=True):
            st.session_state.step = "form"; st.session_state.q_index = 0; st.session_state.page = None; st.rerun()
    with col_content:
        st.markdown("## 🌤️ Météo"); st.divider()
        ville = st.session_state.answers.get("ville", "Montréal")
        duree = int(st.session_state.answers.get("duree_min", 30) or 30)
        result = geocode_city(ville)
        if result:
            lat, lon, ville_complete = result
            st.markdown(f"**📍 {ville_complete}**")
            weather_data = get_today_weather(lat, lon)
            if weather_data:
                try:
                    temp = weather_data["hourly"]["temperature_2m"][0]
                    prec = weather_data["hourly"]["precipitation_probability"][0]
                    col1, col2 = st.columns(2)
                    col1.metric("🌡️ Température", f"{temp}°C")
                    col2.metric("💧 Pluie", f"{prec}%")
                    st.divider()
                    st.info(weather_advice(weather_data, duree))
                except:
                    st.warning("Erreur données météo")
            else:
                st.warning("Météo indisponible")
        else:
            st.error(f"Ville '{ville}' introuvable")

def page_chat():
    col_menu, col_content = st.columns([1, 4])

    with col_menu:
        st.markdown("### 📊 Menu"); st.markdown("---")
        if st.button("🏠 Dashboard", key="menu_chat_home", use_container_width=True): st.session_state.page=None; st.rerun()
        if st.button("📋 Plan", key="menu_chat_plan", use_container_width=True): st.session_state.page="plan"; st.rerun()
        if st.button("🌤️ Météo", key="menu_chat_meteo", use_container_width=True): st.session_state.page="meteo"; st.rerun()
        st.button("💬 Chat", key="menu_chat_chat", use_container_width=True, disabled=True)
        if st.button("📅 Calendrier", key="menu_chat_calendar", use_container_width=True): st.session_state.page="calendar"; st.rerun()
        if st.button("🍎 Nutrition", key="menu_chat_nutri", use_container_width=True): st.session_state.page="nutrition"; st.rerun()
        if st.button("📊 Mes entraînements", key="menu_chat_workouts", use_container_width=True): st.session_state.page="workouts"; st.rerun()
        st.markdown("---")
        if st.button("↺ Refaire", key="menu_chat_reset", use_container_width=True):
            st.session_state.step="form"; st.session_state.q_index=0; st.session_state.page=None; st.rerun()

    with col_content:
        st.markdown("## 💬 Chat Coach")
        st.caption("Exemples: « adapte le plan pour plus de course et moins de HIIT », "
                   "« remplace au jour 1 treadmill par course en plein air », "
                   "« mets mes séances le matin », "
                   "« active les rappels J1, J3, J5 », "
                   "« date de début du programme 2025-11-05 »")
        st.divider()

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Parle à Serge…")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            result = handle_chat_command(user_input)
            feedback = result["feedback"].strip()
            plan_changed = result["plan_changed"]
            cal_changed  = result["calendar_changed"]

            if feedback:
                st.session_state.chat_history.append({"role":"assistant","content":feedback})

            if st.session_state.api_key and not feedback:
                model_reply = call_openai_chat(st.session_state.api_key, user_input, st.session_state.answers)
                st.session_state.chat_history.append({"role":"assistant","content":model_reply})
            elif not feedback:
                st.session_state.chat_history.append({"role":"assistant","content":"🙂 C'est noté."})

            if plan_changed:
                st.session_state.page = "plan"
            elif cal_changed:
                st.session_state.page = "calendar"

            st.rerun()

        cols = st.columns(3)
        with cols[0]:
            if st.button("🧹 Effacer la conversation", use_container_width=True, key="chat_clear_btn"):
                st.session_state.chat_history = []; st.rerun()
        with cols[1]:
            if st.button("🔄 Régénérer le plan", use_container_width=True, key="chat_regen_btn"):
                _regenerate_plan_if_needed()
                st.session_state.chat_history.append({"role":"assistant","content":"🔄 Plan régénéré. Ouverture de l’onglet **Plan**."})
                st.session_state.page="plan"; st.rerun()
        with cols[2]:
            if st.button("📅 Ouvrir Calendrier", use_container_width=True, key="chat_open_cal_btn"):
                st.session_state.page="calendar"; st.rerun()

def page_calendar():
    col_menu, col_content = st.columns([1, 4])
    with col_menu:
        st.markdown("### 📊 Menu"); st.markdown("---")
        if st.button("🏠 Dashboard", key="menu_cal_home", use_container_width=True): 
            st.session_state.page=None; st.rerun()
        if st.button("📋 Plan", key="menu_cal_plan", use_container_width=True): 
            st.session_state.page="plan"; st.rerun()
        if st.button("🌤️ Météo", key="menu_cal_meteo", use_container_width=True): 
            st.session_state.page="meteo"; st.rerun()
        st.button("📅 Calendrier", key="menu_cal_calendar", use_container_width=True, disabled=True)
        if st.button("💬 Chat", key="menu_cal_chat", use_container_width=True): 
            st.session_state.page="chat"; st.rerun()
        if st.button("🍎 Nutrition", key="menu_cal_nutri", use_container_width=True): 
            st.session_state.page="nutrition"; st.rerun()
        st.markdown("---")
        if st.button("↺ Refaire", key="menu_cal_reset", use_container_width=True):
            st.session_state.step="form"; st.session_state.q_index=0; st.session_state.page=None; st.rerun()

    with col_content:
        st.markdown("## 📅 Calendrier"); st.divider()

        picked = st.date_input(
            "Date de début du programme",
            value=st.session_state.get("calendar_start_date", dt.date.today()),
            key="cal_start_input"
        )
        if picked != st.session_state.get("calendar_start_date"):
            st.session_state.calendar_start_date = picked
            recompute_calendar_events()

        plan_hash = hash(st.session_state.get("plan_text",""))
        if st.session_state.get("_last_plan_hash") != plan_hash:
            st.session_state["_last_plan_hash"] = plan_hash
            recompute_calendar_events()

        events = st.session_state.get("calendar_events", [])
        if not events:
            st.warning("Aucune séance détectée dans le plan. Va dans l’onglet **Plan** pour le générer (ou via le chat).")
            return

        if CALENDAR_AVAILABLE:
            calendar_options = {
                "initialView": "dayGridMonth",
                "headerToolbar": {
                    "left":"prev,next today",
                    "center":"title",
                    "right":"dayGridMonth,timeGridWeek,listWeek"
                },
                "height": 600,
                "dayMaxEvents": 2
            }
            custom_css = ".fc-daygrid-event{white-space:normal!important;}"
            st_calendar(events=events, options=calendar_options, custom_css=custom_css, key="cal_widget_live")
        else:
            st.info("`streamlit-calendar` non installé — affichage en tableau simple.")
            import pandas as pd
            tbl = []
            for e in events:
                tbl.append({
                    "Date": e["start"][:10],
                    "Heure": e["start"][11:16] + " → " + e["end"][11:16],
                    "Titre": e["title"]
                })
            st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True)

def page_nutrition():
    col_menu, col_content = st.columns([1, 4])
    with col_menu:
        st.markdown("### 📊 Menu"); st.markdown("---")
        if st.button("🏠 Dashboard", key="menu_nut_home", use_container_width=True): st.session_state.page=None; st.rerun()
        if st.button("📋 Plan", key="menu_nut_plan", use_container_width=True): st.session_state.page="plan"; st.rerun()
        if st.button("🌤️ Météo", key="menu_nut_meteo", use_container_width=True): st.session_state.page="meteo"; st.rerun()
        if st.button("💬 Chat", key="menu_nut_chat", use_container_width=True): st.session_state.page="chat"; st.rerun()
        if st.button("📅 Calendrier", key="menu_nut_calendar", use_container_width=True): st.session_state.page="calendar"; st.rerun()
        st.button("🍎 Nutrition", key="menu_nut_nutri", use_container_width=True, disabled=True)
        st.markdown("---")
        if st.button("↺ Refaire", key="menu_nut_reset", use_container_width=True):
            st.session_state.step="form"; st.session_state.q_index=0; st.session_state.page=None; st.rerun()
    with col_content:
        st.markdown("## 🍎 Nutrition"); st.divider()
        if st.session_state.nutrition_plan is None:
            with st.spinner("Génération du plan nutrition..."):
                if st.session_state.api_key:
                    txt = call_openai_nutrition(st.session_state.api_key, st.session_state.answers)
                else:
                    txt = fallback_nutrition(st.session_state.answers)
                st.session_state.nutrition_plan = txt

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✏️ Modifier", use_container_width=True, key="nut_edit_btn"):
                st.session_state.nutrition_edit_mode = not st.session_state.nutrition_edit_mode; st.rerun()
        with c2:
            if st.button("🔄 Régénérer", use_container_width=True, key="nut_regen_btn"):
                with st.spinner("Régénération..."):
                    if st.session_state.api_key:
                        txt = call_openai_nutrition(st.session_state.api_key, st.session_state.answers)
                    else:
                        txt = fallback_nutrition(st.session_state.answers)
                    st.session_state.nutrition_plan = txt
                    st.session_state.nutrition_edit_mode = False
                st.rerun()
        with c3:
            st.download_button("💾 Télécharger", data=st.session_state.nutrition_plan, file_name="plan_nutrition.txt", mime="text/plain", key="nut_download_btn", use_container_width=True)

        st.divider()
        if st.session_state.nutrition_edit_mode:
            st.info("✏️ Mode édition - Modifie ton plan ci-dessous")
            edited = st.text_area("Plan nutrition", value=st.session_state.nutrition_plan, height=400, key="nut_edit_area")
            csa, cca = st.columns(2)
            with csa:
                if st.button("💾 Enregistrer", use_container_width=True, key="nut_save_btn"):
                    st.session_state.nutrition_plan = edited
                    st.session_state.nutrition_edit_mode = False
                    st.success("✅ Plan sauvegardé!")
                    st.rerun()
            with cca:
                if st.button("❌ Annuler", use_container_width=True, key="nut_cancel_btn"):
                    st.session_state.nutrition_edit_mode = False
                    st.rerun()
        else:
            st.markdown(st.session_state.nutrition_plan)

        space(1)
        with st.expander("💡 Conseils nutritionnels"):
            st.markdown("""
**🥗 Principes de base**
- Hydratation: 2-3L d'eau / jour
- 5 portions de fruits/légumes
- Protéines à chaque repas
- Limiter les sucres ajoutés

**⏰ Timing**
- Collation pré-entrainement 1-2h avant
- Collation post-entrainement dans les 30 min
- Dernier repas 2-3h avant le coucher
""")

def page_workouts():
    col_menu, col_content = st.columns([1, 4])
    with col_menu:
        st.markdown("### 📊 Menu"); st.markdown("---")
        if st.button("🏠 Dashboard", key="menu_wo_home", use_container_width=True): st.session_state.page=None; st.rerun()
        if st.button("📋 Plan", key="menu_wo_plan", use_container_width=True): st.session_state.page="plan"; st.rerun()
        if st.button("🌤️ Météo", key="menu_wo_meteo", use_container_width=True): st.session_state.page="meteo"; st.rerun()
        if st.button("💬 Chat", key="menu_wo_chat", use_container_width=True): st.session_state.page="chat"; st.rerun()
        if st.button("📅 Calendrier", key="menu_wo_calendar", use_container_width=True): st.session_state.page="calendar"; st.rerun()
        if st.button("🍎 Nutrition", key="menu_wo_nutri", use_container_width=True): st.session_state.page="nutrition"; st.rerun()
        st.button("📊 Mes entraînements", key="menu_wo_workouts", use_container_width=True, disabled=True)
        st.markdown("---")
        if st.button("↺ Refaire", key="menu_wo_reset", use_container_width=True):
            st.session_state.step="form"; st.session_state.q_index=0; st.session_state.page=None; st.rerun()
    with col_content:
        st.markdown("## 📊 Mes entraînements"); st.divider()

        tab1, tab2 = st.tabs(["➕ Enregistrer", "📈 Statistiques"])
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                w_date = st.date_input("📅 Date", value=dt.date.today(), key="wo_date")
                w_type = st.selectbox("🏋️ Type", ["Musculation","Cardio","HIIT","Yoga","Étirements","Sport (autre)"], key="wo_type")
                w_dur  = st.number_input("⏱️ Durée (min)", min_value=1, max_value=300, value=45, key="wo_dur")
            with col2:
                w_int = st.select_slider("💪 Intensité", options=["Légère","Modérée","Élevée","Maximale"], value="Modérée", key="wo_int")
                w_feel= st.select_slider("😊 Ressenti", options=["😫 Difficile","😐 Moyen","😊 Bien","🤩 Excellent"], value="😊 Bien", key="wo_feel")
                w_cal = st.number_input("🔥 Calories (est.)", min_value=0, max_value=2000, value=300, key="wo_cal")
            w_notes = st.text_area("📝 Notes", placeholder="Exercices effectués, observations...", key="wo_notes", height=100)
            if st.button("💾 Enregistrer l'entraînement", use_container_width=True, key="wo_save"):
                st.session_state.workout_history.append({
                    "date": w_date.strftime("%Y-%m-%d"),
                    "type": w_type, "duration": w_dur, "intensity": w_int,
                    "feeling": w_feel, "calories": w_cal, "notes": w_notes
                })
                st.success("✅ Entraînement enregistré!"); st.rerun()

        with tab2:
            import pandas as pd
            if len(st.session_state.workout_history)==0:
                st.info("📊 Aucun entraînement enregistré.")
            else:
                total = len(st.session_state.workout_history)
                total_dur = sum(w["duration"] for w in st.session_state.workout_history)
                total_cal = sum(w["calories"] for w in st.session_state.workout_history)
                avg_dur = total_dur/total
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("🏋️ Entraînements", total)
                c2.metric("⏱️ Temps total", f"{total_dur} min")
                c3.metric("📊 Durée moyenne", f"{int(avg_dur)} min")
                c4.metric("🔥 Calories totales", total_cal)
                st.divider()
                df = pd.DataFrame(st.session_state.workout_history)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
                st.markdown("#### 📊 Durée des entraînements")
                st.line_chart(df.set_index("date")[["duration"]], use_container_width=True)
                st.markdown("#### 🏋️ Répartition par type")
                st.bar_chart(df["type"].value_counts(), use_container_width=True)
                st.markdown("#### 🔥 Calories brûlées par séance")
                st.area_chart(df.set_index("date")[["calories"]], use_container_width=True)
                st.divider()
                st.markdown("#### 📋 Historique")
                for i, workout in enumerate(reversed(st.session_state.workout_history)):
                    with st.expander(f"{workout['date']} - {workout['type']} ({workout['duration']} min)"):
                        ca, cb = st.columns(2)
                        with ca:
                            st.write(f"**Intensité:** {workout['intensity']}")
                            st.write(f"**Ressenti:** {workout['feeling']}")
                        with cb:
                            st.write(f"**Calories:** {workout['calories']} kcal")
                            if workout['notes']: st.write(f"**Notes:** {workout['notes']}")
                        if st.button("🗑️ Supprimer", key=f"wo_del_{len(st.session_state.workout_history)-i-1}"):
                            st.session_state.workout_history.pop(len(st.session_state.workout_history)-i-1); st.rerun()
                st.divider()
                if st.button("📥 Télécharger CSV", use_container_width=True, key="wo_download_btn"):
                    csv = df.to_csv(index=False)
                    st.download_button("📥 Télécharger le fichier CSV", data=csv, file_name="mes_entrainements.csv", mime="text/csv", key="wo_download_real")

def show_statistics_dashboard():
    st.markdown("## 📊 Tableau de bord"); st.markdown("---")
    a = st.session_state.answers
    st.markdown("### 👤 Profil")
    c1,c2,c3,c4 = st.columns(4)
    age = a.get("age","N/A"); poids = a.get("poids_kg","N/A"); taille = a.get("taille_cm","N/A")
    c1.metric("Âge", f"{age} ans" if age!="N/A" else "N/A")
    c2.metric("Poids", f"{poids} kg" if poids!="N/A" else "N/A")
    if poids!="N/A" and taille!="N/A" and poids and taille:
        try: imc = round(float(poids)/((float(taille)/100)**2),1)
        except: imc = "N/A"
    else: imc="N/A"
    c3.metric("Taille", f"{taille} cm" if taille!="N/A" else "N/A")
    c4.metric("IMC", f"{imc}")
    space(1)
    st.markdown("### 🎯 Objectifs")
    c1,c2 = st.columns(2)
    c1.info(f"**Objectif:** {a.get('objectif_principal','N/A')}")
    c2.info(f"**Horizon:** {a.get('horizon','N/A')}")
    space(1)
    st.markdown("### 🏋️ Plan")
    c1,c2,c3 = st.columns(3)
    c1.metric("Jours/sem", a.get("jours_sem","N/A"))
    dur = a.get("duree_min","N/A")
    c2.metric("Durée/séance", f"{dur} min" if dur!="N/A" else "N/A")
    c3.metric("Niveau", a.get("niveau_exp","N/A"))
    space(2)
    st.markdown("### ⚡ Actions rapides")
    c1,c2,c3 = st.columns(3)
    if c1.button("📋 Plan", key="qa_plan_btn", use_container_width=True):
        st.session_state.page="plan"; st.rerun()
    if c2.button("💬 Chat", key="qa_chat_btn", use_container_width=True):
        st.session_state.page="chat"; st.rerun()
    if c3.button("📅 Calendrier", key="qa_calendar_btn", use_container_width=True):
        st.session_state.page="calendar"; st.rerun()

def view_dashboard_new():
    col_menu, col_content = st.columns([1, 4])
    with col_menu:
        st.markdown("### 📊 Menu"); st.markdown("---")
        if st.button("📋 Plan",   key="menu_plan_btn",   use_container_width=True):
            st.session_state.page = "plan";      st.rerun()
        if st.button("🌤️ Météo", key="menu_meteo_btn",  use_container_width=True):
            st.session_state.page = "meteo";     st.rerun()
        if st.button("💬 Chat",   key="menu_chat_btn",   use_container_width=True):
            st.session_state.page = "chat";      st.rerun()
        if st.button("📅 Calendrier", key="menu_calendar_btn", use_container_width=True):
            st.session_state.page = "calendar";  st.rerun()
        if st.button("🍎 Nutrition",  key="menu_nutrition_btn", use_container_width=True):
            st.session_state.page = "nutrition"; st.rerun()
        if st.button("📊 Mes entraînements", key="menu_workouts_btn", use_container_width=True):
            st.session_state.page = "workouts";  st.rerun()
        st.markdown("---")
        if st.button("↺ Refaire", key="menu_reset_btn", use_container_width=True):
            st.session_state.step = "form"; st.session_state.q_index = 0; st.session_state.page = None; st.rerun()
    with col_content:
        show_statistics_dashboard()

# ===================== DEBUG AIDE =====================
DEBUG = True
def _debug_ping():
    st.sidebar.markdown("✅ App chargée")
    st.sidebar.markdown(f"Step: `{st.session_state.get('step')}`  | Page: `{st.session_state.get('page')}`")
if DEBUG:
    _debug_ping()

# ===================== ROUTAGE =====================
try:
    if st.session_state.step == "landing":
        view_landing()
    elif st.session_state.step == "form":
        view_form()
    elif st.session_state.step == "dashboard":
        page = st.session_state.get("page", None)
        if page == "plan":
            page_plan()
        elif page == "meteo":
            page_meteo()
        elif page == "chat":
            page_chat()
        elif page == "calendar":
            page_calendar()
        elif page == "nutrition":
            page_nutrition()
        elif page == "workouts":
            page_workouts()
        else:
            view_dashboard_new()
    else:
        st.session_state.step = "landing"
        view_landing()
except Exception as e:
    st.error("❌ Une exception a été levée pendant le rendu.")
    st.exception(e)
