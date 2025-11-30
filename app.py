# -*- coding: utf-8 -*-
"""
LP9 - Coach IA Serge - VERSION AMÉLIORÉE
Modifications:
- Boutons du formulaire plus visibles
- Suppression du taux de complétion
- Suppression de la météo en double (une seule section)
- Suppression du bouton "Modifier mon profil"
- Champs de formulaire plus hauts pour meilleure lisibilité
- Correction mise à jour "Prochain entraînement" après enregistrement
- Météo corrigée (Open-Meteo)
- Respect du nombre de séances/semaine dans le plan IA
- Chatbot capable de proposer/appliquer des remplacements dans le plan
- Plan nutritionnel sur 7 jours complets
"""

import os
import re
import json
import requests
import datetime as dt
import streamlit as st
from streamlit.components.v1 import html
import logging

# ===================== CONFIGURATION LOGGING =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('coach_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===================== OPENAI KEY HELPER =====================
def get_initial_api_key() -> str:
    """
    Récupère la clé OpenAI dans cet ordre :
    1) st.secrets["OPENAI_API_KEY"] (Streamlit Cloud / .streamlit/secrets.toml)
    2) Variable d'environnement OPENAI_API_KEY
    """
    key = ""

    # 1) Secrets Streamlit (Cloud ou secrets.toml local)
    try:
        if "OPENAI_API_KEY" in st.secrets:
            key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        # st.secrets peut ne pas exister en local si non configuré
        pass

    # 2) Fallback sur l'environnement
    if not key:
        key = os.getenv("OPENAI_API_KEY", "")

    return key

# ===================== PAGE CONFIG =====================
st.set_page_config(
    page_title="Coach IA – Serge Pro Edition",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== STYLE CSS MODERNE =====================
st.markdown("""
<style>
    /* Reset & Base */
    * {
        box-sizing: border-box;
    }
    
    .main > div {
        padding-top: 2rem;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1e1e1e;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #3ea6ff;
        border-radius: 4px;
    }
    
    /* Typography */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* Cards */
    .custom-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
    }
    
    .custom-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 4px solid #3ea6ff;
    }
    
    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #3ea6ff;
        margin: 0;
    }
    
    .stat-label {
        font-size: 0.875rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Weather Card */
    .weather-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .weather-temp {
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
    }
    
    .weather-condition {
        font-size: 1.25rem;
        opacity: 0.9;
    }
    
    /* Quote Card */
    .quote-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        font-style: italic;
        font-size: 1.125rem;
        line-height: 1.6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Buttons - FORMULAIRE PLUS VISIBLE */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #3ea6ff 0%, #667eea 100%);
        color: white;
        border: 3px solid #2d8dd9;
        padding: 1rem 2rem;
        font-size: 1.25rem;
        font-weight: 700;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 6px 12px rgba(62, 166, 255, 0.4);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2d8dd9 0%, #5568d3 100%);
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(62, 166, 255, 0.6);
        border-color: #1e6bb8;
    }
    
    .stButton > button:active {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(62, 166, 255, 0.4);
    }
    
    /* Progress bars */
    .stProgress > div > div {
        background: linear-gradient(90deg, #3ea6ff 0%, #667eea 100%);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        background-color: #f0f2f6;
        border-radius: 8px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3ea6ff 0%, #667eea 100%);
        color: white;
    }
    
    /* Inputs - HAUTEUR AUGMENTÉE POUR LISIBILITÉ */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 1rem 0.75rem;
        font-size: 1.1rem;
        min-height: 50px;
    }
    
    .stSelectbox > div > div > div {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 0.75rem;
        font-size: 1.1rem;
        min-height: 50px;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #3ea6ff;
        box-shadow: 0 0 0 1px #3ea6ff;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Alerts */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
    }
    
    /* Chat messages */
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        max-width: 80%;
    }
    
    .user-message {
        background: #e3f2fd;
        margin-left: auto;
        text-align: right;
    }
    
    .assistant-message {
        background: #f5f5f5;
        margin-right: auto;
    }
    
    /* Calendar */
    .calendar-event {
        background: #3ea6ff;
        color: white;
        padding: 0.5rem;
        border-radius: 6px;
        margin: 0.25rem 0;
        font-size: 0.875rem;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .stat-number {
            font-size: 2rem;
        }
        
        .weather-temp {
            font-size: 2rem;
        }
        
        .quote-card {
            font-size: 1rem;
            padding: 1.5rem;
        }
    }
    
    /* Landing page */
    .landing-title {
        font-size: 4rem;
        font-weight: 900;
        background: linear-gradient(135deg, #3ea6ff 0%, #667eea 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .landing-subtitle {
        font-size: 1.5rem;
        color: #ccc;
        text-align: center;
        margin-bottom: 3rem;
    }
    
    /* Form navigation */
    .form-progress {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 2rem;
    }
    
    .form-progress-bar {
        background: #e0e0e0;
        height: 8px;
        border-radius: 4px;
        overflow: hidden;
    }
    
    .form-progress-fill {
        background: linear-gradient(90deg, #3ea6ff 0%, #667eea 100%);
        height: 100%;
        transition: width 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# ===================== STATE INITIALIZATION =====================
def _init_state():
    """Initialise l'état de session avec valeurs par défaut"""
    defaults = {
        # Navigation
        "step": "landing",
        "q_index": 0,
        "answers": {},
        "page": None,
        
        # Plans et contenu
        "plan_text": "",
        "plan_edit_mode": False,
        "nutrition_plan": None,
        "nutrition_edit_mode": False,
        
        # API (clé lue via secrets/env ou overridée via la sidebar)
        "api_key": get_initial_api_key(),
        
        # Profil
        "user_name": "Athlète",
        "user_email": "",
        "user_dob": dt.date.today(),
        "user_gender": "Homme",
        "city": "Montreal",
        "country": "Canada",
        "user_bio": "",
        "avatar_url": "",
        
        # Objectifs
        "goal_type": "Maintien",
        "current_weight": 70.0,
        "target_weight": 65.0,
        "training_frequency": 3,
        "training_duration": 45,
        "target_date": dt.date.today() + dt.timedelta(days=90),
        
        # Params
        "notifications_enabled": True,
        "notification_time": dt.time(8, 0),
        "weight_unit": "Kilogrammes (kg)",
        "distance_unit": "Kilomètres (km)",
        "language": "Français",
        
        # History
        "completed_workouts": [],
        "chat_messages": [{
            "role": "system",
            "content": (
                "Tu es Serge, un coach sportif professionnel certifié. "
                "Tu aides les utilisateurs avec leurs questions sur l'entraînement, "
                "la nutrition, la récupération et la motivation. Réponds de façon "
                "concise, encourageante et professionnelle."
            )
        }],
        "chat_history": [],
        
        # WhatsApp
        "whatsapp_phone_number_id": "",
        "whatsapp_access_token": "",
        "whatsapp_api_version": "v18.0",
        "recipient_phone": "",
        "reminder_days": [1, 3, 5],
        "message_template_name": "reminder_workout",
        
        # Calendrier
        "calendar_start_date": dt.date.today(),
        "calendar_events": [],
        "_last_plan_hash": None,
        
        # Workout history
        "workout_history": [],
        
        # État visuel
        "flash_plan_updated": False,
        "active_card": None,
        
        # Dernière séance complétée
        "last_completed_day": None,

        # Modification de plan en attente (via chat)
        "pending_plan_change": None,
    }
    
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
            logger.debug(f"Initialized state: {k}")

_init_state()


# ===================== WHATSAPP FUNCTIONS =====================
def send_whatsapp_text_message(to_number: str, message: str) -> bool:
    """Envoie un message texte via WhatsApp Business API"""
    try:
        phone_id = st.session_state.whatsapp_phone_number_id
        token = st.session_state.whatsapp_access_token
        version = st.session_state.whatsapp_api_version
        
        if not phone_id or not token:
            logger.warning("WhatsApp credentials missing")
            st.error("⚠️ Identifiants WhatsApp Business API manquants")
            return False
        
        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"preview_url": False, "body": message}
        }
        
        logger.info(f"Sending WhatsApp message to {to_number[:4]}***")
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
        
        if response.status_code == 200:
            logger.info("WhatsApp message sent successfully")
            return True
        else:
            logger.error(f"WhatsApp API error: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("WhatsApp API timeout")
        st.error("❌ Timeout lors de l'envoi WhatsApp")
        return False
    except Exception as e:
        logger.error(f"WhatsApp error: {str(e)}", exc_info=True)
        st.error(f"❌ Erreur WhatsApp: {str(e)}")
        return False

def send_whatsapp_template_message(to_number: str, template_name: str, template_params: list = None) -> bool:
    """Envoie un message template via WhatsApp"""
    try:
        phone_id = st.session_state.whatsapp_phone_number_id
        token = st.session_state.whatsapp_access_token
        version = st.session_state.whatsapp_api_version
        
        if not phone_id or not token:
            st.error("⚠️ Identifiants WhatsApp manquants")
            return False
        
        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        components = []
        if template_params:
            parameters = [{"type": "text", "text": str(param)} for param in template_params]
            components.append({"type": "body", "parameters": parameters})
        
        data = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "fr"},
                "components": components
            }
        }
        
        logger.info(f"Sending WhatsApp template '{template_name}'")
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"WhatsApp template error: {str(e)}")
        st.error(f"❌ Erreur: {str(e)}")
        return False

def validate_phone_number(phone: str) -> bool:
    """Valide un numéro de téléphone"""
    if not phone or not phone.isdigit():
        return False
    return 10 <= len(phone) <= 15

# ===================== SIDEBAR NAVIGATION =====================
with st.sidebar:
    st.title("🏋️ Coach Serge Pro")
    st.markdown("---")
    
    # API Configuration
    st.subheader("🔧 Configuration OpenAI")
    
    api_key_input = st.text_input(
        "Clé API OpenAI",
        value=st.session_state.api_key,
        type="password",
        help="Colle ici ta clé OpenAI (ne sera pas affichée en clair)",
        key="sidebar_openai_key"
    )

    if api_key_input:
        if not api_key_input.startswith("sk-"):
            st.warning("⚠️ Format de clé invalide")
        else:
            st.session_state.api_key = api_key_input
            st.success("✅ Clé API configurée")
            logger.info("API key configured")
    else:
        if st.session_state.api_key:
            st.success("✅ Clé API chargée depuis l'environnement")
        else:
            st.info("Ajoute ta clé API OpenAI pour activer l'IA.")
    
    st.markdown("---")
    
    # WhatsApp Section
    st.subheader("📱 Notifications WhatsApp")
    
    with st.expander("⚙️ Configuration WhatsApp API", expanded=False):
        st.info("Configure ton compte WhatsApp Business API")
        
        phone_id = st.text_input(
            "Phone Number ID",
            value=st.session_state.whatsapp_phone_number_id,
            type="password",
            key="sidebar_wa_phone"
        )
        
        access_token = st.text_input(
            "Access Token",
            value=st.session_state.whatsapp_access_token,
            type="password",
            key="sidebar_wa_token"
        )
        
        api_version = st.text_input(
            "API Version",
            value=st.session_state.whatsapp_api_version,
            key="sidebar_wa_version"
        )
        
        template_name = st.text_input(
            "Template de rappel",
            value=st.session_state.message_template_name,
            key="sidebar_wa_template"
        )
        
        st.session_state.whatsapp_phone_number_id = phone_id
        st.session_state.whatsapp_access_token = access_token
        st.session_state.whatsapp_api_version = api_version
        st.session_state.message_template_name = template_name
    
    notifications = st.toggle(
        "🔔 Activer les rappels",
        value=st.session_state.notifications_enabled,
        key="sidebar_notifications"
    )
    st.session_state.notifications_enabled = notifications
    
    if notifications:
        recipient = st.text_input(
            "📞 Numéro destinataire",
            value=st.session_state.recipient_phone,
            placeholder="Ex: 15141234567",
            help="Format international sans +",
            key="sidebar_recipient"
        )
        st.session_state.recipient_phone = recipient
        
        if recipient and not validate_phone_number(recipient):
            st.warning("⚠️ Numéro invalide")
        
        st.write("**Jours de rappel:**")
        cols = st.columns(4)
        selected = []
        for i in range(1, 8):
            with cols[(i-1) % 4]:
                if st.checkbox(
                    f"J{i}",
                    value=i in st.session_state.reminder_days,
                    key=f"sidebar_day_{i}"
                ):
                    selected.append(i)
        st.session_state.reminder_days = selected
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🧪 Test", use_container_width=True, key="sidebar_test"):
                if recipient and validate_phone_number(recipient):
                    success = send_whatsapp_text_message(
                        recipient,
                        "🏋️ Test Coach Serge!\n\nLes notifications fonctionnent! 💪"
                    )
                    if success:
                        st.success("✅ Envoyé!")
                    else:
                        st.error("❌ Échec")
                else:
                    st.warning("⚠️ Entre un numéro valide")
    
    st.markdown("---")
    
    debug_mode = st.checkbox("🐛 Mode debug", value=False, key="sidebar_debug")
    if debug_mode:
        st.write(f"**Step:** {st.session_state.step}")
        st.write(f"**Page:** {st.session_state.page}")
        st.write(f"**Q-index:** {st.session_state.q_index}")

# ===================== QUESTIONNAIRE CONSTANTS =====================
QUESTIONS = [
    {"key":"age","label":"Quel est ton âge?","type":"number","min":13,"max":100},
    {"key":"sexe","label":"Quel est ton sexe?","type":"select","options":["Homme","Femme","Autre / Préfère ne pas dire"]},
    {"key":"taille_cm","label":"Quelle est ta taille (en cm)?","type":"number","min":120,"max":220},
    {"key":"poids_kg","label":"Quel est ton poids (en kg)?","type":"number","min":35,"max":220},
    {"key":"niveau_exp","label":"Quel est ton niveau d'expérience en entraînement?","type":"select",
     "options":["Débutant","Intermédiaire","Avancé","Expert"]},
    {"key":"blessures","label":"As-tu actuellement des blessures ou des limitations physiques?","type":"text",
     "help":"Indique toute blessure pour qu'on adapte les exercices"},
    {"key":"sante","label":"As-tu des problèmes de santé connus (asthme, hypertension, diabète, etc.)?","type":"text"},
    {"key":"activite","label":"Quel est ton niveau d'activité physique au quotidien (hors entraînements)?","type":"select",
     "options":["Peu actif (Travail de bureau)","Modérément actif (Marche régulière)",
                "Actif (Travail physique)","Très actif (Sports fréquents)"]},
    {"key":"objectif_principal","label":"Quel est ton objectif principal d'entraînement?","type":"text",
     "help":"Sois précis: perte de poids, gain musculaire, endurance, force..."},
    {"key":"objectif_secondaire","label":"As-tu un objectif secondaire?","type":"text","help":"Optionnel"},
    {"key":"horizon","label":"Dans combien de temps veux-tu atteindre ton objectif principal?","type":"select",
     "options":["3 mois","6 mois","1 an","Plus d'un an"]},
    {"key":"motivation","label":"Quel est ton niveau de motivation sur 10?","type":"slider","min":1,"max":10},
    {"key":"types_exos","label":"Quel type d'exercices préfères-tu?","type":"multiselect",
     "options":["Musculation","Cardio (course, vélo...)","HIIT (haute intensité)",
                "Sports collectifs","Yoga / Pilates","Natation","Autre"]},
    {"key":"jours_sem","label":"Combien de jours par semaine veux-tu t'entraîner?","type":"slider","min":1,"max":7},
    {"key":"duree_min","label":"Combien de temps veux-tu consacrer à chaque séance (en min)?","type":"slider",
     "min":15,"max":120,"step":5},
    {"key":"moment","label":"À quel moment de la journée préfères-tu t'entraîner?","type":"select",
     "options":["Matin (6h-10h)","Midi (11h-14h)","Après-midi (15h-18h)","Soir / Nuit (19h+)"]},
    {"key":"lieu","label":"Préfères-tu t'entraîner à l'intérieur ou dehors?","type":"select",
     "options":["Intérieur (gym, maison)","Extérieur (parc, rue...)","Peu importe"]},
    {"key":"materiel","label":"Quel matériel d'entraînement as-tu à ta disposition?","type":"text",
     "help":"Liste le matériel disponible"},
    {"key":"sommeil_h","label":"Combien d'heures dors-tu en moyenne par nuit?","type":"slider","min":4.0,"max":12.0,"step":0.5},
    {"key":"ville","label":"Dans quelle ville t'entraînes-tu (pour la météo)?","type":"text"},
    {"key":"nutrition","label":"Souhaites-tu recevoir des conseils de nutrition et/ou de récupération?","type":"select",
     "options":["Oui, absolument","Oui, si possible","Non merci"]},
]

TOTAL_Q = len(QUESTIONS)

# ===================== OPENAI FUNCTIONS =====================
def call_openai_plan(api_key: str, profile: dict) -> str:
    """Génère un plan d'entraînement via OpenAI en respectant le nb de séances/semaine."""
    try:
        if not api_key or not api_key.startswith("sk-"):
            logger.warning("Invalid API key for plan generation")
            return ""

        try:
            jours_sem = int(profile.get("jours_sem") or 3)
        except Exception:
            jours_sem = 3
        jours_sem = max(1, min(7, jours_sem))

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        system_prompt = (
            "Tu es un coach sportif certifié professionnel.\n"
            f"L'utilisateur souhaite s'entraîner **{jours_sem} jours par semaine**.\n\n"
            "GENÈRE un plan d'entraînement personnalisé sur **7 jours** au format Markdown.\n"
            "- Utilise des sections claires du type : **Jour X — Titre**.\n"
            "- Pour chaque **jour d'entraînement** (il doit y en avoir exactement "
            f"{jours_sem} sur 7) indique : durée, exercices (séries x reps) et RPE (1-10), "
            "ainsi que des conseils de récupération.\n"
            "- Pour les **jours de repos**, écris clairement : **Jour X — Repos complet** "
            "et ne propose AUCUN exercice, AUCUNE activité physique, même pas de "
            "« récupération active ».\n"
            "- Respecte les blessures, le matériel disponible et le niveau de l'utilisateur."
        )

        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Profil utilisateur: {json.dumps(profile, ensure_ascii=False)}"}
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }

        logger.info("Calling OpenAI API for workout plan")
        response = requests.post(url, headers=headers, json=body, timeout=60)

        if response.status_code == 200:
            data = response.json()
            plan = data["choices"][0]["message"]["content"]
            logger.info("Plan generated successfully")
            return plan
        else:
            logger.error(f"OpenAI API error: {response.status_code}")
            return ""

    except requests.exceptions.Timeout:
        logger.error("OpenAI API timeout")
        st.error("❌ Timeout - L'API OpenAI ne répond pas")
        return ""
    except Exception as e:
        logger.error(f"OpenAI plan error: {str(e)}", exc_info=True)
        return ""

def compute_calorie_targets(profile: dict):
    """Calcule l'apport calorique et macros cibles en fonction du profil."""
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

    obj_lower = (objectif or "").lower()
    if "perte" in obj_lower:
        calories -= 400
    elif "masse" in obj_lower or "gain" in obj_lower:
        calories += 400

    proteines = round(poids * 1.8)
    glucides = round((calories * 0.5) / 4)
    lipides = round((calories * 0.25) / 9)

    return calories, proteines, glucides, lipides, objectif

def call_openai_nutrition(api_key: str, profile: dict) -> str:
    """Génère un plan nutritionnel via OpenAI sur 7 jours avec cibles caloriques."""
    try:
        if not api_key or not api_key.startswith("sk-"):
            return ""

        calories, proteines, glucides, lipides, objectif = compute_calorie_targets(profile)

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        system_prompt = (
            "Tu es un nutritionniste certifié.\n"
            f"L'objectif principal déclaré est : {objectif}.\n"
            f"Les cibles quotidiennes approximatives sont : {calories} kcal, "
            f"{proteines} g de protéines, {glucides} g de glucides, {lipides} g de lipides.\n\n"
            "Crée un **plan nutritionnel sur exactement 7 jours (Jour 1 à Jour 7)** "
            "au format Markdown.\n"
            "Pour CHAQUE jour, inclus :\n"
            "- Petit-déjeuner\n- Dîner\n- Souper\n- 1 à 2 collations\n"
            "- Un total calorique estimé pour la journée (proche des cibles, ±10%).\n"
            "Utilise des intitulés clairs du type : `### Jour 1`, `### Jour 2`, ..., `### Jour 7`.\n"
            "Assure-toi de ne PAS oublier le Jour 7."
        )

        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Profil: {json.dumps(profile, ensure_ascii=False)}"}
            ],
            "max_tokens": 1500,
            "temperature": 0.7
        }

        logger.info("Calling OpenAI API for nutrition plan")
        response = requests.post(url, headers=headers, json=body, timeout=60)

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return ""

    except Exception as e:
        logger.error(f"OpenAI nutrition error: {str(e)}")
        return ""

def call_openai_chat(api_key: str, user_input: str, profile: dict, current_plan: str = "", nutrition_plan: str = "") -> str:
    """Obtient une réponse de chat du coach IA"""
    try:
        if not api_key or not api_key.startswith("sk-"):
            return "Configure une clé API OpenAI pour utiliser le chat IA."
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            f"Tu es Serge, un coach sportif professionnel expert et motivant. "
            f"Tu discutes avec ton client et tu connais son profil, son plan d'entraînement et son plan nutritionnel. "
            f"Réponds de manière personnalisée, concise et pratique. "
            f"\n\n**PROFIL CLIENT:**\n{json.dumps(profile, ensure_ascii=False, indent=2)}"
        )
        
        if current_plan:
            system_prompt += f"\n\n**PLAN D'ENTRAÎNEMENT ACTUEL:**\n{current_plan[:1500]}"
        
        if nutrition_plan:
            system_prompt += f"\n\n**PLAN NUTRITIONNEL:**\n{nutrition_plan[:1000]}"
        
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "max_tokens": 600,
            "temperature": 0.7
        }
        
        logger.info("Calling OpenAI API for chat")
        response = requests.post(url, headers=headers, json=body, timeout=30)
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return "Désolé, je ne peux pas répondre pour le moment."
        
    except Exception as e:
        logger.error(f"OpenAI chat error: {str(e)}")
        return f"Erreur: {str(e)}"

def call_openai_exercise_suggestion(api_key: str, request: str, profile: dict, current_plan: str) -> str:
    """Propose des exercices de remplacement sans modifier le plan (demande confirmation)."""
    if not api_key or not api_key.startswith("sk-"):
        return "Configure une clé API OpenAI pour que je puisse analyser et proposer un remplacement précis."

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "Tu es un coach sportif professionnel.\n"
        "L'utilisateur veut modifier un ou plusieurs exercices dans son plan d'entraînement.\n"
        "Lis sa demande et PROPOSE 1 à 3 exercices de remplacement **concrets** "
        "(nom, séries, répétitions, éventuellement charge ou RPE) qui soient équivalents.\n"
        "Ne réécris PAS tout le plan, concentre-toi seulement sur les substitutions proposées.\n"
        "À la fin, termine TOUJOURS par une question très claire du type :\n"
        "\"Veux-tu que je mette à jour le plan avec ces changements ? Réponds par oui ou non.\""
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Profil utilisateur:\n{json.dumps(profile, ensure_ascii=False, indent=2)}\n\n"
                f"Plan actuel (extrait):\n{(current_plan or '')[:2000]}\n\n"
                f"Demande de l'utilisateur :\n{request}"
            )
        }
    ]

    body = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 700,
        "temperature": 0.6
    }

    try:
        logger.info("Calling OpenAI for exercise suggestion (no plan update yet)")
        response = requests.post(url, headers=headers, json=body, timeout=60)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"OpenAI exercise suggestion error: {response.status_code}")
            return "Je n'ai pas pu générer une suggestion d'exercice pour le moment."
    except Exception as e:
        logger.error(f"Exercise suggestion error: {e}")
        return f"Erreur lors de la suggestion d'exercice : {e}"

def fallback_nutrition(profile: dict) -> str:
    """Génère un plan nutritionnel simple sur 7 jours avec les bons apports."""
    calories, proteines, glucides, lipides, objectif = compute_calorie_targets(profile)

    base_intro = f"""**Plan nutritionnel — Objectif : {objectif}**

🔹 Apport cible : **{calories} kcal / jour**  
🔹 Répartition macros (approx.) :  
- Protéines : {proteines} g  
- Glucides : {glucides} g  
- Lipides : {lipides} g  

Ce plan propose 7 jours avec des menus variés mais équilibrés, autour de ces cibles.
"""

    jours = []
    for i in range(1, 8):
        jours.append(f"""
---

### Jour {i}

**Petit-déjeuner** (~{int(0.25 * calories)} kcal)  
- Avoine (60g) avec fruits rouges  
- Yogourt grec (150g)  
- 1 fruit (pomme ou banane)  

**Dîner** (~{int(0.3 * calories)} kcal)  
- Source de protéine (poulet, tofu ou poisson, 120-150g)  
- Féculent complet (riz brun, quinoa, pâtes de blé entier ~80-100g crus)  
- Légumes variés (brocoli, carottes, salade)  
- 1 c. à soupe d'huile d'olive  

**Souper** (~{int(0.3 * calories)} kcal)  
- Source de protéine (saumon, légumineuses, tempeh, etc. 120-150g)  
- Légumes cuits ou crus  
- Portion modérée de féculents (riz, pommes de terre, etc.)  

**Collations** (~{int(0.15 * calories)} kcal au total)  
- 1 poignée d'amandes ou noix (20-30g)  
- 1 yogourt ou un petit shake protéiné  
- 1 fruit

**Total cible** : ~{calories} kcal (±10%)  
""")

    conseils = """
---

💧 **Hydratation :** 2-3 L d'eau par jour  
🚫 **À limiter :** sucres ajoutés, aliments ultra-transformés, alcool en excès  
✅ **À privilégier :** aliments entiers, protéines maigres, légumes, fruits frais, fibres  
"""

    return base_intro + "\n".join(jours) + conseils

# ===================== CALENDRIER FUNCTIONS =====================
try:
    from streamlit_calendar import calendar as st_calendar
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
    logger.warning("streamlit-calendar not installed")

def parse_workout_plan(plan_text: str) -> list:
    """Parse le plan pour extraire les sessions par jour"""
    sessions = []
    
    if not plan_text or not isinstance(plan_text, str) or not plan_text.strip():
        logger.warning("Plan text is empty or invalid")
        return sessions
    
    lines = plan_text.splitlines()
    logger.info(f"Parsing plan with {len(lines)} lines")
    
    patterns = [
        re.compile(r'^\s*\*\*\s*(?:Jour|Day|JOUR|DAY)\s+(\d+)\s*(?:[:\-–—]\s*(.*))?\s*\*\*\s*$', re.IGNORECASE),
        re.compile(r'^\s*(?:Jour|Day|JOUR|DAY)\s+(\d+)\s*(?:[:\-–—]\s*(.*))?\s*$', re.IGNORECASE),
        re.compile(r'^\s*#{1,6}\s*(?:Jour|Day|JOUR|DAY)\s+(\d+)\s*(?:[:\-–—]\s*(.*))?\s*$', re.IGNORECASE),
    ]
    
    current_day = None
    current_title = None
    current_description = []
    
    for line_num, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        if not line_stripped:
            continue
        
        matched = False
        for pattern in patterns:
            match = pattern.match(line_stripped)
            if match:
                matched = True
                
                if current_day is not None:
                    desc = "\n".join(current_description).strip()
                    sessions.append({
                        "day": current_day,
                        "title": current_title or "Entraînement",
                        "description": desc[:500] if desc else "Séance d'entraînement"
                    })
                    logger.debug(f"Saved session Day {current_day}: {current_title}")
                
                current_day = int(match.group(1))
                current_title = (match.group(2) or "Entraînement").strip() if match.lastindex and match.group(2) else "Entraînement"
                current_description = []
                logger.info(f"Line {line_num}: Found Day {current_day} - {current_title}")
                break
        
        if matched:
            continue
        
        if current_day is not None:
            if not re.match(r'^[\*\-=_#]{3,}$', line_stripped):
                if len(current_description) < 20:
                    current_description.append(line_stripped)
    
    if current_day is not None:
        desc = "\n".join(current_description).strip()
        sessions.append({
            "day": current_day,
            "title": current_title or "Entraînement",
            "description": desc[:500] if desc else "Séance d'entraînement"
        })
        logger.debug(f"Saved final session Day {current_day}: {current_title}")
    
    logger.info(f"✅ Parsed {len(sessions)} total sessions from plan")
    
    for session in sessions:
        logger.info(f" → Jour {session['day']}: {session['title']}")
    
    if len(sessions) == 0:
        logger.warning("No sessions found with standard patterns, trying basic parsing")
        for line in lines:
            if re.search(r'(?:jour|day)\s*(\d+)', line, re.IGNORECASE):
                match = re.search(r'(?:jour|day)\s*(\d+)', line, re.IGNORECASE)
                day_num = int(match.group(1))
                sessions.append({
                    "day": day_num,
                    "title": f"Jour {day_num}",
                    "description": line.strip()
                })
                logger.info(f" → Basic parse: Jour {day_num}")
    
    return sessions

def create_calendar_events(sessions: list, start_date=None) -> list:
    """Crée des événements calendrier à partir des sessions"""
    from datetime import datetime, timedelta
    
    if not sessions:
        return []
    
    if start_date is None:
        start_date = datetime.now()
    
    if hasattr(start_date, 'hour'):
        start_date = datetime.combine(start_date.date(), datetime.min.time())
    else:
        start_date = datetime.combine(start_date, datetime.min.time())
    
    moment_pref = st.session_state.answers.get("moment", "Matin (6h-10h)")
    duree = int(st.session_state.answers.get("duree_min", 60) or 60)
    
    time_map = {
        "Matin (6h-10h)": "07:00",
        "Midi (11h-14h)": "12:00",
        "Après-midi (15h-18h)": "15:00",
        "Soir / Nuit (19h+)": "18:00"
    }
    
    start_time = time_map.get(moment_pref, "07:00")
    hour, minute = map(int, start_time.split(':'))
    end_minute = minute + duree
    end_hour = hour + (end_minute // 60)
    end_minute = end_minute % 60
    end_time = f"{end_hour:02d}:{end_minute:02d}"
    
    events = []
    for session in sessions:
        event_date = start_date + timedelta(days=session['day'] - 1)
        date_str = event_date.strftime("%Y-%m-%d")
        
        title_lower = (session['title'] or "").lower()
        is_rest = any(word in title_lower for word in ["repos", "rest", "récupération", "recovery"])
        color = "#888888" if is_rest else "#3ea6ff"
        
        events.append({
            "title": f"Jour {session['day']}: {session['title']}",
            "start": f"{date_str}T{start_time}:00",
            "end": f"{date_str}T{end_time}:00",
            "extendedProps": {
                "description": session['description'],
                "day_number": session['day']
            },
            "backgroundColor": color,
            "borderColor": color,
            "textColor": "#ffffff"
        })
    
    logger.info(f"Created {len(events)} calendar events")
    return events

def recompute_calendar_events():
    """Recalcule les événements du calendrier"""
    start_date = st.session_state.get("calendar_start_date")
    if not start_date:
        start_date = dt.date.today()
        st.session_state.calendar_start_date = start_date
    
    plan_text = st.session_state.get("plan_text", "") or ""
    if not plan_text:
        st.session_state.calendar_events = []
        return
    
    sessions = parse_workout_plan(plan_text)
    events = create_calendar_events(sessions, start_date)
    st.session_state.calendar_events = events
    logger.info(f"Calendar recomputed: {len(events)} events")

# ===================== MÉTÉO FUNCTIONS =====================
def geocode_city(city: str):
    """Récupère les coordonnées d'une ville"""
    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "fr"},
            timeout=10
        )
        results = response.json().get("results", [])
        if not results:
            return None
        loc = results[0]
        return (
            float(loc["latitude"]),
            float(loc["longitude"]),
            f'{loc["name"]}, {loc.get("country","")}'
        )
    except Exception as e:
        logger.error(f"Geocoding error: {str(e)}")
        return None

def get_today_weather(lat: float, lon: float):
    """Récupère la météo du jour"""
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,precipitation_probability",
                "forecast_days": 1,
                "timezone": "auto"
            },
            timeout=10
        )
        return response.json()
    except Exception as e:
        logger.error(f"Weather API error: {str(e)}")
        return None

def weather_advice(weather_json, planned_minutes: int) -> str:
    """Génère des conseils selon la météo"""
    try:
        temps = weather_json["hourly"]["temperature_2m"][0]
        prec = weather_json["hourly"]["precipitation_probability"][0]
        
        if prec > 50 or temps < 0 or temps > 28:
            return (
                f"⚠️ Météo peu favorable ({temps}°C, pluie {prec}%). "
                f"Alternative indoor ~{planned_minutes} min : circuit cardio / full body / yoga."
            )
        return f"✅ Météo OK ({temps}°C, pluie {prec}%). Entraînement extérieur possible!"
    except Exception as e:
        logger.error(f"Weather advice error: {str(e)}")
        return "Météo indisponible."

def get_weather(city: str = "Montreal") -> dict:
    """Récupère la météo actuelle pour une ville via Open-Meteo (plus fiable)."""
    geo = geocode_city(city)
    if geo:
        lat, lon, full_name = geo
        try:
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": True,
                    "timezone": "auto"
                },
                timeout=10
            )
            data = response.json()
            cw = data.get("current_weather", {}) or {}
            temp = cw.get("temperature")
            weather_code = cw.get("weathercode")

            code_map = {
                0: "Ciel dégagé",
                1: "Principalement dégagé",
                2: "Partiellement nuageux",
                3: "Couvert",
                45: "Brouillard",
                48: "Brouillard givrant",
                51: "Bruine faible",
                53: "Bruine modérée",
                55: "Bruine forte",
                61: "Pluie faible",
                63: "Pluie modérée",
                65: "Pluie forte",
                71: "Neige faible",
                73: "Neige modérée",
                75: "Neige forte",
                80: "Averses faibles",
                81: "Averses modérées",
                82: "Averses fortes"
            }
            condition = code_map.get(weather_code, "Conditions variables")

            if isinstance(temp, (int, float)):
                return {
                    "temp": f"{round(temp)}",
                    "condition": condition,
                    "humidity": "--",
                    "feels_like": f"{round(temp)}"
                }
        except Exception as e:
            logger.warning(f"Open-Meteo error in get_weather: {e}")

    logger.warning("Fallback météo utilisé (valeurs par défaut).")
    return {
        "temp": "20",
        "condition": "Ensoleillé",
        "humidity": "65",
        "feels_like": "18"
    }

# ===================== PLAN ADAPTATION (AI AGENT) =====================
def _extract_json_block(text: str):
    """Extrait un bloc JSON d'une réponse texte (avec ou sans ```json)."""
    try:
        m = re.search(r"```json(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if m:
            return json.loads(m.group(1).strip())

        m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if m:
            return json.loads(m.group(1).strip())

        return None
    except Exception:
        return None

def ai_edit_plan(api_key: str, instruction: str, plan_text: str, profile: dict) -> dict:
    """Adapte le plan complet avec l'IA"""
    if not api_key or not api_key.startswith("sk-"):
        return {"ok": False, "new_plan": "", "summary": "Pas de clé API."}
    
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            "Tu es un coach certifié. Tu reçois un plan d'entraînement en Markdown "
            "et une instruction de modification. Adapte le plan selon l'instruction "
            "en gardant le format (jours, exercices, RPE). Respecte les contraintes. "
            "Réponds STRICTEMENT en JSON: {\"new_plan\": \"\", \"summary\": \"\", \"changed_days\": []}"
        )
        
        user_prompt = (
            f"=== PROFIL ===\n{json.dumps(profile, ensure_ascii=False)}\n\n"
            f"=== INSTRUCTION ===\n{instruction}\n\n"
            f"=== PLAN ACTUEL ===\n{plan_text}\n\n"
            "=== FORMAT SORTIE ===\n"
            "{\"new_plan\": \"...\", \"summary\": \"...\", \"changed_days\": [1,2,3]}"
        )
        
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 1400,
            "temperature": 0.5
        }
        
        logger.info(f"Calling AI edit plan: {instruction[:50]}...")
        response = requests.post(url, headers=headers, json=body, timeout=60)
        
        if response.status_code != 200:
            return {"ok": False, "new_plan": "", "summary": f"Erreur API: {response.status_code}"}
        
        content = response.json()["choices"][0]["message"]["content"]
        obj = _extract_json_block(content) or {}
        
        new_plan = obj.get("new_plan", "").strip()
        summary = obj.get("summary", "").strip()
        
        if new_plan and ("Jour 1" in new_plan or "Day 1" in new_plan):
            logger.info("Plan adapted successfully")
            return {"ok": True, "new_plan": new_plan, "summary": summary or "Plan adapté."}
        
        return {"ok": False, "new_plan": "", "summary": "Réponse modèle non exploitable."}
        
    except Exception as e:
        logger.error(f"AI edit plan error: {str(e)}", exc_info=True)
        return {"ok": False, "new_plan": "", "summary": f"Erreur: {str(e)}"}

# ===================== CHAT COMMAND HANDLER =====================
def handle_chat_command(user_text: str):
    """Traite les commandes textuelles du chat (plan, remplacement, etc.)."""
    text = user_text.strip()
    low = text.lower()

    # 0) Si une modification est en attente, on check d'abord oui/non
    pending = st.session_state.get("pending_plan_change")
    if pending:
        if any(w in low for w in ["oui", "yes", "ok", "vas-y", "vas y", "go", "applique", "apply"]):
            profile = st.session_state.answers
            result = ai_edit_plan(
                st.session_state.api_key,
                pending["instruction"],
                st.session_state.plan_text,
                profile
            )
            st.session_state.pending_plan_change = None

            if result.get("ok"):
                st.session_state.plan_text = result["new_plan"]
                st.session_state.flash_plan_updated = True
                st.session_state._last_plan_hash = hash(st.session_state.plan_text)
                recompute_calendar_events()
                feedback = (
                    "✅ J'ai mis à jour ton plan avec les changements proposés.\n\n"
                    f"**Résumé** — {result.get('summary', 'Plan adapté.')}"
                )
                return {
                    "feedback": feedback,
                    "plan_changed": True,
                    "calendar_changed": True,
                    "is_command": True
                }
            else:
                return {
                    "feedback": f"⚠️ Je n'ai pas réussi à appliquer la modification. {result.get('summary', '')}",
                    "plan_changed": False,
                    "calendar_changed": False,
                    "is_command": True
                }

        if any(w in low for w in ["non", "no", "annule", "cancel"]):
            st.session_state.pending_plan_change = None
            return {
                "feedback": "👍 D'accord, je ne modifie pas le plan.",
                "plan_changed": False,
                "calendar_changed": False,
                "is_command": True
            }

    # 1) Regénération complète du plan
    if re.search(r"\b(régénère|regenere|regenerate)\b.*\bplan\b", low):
        profile = {k: st.session_state.answers.get(k) for k in [
            "age", "sexe", "taille_cm", "poids_kg", "niveau_exp", "blessures", "sante",
            "activite", "objectif_principal", "objectif_secondaire", "horizon", "motivation",
            "types_exos", "jours_sem", "duree_min", "moment", "lieu", "materiel",
            "sommeil_h", "ville", "nutrition"
        ]}
        plan_text = call_openai_plan(st.session_state.api_key, profile) if st.session_state.api_key else ""
        st.session_state.plan_text = plan_text or fallback_plan(profile)
        st.session_state._last_plan_hash = hash(st.session_state.plan_text)
        recompute_calendar_events()
        return {
            "feedback": "🔄 J'ai régénéré ton plan.",
            "plan_changed": True,
            "calendar_changed": True,
            "is_command": True
        }

    # 2) Demande de remplacement d'exercice
    replace_patterns = [
        r"exercice de remplacement",
        r"remplace", r"remplacer", r"remplacement",
        r"exercice équivalent", r"exercices équivalents"
    ]
    is_replacement_request = any(re.search(p, low) for p in replace_patterns)

    if is_replacement_request:
        if not st.session_state.api_key:
            return {
                "feedback": "💡 Pour que je puisse proposer et appliquer un exercice de remplacement automatiquement, ajoute une clé OpenAI dans la barre latérale.",
                "plan_changed": False,
                "calendar_changed": False,
                "is_command": True
            }

        suggestion = call_openai_exercise_suggestion(
            st.session_state.api_key,
            text,
            st.session_state.answers,
            st.session_state.plan_text
        )

        st.session_state.pending_plan_change = {
            "instruction": text
        }

        return {
            "feedback": suggestion,
            "plan_changed": False,
            "calendar_changed": False,
            "is_command": True
        }

    # 3) Modifications plus générales du plan
    plan_modification_keywords = [
        r"\b(modifie|modifier|change|changer|adapte|adapter|ajuste|ajuster)\b.*\bplan\b",
        r"\bplan\b.*\b(modifie|modifier|change|changer|adapte|adapter|ajuste|ajuster)\b",
        r"\b(ajoute|ajouter|enlève|enlever|retire|retirer|supprime|supprimer)\b.*\b(jour|exercice|séance)\b",
        r"\b(plus|moins)\b.*\b(cardio|musculation|hiit|repos|exercice)\b",
        r"\b(rédui[st]|augmente|diminue)\b.*\b(durée|jours|répétitions|séries)\b"
    ]

    is_plan_modification = any(re.search(pattern, low) for pattern in plan_modification_keywords)

    if is_plan_modification and st.session_state.api_key:
        if not st.session_state.plan_text:
            profile = {k: st.session_state.answers.get(k) for k in [
                "age", "sexe", "taille_cm", "poids_kg", "niveau_exp", "blessures", "sante",
                "activite", "objectif_principal", "objectif_secondaire", "horizon", "motivation",
                "types_exos", "jours_sem", "duree_min", "moment", "lieu", "materiel",
                "sommeil_h", "ville", "nutrition"
            ]}
            plan_text = call_openai_plan(st.session_state.api_key, profile) or fallback_plan(profile)
            st.session_state.plan_text = plan_text

        result = ai_edit_plan(
            st.session_state.api_key,
            text,
            st.session_state.plan_text,
            st.session_state.answers
        )

        if result.get("ok"):
            st.session_state.plan_text = result["new_plan"]
            st.session_state.flash_plan_updated = True
            st.session_state._last_plan_hash = hash(st.session_state.plan_text)
            recompute_calendar_events()
            return {
                "feedback": f"🧠 J'ai adapté le plan automatiquement.\n\n**Résumé** — {result.get('summary','')}",
                "plan_changed": True,
                "calendar_changed": True,
                "is_command": True
            }
        else:
            return {
                "feedback": f"⚠️ Je n'ai pas pu adapter le plan. {result.get('summary','')}",
                "plan_changed": False,
                "calendar_changed": False,
                "is_command": True
            }

    if is_plan_modification and not st.session_state.api_key:
        return {
            "feedback": "💡 Pour adapter automatiquement le plan, ajoute une clé OpenAI dans la barre latérale.",
            "plan_changed": False,
            "calendar_changed": False,
            "is_command": True
        }

    # 4) Sinon : pas une commande spéciale → chat normal
    return {
        "feedback": "",
        "plan_changed": False,
        "calendar_changed": False,
        "is_command": False
    }

# ===================== UI HELPERS =====================
def render_input(q, default=None):
    """Rend un input de questionnaire selon son type"""
    t = q["type"]
    label = q["label"]
    
    if t == "text":
        return st.text_input(label, value=default or "", key=f"in_{q['key']}")
    elif t == "number":
        base = q.get("min", 0)
        val = base if default in (None, "") else int(default)
        return st.number_input(
            label,
            min_value=q.get("min", 0),
            max_value=q.get("max", 999),
            value=val,
            key=f"in_{q['key']}"
        )
    elif t == "select":
        opts = q["options"]
        idx = opts.index(default) if default in opts else 0
        return st.selectbox(label, opts, index=idx, key=f"in_{q['key']}")
    elif t == "multiselect":
        opts = q["options"]
        default = default or []
        return st.multiselect(label, opts, default=default, key=f"in_{q['key']}")
    elif t == "slider":
        return st.slider(
            label,
            q["min"],
            q["max"],
            value=default if default is not None else q["min"],
            step=q.get("step", 1),
            key=f"in_{q['key']}"
        )
    return st.text_input(label, value=default or "", key=f"in_{q['key']}")

# ===================== WEATHER & FEATURES =====================
def get_daily_quote() -> str:
    """Retourne une citation motivante aléatoire"""
    quotes = [
        "Le succès, c'est tomber sept fois et se relever huit.",
        "Votre corps peut tout faire. C'est votre esprit que vous devez convaincre.",
        "La discipline est le pont entre les objectifs et l'accomplissement.",
        "Ne comptez pas les jours, faites que les jours comptent.",
        "Vous êtes plus fort que vous ne le pensez.",
    ]
    import random
    return random.choice(quotes)

def calculate_streak(workouts: list) -> int:
    """Calcule la série consécutive"""
    if not workouts:
        return 0
    
    from datetime import datetime
    sorted_workouts = sorted(workouts, key=lambda x: x.get('date', ''), reverse=True)
    streak = 0
    current_date = datetime.now().date()
    
    for workout in sorted_workouts:
        try:
            workout_date = datetime.strptime(workout.get('date', ''), '%Y-%m-%d').date()
            delta = (current_date - workout_date).days
            if delta == streak or delta == streak + 1:
                streak += 1
                current_date = workout_date
            else:
                break
        except:
            continue
    
    return streak

def get_next_workout(plan_text: str, last_completed_day: int = None) -> dict:
    """Récupère le prochain workout en tenant compte des jours complétés"""
    if not plan_text:
        return None
    
    sessions = parse_workout_plan(plan_text)
    if not sessions:
        return None
    
    if last_completed_day is not None:
        for session in sessions:
            if session['day'] > last_completed_day:
                return session
        return sessions[0] if sessions else None
    
    from datetime import datetime
    today = datetime.now()
    day_of_week = today.weekday() + 1
    
    for session in sessions:
        if session['day'] == day_of_week:
            return session
    
    return sessions[0] if sessions else None

def render_top_navigation(current_page=None):
    """Navigation horizontale en haut"""
    cols = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1])
    
    with cols[0]:
        if st.button("👤 Profil", key=f"nav_{current_page}_profile", use_container_width=True, 
                    disabled=(current_page == "profile")):
            st.session_state.page = "profile"
            st.rerun()
    
    with cols[1]:
        if st.button("🏠 Dashboard", key=f"nav_{current_page}_home", use_container_width=True, 
                    disabled=(current_page is None)):
            st.session_state.page = None
            st.rerun()
    
    with cols[2]:
        if st.button("📋 Plan", key=f"nav_{current_page}_plan", use_container_width=True, 
                    disabled=(current_page == "plan")):
            st.session_state.page = "plan"
            st.rerun()
    
    with cols[3]:
        if st.button("🌤️ Météo", key=f"nav_{current_page}_meteo", use_container_width=True, 
                    disabled=(current_page == "meteo")):
            st.session_state.page = "meteo"
            st.rerun()
    
    with cols[4]:
        if st.button("💬 Chat", key=f"nav_{current_page}_chat", use_container_width=True, 
                    disabled=(current_page == "chat")):
            st.session_state.page = "chat"
            st.rerun()
    
    with cols[5]:
        if st.button("📅 Calendrier", key=f"nav_{current_page}_calendar", use_container_width=True, 
                    disabled=(current_page == "calendar")):
            st.session_state.page = "calendar"
            st.rerun()
    
    with cols[6]:
        if st.button("🍎 Nutrition", key=f"nav_{current_page}_nutrition", use_container_width=True, 
                    disabled=(current_page == "nutrition")):
            st.session_state.page = "nutrition"
            st.rerun()
    
    with cols[7]:
        if st.button("🏋️ Workouts", key=f"nav_{current_page}_workouts", use_container_width=True, 
                    disabled=(current_page == "workouts")):
            st.session_state.page = "workouts"
            st.rerun()
    
    with cols[8]:
        if st.button("🔄 Reset", key=f"nav_{current_page}_reset", use_container_width=True):
            st.session_state.step = "form"
            st.session_state.q_index = 0
            st.session_state.page = None
            st.rerun()

def fallback_plan(profile: dict) -> str:
    """Génère un plan d'entraînement basique sur 7 jours en respectant jours_sem."""
    niveau = profile.get("niveau_exp", "Débutant") or "Débutant"
    try:
        jours = int(profile.get("jours_sem", 3) or 3)
    except Exception:
        jours = 3
    jours = max(1, min(7, jours))

    duree = int(profile.get("duree_min", 45) or 45)
    objectif = profile.get("objectif_principal", "Condition générale") or "Condition générale"

    header = f"""# Plan d'entraînement personnalisé

**Niveau :** {niveau}  
**Objectif :** {objectif}  
**Fréquence :** {jours} jours/semaine  
**Durée par séance :** {duree} min

---
"""

    templates = [
        ("Full Body", [
            "- Échauffement: 5-10 min cardio léger",
            "- Squats: 3 x 10-12",
            "- Pompes (sur genoux si nécessaire): 3 x 8-10",
            "- Fentes: 3 x 10 (chaque jambe)",
            "- Planche: 3 x 20-30 sec",
            "- Retour au calme: étirements 5 min"
        ]),
        ("Cardio + Core", [
            "- Échauffement: 5 min",
            "- Intervalles cardio: 20-25 min (course/vélo/rameur)",
            "- Crunches: 3 x 15",
            "- Mountain climbers: 3 x 20 sec",
            "- Russian twists: 3 x 15",
            "- Étirements: 5 min"
        ]),
        ("Force haut du corps", [
            "- Échauffement: 5-10 min",
            "- Développé couché ou pompes: 3 x 8-10",
            "- Rowing: 3 x 10-12",
            "- Élévations latérales: 3 x 12-15",
            "- Gainage: 3 x 30 sec",
            "- Étirements: 5 min"
        ])
    ]

    lines = [header]

    training_days = 0
    for day in range(1, 8):
        if training_days < jours:
            title, exos = templates[training_days % len(templates)]
            lines.append(f"**Jour {day} — {title}**")
            lines.append(f"⏱ Durée: {duree} min | 🔥 RPE: 6-7/10")
            lines.extend(exos)
            lines.append("\n---\n")
            training_days += 1
        else:
            lines.append(f"**Jour {day} — Repos complet**")
            lines.append("💤 Aucune séance prévue, concentre-toi sur le sommeil, l'hydratation et la récupération.")
            lines.append("\n---\n")

    lines.append("**Conseils généraux :**\n- Hydrate-toi bien avant, pendant et après\n- Écoute ton corps et ajuste l'intensité\n- Augmente progressivement la charge\n")
    return "\n".join(lines)

# ===================== MAIN APP LOGIC =====================

# Landing Page
if st.session_state.step == "landing":
    st.markdown('<h1 class="landing-title">🏋️ Coach Serge Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="landing-subtitle">Ton coach sportif personnel propulsé par l\'IA</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Découvre ton potentiel")
        st.write("📊 Plans d'entraînement personnalisés")
        st.write("🍎 Conseils nutritionnels adaptés")
        st.write("💬 Coach IA disponible 24/7")
        st.write("📅 Suivi et calendrier interactif")
        st.write("🌤️ Adaptation météo en temps réel")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 Commencer mon parcours", use_container_width=True, key="start_btn"):
            st.session_state.step = "form"
            st.session_state.q_index = 0
            st.rerun()

# Form / Questionnaire
elif st.session_state.step == "form":
    idx = st.session_state.q_index
    
    if idx >= TOTAL_Q:
        st.session_state.step = "dashboard"
        
        profile = {k: st.session_state.answers.get(k) for k in [
            "age", "sexe", "taille_cm", "poids_kg", "niveau_exp", "blessures", "sante",
            "activite", "objectif_principal", "objectif_secondaire", "horizon", "motivation",
            "types_exos", "jours_sem", "duree_min", "moment", "lieu", "materiel",
            "sommeil_h", "ville", "nutrition"
        ]}
        
        if st.session_state.api_key:
            with st.spinner("🤖 Génération de ton plan personnalisé..."):
                plan_text = call_openai_plan(st.session_state.api_key, profile)
                st.session_state.plan_text = plan_text or fallback_plan(profile)
        else:
            st.session_state.plan_text = fallback_plan(profile)
        
        st.session_state._last_plan_hash = hash(st.session_state.plan_text)
        recompute_calendar_events()
        st.rerun()
    
    else:
        q = QUESTIONS[idx]
        
        progress = (idx / TOTAL_Q)
        st.markdown(f"""
        <div class="form-progress">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span>Question {idx + 1} sur {TOTAL_Q}</span>
                <span>{int(progress * 100)}%</span>
            </div>
            <div class="form-progress-bar">
                <div class="form-progress-fill" style="width: {progress * 100}%"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"### {q['label']}")
        if q.get("help"):
            st.info(q["help"])
        
        default_val = st.session_state.answers.get(q["key"])
        answer = render_input(q, default=default_val)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if idx > 0:
                if st.button("⬅️ Précédent", use_container_width=True, key="prev_btn"):
                    st.session_state.q_index -= 1
                    st.rerun()
        
        with col3:
            if st.button("Suivant ➡️", use_container_width=True, key="next_btn"):
                st.session_state.answers[q["key"]] = answer
                st.session_state.q_index += 1
                st.rerun()

# Dashboard / Main App
elif st.session_state.step == "dashboard":
    
    # Page routing
    if st.session_state.page == "profile":
        render_top_navigation("profile")
        st.title("👤 Mon Profil")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Informations personnelles")
            name = st.text_input("Nom", value=st.session_state.user_name, key="profile_name")
            email = st.text_input("Email", value=st.session_state.user_email, key="profile_email")
            dob = st.date_input("Date de naissance", value=st.session_state.user_dob, key="profile_dob")
            gender = st.selectbox("Genre", ["Homme", "Femme", "Autre"], 
                                index=["Homme", "Femme", "Autre"].index(st.session_state.user_gender), 
                                key="profile_gender")
            
            st.session_state.user_name = name
            st.session_state.user_email = email
            st.session_state.user_dob = dob
            st.session_state.user_gender = gender
        
        with col2:
            st.subheader("Objectifs")
            goal = st.selectbox("Type d'objectif", 
                              ["Perte de poids", "Gain musculaire", "Maintien", "Endurance"],
                              index=["Perte de poids", "Gain musculaire", "Maintien", "Endurance"].index(st.session_state.goal_type),
                              key="profile_goal")
            current_w = st.number_input("Poids actuel (kg)", value=st.session_state.current_weight, key="profile_current")
            target_w = st.number_input("Poids cible (kg)", value=st.session_state.target_weight, key="profile_target")
            freq = st.slider("Fréquence d'entraînement (jours/sem)", 1, 7, st.session_state.training_frequency, key="profile_freq")
            duration = st.slider("Durée par séance (min)", 15, 120, st.session_state.training_duration, key="profile_duration")
            
            st.session_state.goal_type = goal
            st.session_state.current_weight = current_w
            st.session_state.target_weight = target_w
            st.session_state.training_frequency = freq
            st.session_state.training_duration = duration
        
        if st.button("💾 Sauvegarder", use_container_width=True, key="save_profile"):
            st.success("✅ Profil mis à jour!")
    
    elif st.session_state.page == "plan":
        render_top_navigation("plan")
        st.title("📋 Mon Plan d'Entraînement")
        
        if st.session_state.plan_text:
            if st.session_state.flash_plan_updated:
                st.success("✅ Plan mis à jour automatiquement!")
                st.session_state.flash_plan_updated = False
            
            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("✏️ Éditer", key="edit_plan_btn"):
                    st.session_state.plan_edit_mode = not st.session_state.plan_edit_mode
                    st.rerun()
            
            if st.session_state.plan_edit_mode:
                edited = st.text_area(
                    "Modifie ton plan",
                    value=st.session_state.plan_text,
                    height=500,
                    key="plan_editor"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Sauvegarder", use_container_width=True, key="save_plan"):
                        st.session_state.plan_text = edited
                        st.session_state.plan_edit_mode = False
                        st.session_state._last_plan_hash = hash(edited)
                        recompute_calendar_events()
                        st.success("✅ Plan sauvegardé!")
                        st.rerun()
                
                with col2:
                    if st.button("❌ Annuler", use_container_width=True, key="cancel_plan"):
                        st.session_state.plan_edit_mode = False
                        st.rerun()
            else:
                st.markdown(st.session_state.plan_text)
        else:
            st.info("Aucun plan disponible. Génère-en un depuis le chat ou le dashboard.")
    
    elif st.session_state.page == "meteo":
        render_top_navigation("meteo")
        st.title("🌤️ Météo & Conseils")
        
        ville = st.session_state.answers.get("ville", "Montreal") or "Montreal"
        weather = get_weather(ville)
        
        st.markdown(f"""
        <div class="weather-card">
            <h2>Météo à {ville}</h2>
            <p class="weather-temp">{weather['temp']}°C</p>
            <p class="weather-condition">{weather['condition']}</p>
            <p>Ressenti: {weather['feels_like']}°C</p>
            <p>Humidité: {weather['humidity']}%</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 💡 Conseils d'entraînement")
        
        duree = int(st.session_state.answers.get("duree_min", 45) or 45)
        geo = geocode_city(ville)
        
        if geo:
            lat, lon, full_name = geo
            weather_json = get_today_weather(lat, lon)
            if weather_json:
                advice = weather_advice(weather_json, duree)
                st.info(advice)
        else:
            st.warning("Impossible de récupérer les prévisions détaillées.")
    
    elif st.session_state.page == "chat":
        render_top_navigation("chat")
        st.title("💬 Chat avec Serge")
        
        chat_container = st.container()
        
        with chat_container:
            for msg in st.session_state.chat_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    st.markdown(f'<div class="chat-message user-message">👤 {content}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message assistant-message">🤖 {content}</div>', unsafe_allow_html=True)
        
        user_input = st.chat_input("Tape ton message...", key="chat_input")
        
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            cmd_result = handle_chat_command(user_input)
            
            if cmd_result["is_command"]:
                response = cmd_result["feedback"]
            else:
                profile = st.session_state.answers
                plan = st.session_state.plan_text
                nutrition = st.session_state.nutrition_plan or ""
                
                response = call_openai_chat(
                    st.session_state.api_key,
                    user_input,
                    profile,
                    plan,
                    nutrition
                )
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
    
    elif st.session_state.page == "calendar":
        render_top_navigation("calendar")
        st.title("📅 Calendrier d'Entraînement")
        
        if not CALENDAR_AVAILABLE:
            st.warning("📦 Module `streamlit-calendar` non installé. Installe-le avec : `pip install streamlit-calendar`")
            
            st.subheader("Sessions planifiées")
            sessions = parse_workout_plan(st.session_state.plan_text)
            
            for session in sessions:
                st.markdown(f"**Jour {session['day']} — {session['title']}**")
                st.write(session['description'][:200] + "...")
                st.markdown("---")
        else:
            start_date = st.date_input(
                "Date de début",
                value=st.session_state.calendar_start_date,
                key="cal_start"
            )
            
            if start_date != st.session_state.calendar_start_date:
                st.session_state.calendar_start_date = start_date
                recompute_calendar_events()
                st.rerun()
            
            if st.button("🔄 Recalculer", key="recalc_cal"):
                recompute_calendar_events()
                st.success("✅ Calendrier mis à jour!")
                st.rerun()
            
            events = st.session_state.calendar_events
            
            if events:
                calendar_options = {
                    "initialView": "dayGridMonth",
                    "headerToolbar": {
                        "left": "prev,next today",
                        "center": "title",
                        "right": "dayGridMonth,timeGridWeek,timeGridDay"
                    },
                    "selectable": True,
                    "editable": False,
                    "locale": "fr"
                }
                
                st_calendar(events=events, options=calendar_options, key="calendar_widget")
            else:
                st.info("Aucun événement planifié. Génère un plan d'abord.")
    
    elif st.session_state.page == "nutrition":
        render_top_navigation("nutrition")
        st.title("🍎 Plan Nutritionnel")
        
        if not st.session_state.nutrition_plan:
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🤖 Générer", key="gen_nutrition"):
                    profile = st.session_state.answers
                    
                    if st.session_state.api_key:
                        with st.spinner("Génération du plan nutritionnel..."):
                            nutrition = call_openai_nutrition(st.session_state.api_key, profile)
                            st.session_state.nutrition_plan = nutrition or fallback_nutrition(profile)
                    else:
                        st.session_state.nutrition_plan = fallback_nutrition(profile)
                    
                    st.rerun()
            
            st.info("Clique sur 'Générer' pour créer ton plan nutritionnel personnalisé.")
        
        else:
            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("✏️ Éditer", key="edit_nutrition_btn"):
                    st.session_state.nutrition_edit_mode = not st.session_state.nutrition_edit_mode
                    st.rerun()
            
            if st.session_state.nutrition_edit_mode:
                edited = st.text_area(
                    "Modifie ton plan nutritionnel",
                    value=st.session_state.nutrition_plan,
                    height=500,
                    key="nutrition_editor"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Sauvegarder", use_container_width=True, key="save_nutrition"):
                        st.session_state.nutrition_plan = edited
                        st.session_state.nutrition_edit_mode = False
                        st.success("✅ Plan nutritionnel sauvegardé!")
                        st.rerun()
                
                with col2:
                    if st.button("❌ Annuler", use_container_width=True, key="cancel_nutrition"):
                        st.session_state.nutrition_edit_mode = False
                        st.rerun()
            else:
                st.markdown(st.session_state.nutrition_plan)
    
    elif st.session_state.page == "workouts":
        render_top_navigation("workouts")
        st.title("🏋️ Historique des Entraînements")
        
        st.subheader("➕ Ajouter une séance")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            workout_date = st.date_input("Date", value=dt.date.today(), key="workout_date")
        
        with col2:
            workout_type = st.text_input("Type", placeholder="Ex: Full Body", key="workout_type")
        
        with col3:
            workout_duration = st.number_input("Durée (min)", min_value=5, max_value=180, value=45, key="workout_duration")
        
        notes = st.text_area("Notes", placeholder="Comment s'est passée la séance?", key="workout_notes")
        
        if st.button("💾 Enregistrer", use_container_width=True, key="save_workout"):
            workout = {
                "date": workout_date.strftime("%Y-%m-%d"),
                "type": workout_type,
                "duration": workout_duration,
                "notes": notes
            }
            st.session_state.workout_history.append(workout)
            st.success("✅ Séance enregistrée!")
            st.rerun()
        
        st.markdown("---")
        st.subheader("📊 Historique")
        
        if st.session_state.workout_history:
            for i, w in enumerate(reversed(st.session_state.workout_history)):
                with st.expander(f"{w['date']} — {w['type']} ({w['duration']} min)"):
                    st.write(f"**Notes:** {w['notes']}")
                    
                    if st.button("🗑️ Supprimer", key=f"del_workout_{i}"):
                        st.session_state.workout_history.remove(w)
                        st.rerun()
        else:
            st.info("Aucune séance enregistrée.")
    
    else:
        # Dashboard principal
        render_top_navigation(None)
        
        st.markdown(f"# 👋 Salut, {st.session_state.user_name}!")
        
        current_date = dt.datetime.now().strftime("%A %d %B %Y")
        st.markdown(f"<p style='color: #666;'>{current_date}</p>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        completed = len(st.session_state.workout_history)
        streak = calculate_streak(st.session_state.workout_history)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{completed}</p>
                <p class="stat-label">Séances complétées</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{streak}</p>
                <p class="stat-label">Série actuelle</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            ville = st.session_state.answers.get("ville", "Montreal") or "Montreal"
            weather = get_weather(ville)
            
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{weather['temp']}°C</p>
                <p class="stat-label">Météo à {ville}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.subheader("📋 Prochain entraînement")
            
            next_workout = get_next_workout(st.session_state.plan_text, st.session_state.last_completed_day)
            
            if next_workout:
                st.markdown(f"""
                <div class="custom-card">
                    <h3>{next_workout['title']}</h3>
                    <p>{next_workout['description'][:200]}...</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("✅ Marquer comme complété", key="complete_workout"):
                    workout = {
                        "date": dt.date.today().strftime("%Y-%m-%d"),
                        "type": next_workout['title'],
                        "duration": int(st.session_state.answers.get("duree_min", 45) or 45),
                        "notes": "Séance complétée"
                    }
                    st.session_state.workout_history.append(workout)
                    st.session_state.last_completed_day = next_workout['day']
                    st.success("🎉 Bravo! Séance enregistrée!")
                    st.rerun()
            else:
                st.info("Aucun entraînement planifié aujourd'hui.")
        
        with col_right:
            st.subheader("💪 Motivation")
            quote = get_daily_quote()
            st.markdown(f"""
            <div class="quote-card">
                "{quote}"
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.subheader("⚡ Actions rapides")
            
            if st.button("📋 Voir mon plan", use_container_width=True, key="quick_plan"):
                st.session_state.page = "plan"
                st.rerun()
            
            if st.button("💬 Parler au coach", use_container_width=True, key="quick_chat"):
                st.session_state.page = "chat"
                st.rerun()
            
            if st.button("🍎 Nutrition", use_container_width=True, key="quick_nutrition"):
                st.session_state.page = "nutrition"
                st.rerun()
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        if st.session_state.workout_history:
            st.subheader("📊 Activité récente")
            
            recent = st.session_state.workout_history[-5:]
            
            for w in reversed(recent):
                cols = st.columns([2, 2, 1])
                with cols[0]:
                    st.write(f"**{w['date']}**")
                with cols[1]:
                    st.write(f"{w['type']}")
                with cols[2]:
                    st.write(f"{w['duration']} min")
        else:
            st.info("Aucune activité récente.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🎯 Progression vers l'objectif")
        
        current = st.session_state.current_weight
        target = st.session_state.target_weight
        diff = current - target
        
        if diff > 0:
            action = "perdre"
        elif diff < 0:
            action = "gagner"
        else:
            action = "maintenir"
        
        st.write(f"Objectif: {abs(diff):.1f} kg à {action}")
        
        if diff != 0:
            # Progression non calculable sans poids de départ : ici on affiche un placeholder
            st.progress(0.0)
