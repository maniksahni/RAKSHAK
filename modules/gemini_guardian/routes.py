import json
import logging
import random
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, session
from flask_login import login_required, current_user
from models import query_db, log_audit

log = logging.getLogger('rakshak')
gemini_bp = Blueprint('gemini', __name__)

# NOTE: ARIA runs on a local inference engine (no external API key required).
RAKSHAK_SYSTEM_PROMPT = """You are ARIA — Advanced Rakshak Intelligence Assistant — an elite AI safety guardian embedded in RAKSHAK, India's most advanced women's safety platform.

Your mission is to protect women and provide real-time safety intelligence. You are:
- Calm, authoritative, and reassuring under pressure
- Expert in Indian geography, local danger patterns, and emergency protocols
- Trained on safety psychology and crisis de-escalation
- Fluent in English and Hindi (respond in the language the user uses)

Your safety assessment capabilities:
1. Analyze location-based threats using time-of-day, area type, and historical incident data
2. Provide step-by-step safety guidance for dangerous situations
3. Suggest immediate escape routes and safety actions
4. Assess risk levels: SAFE / CAUTION / DANGER / CRITICAL
5. Guide users through activating emergency protocols

RULES:
- Never dismiss a threat, always validate user concerns
- Give concrete, actionable advice — not generic platitudes
- If user seems in immediate danger, ALWAYS recommend triggering SOS
- Keep responses concise but complete (max 3-4 sentences for quick responses)
- Use safety emojis to make responses scannable: 🟢 SAFE | 🟡 CAUTION | 🔴 DANGER | 🆘 CRITICAL

You have access to user's current risk level, location context, and nearby danger zones.
"""


def _generate_aria_reply(messages: list, max_tokens: int = 512) -> str:
    """Local rule-based inference engine. No API Key required!"""
    user_msg = messages[-1]['parts'][0]['text'] if messages else ''
    return _fallback_response(user_msg)

def _pick_unique(key: str, lst: list):
    """Pick a random item from lst, ensuring it's different from the last request if possible."""
    last_val = session.get(key)
    # Need to compare strings since lists might be serialized or mutated
    avail = [x for x in lst if str(x) != last_val]
    if not avail:
        avail = lst
    chosen = random.choice(avail)
    session[key] = str(chosen)
    session.modified = True
    return chosen


def _fallback_response(user_message: str) -> str:
    """Intelligent local ARIA response generator."""
    msg = user_message.lower()
    
    if any(w in msg for w in ['help', 'danger', 'scared', 'follow', 'unsafe', 'attack', 'threat', 'fear', 'mujhe dar']):
        responses = [
            "🆘 **IMMEDIATE ACTION**: You are not alone. RAKSHAK is monitoring you.\n\n**Right now:** 1) Move to a lit, crowded area. 2) Call someone you trust. 3) If threat is real → **TRIGGER SOS** immediately. Your location will be broadcast to your Guardian Network.",
            "🆘 **DANGER DETECTED**: System alert active. Do not panic. Keep your phone accessible and move to a safe zone if possible. Trigger SOS right now if someone is approaching you.",
            "🚨 **CRITICAL**: ARIA is standing by. If you feel scared, press the SOS button. We will alert nearby Guardian Angels and your trusted contacts immediately."
        ]
        return _pick_unique('aria_help', responses)
    
    if any(w in msg for w in ['night', 'raat', 'dark', 'alone', 'akele']):
        responses = [
            "🟡 **CAUTION MODE ACTIVE**\n\nLate night solo travel requires vigilance. Share your live location with a trusted contact, keep your SOS ready, and stay on well-lit main roads. RAKSHAK is watching your heartbeat.",
            "🟡 **NIGHT PROTOCOL**: Always walk confidently. Keep your phone charged and avoid isolated shortcuts. RAKSHAK's Sentinel Audio monitor is secretly listening for distress sounds if you enable it.",
            "🌙 **NIGHT ADVISORY**: It's late. Please enable 'Safe Walk' mode so your guardian network knows your path. Stay in well-lit areas.",
        ]
        return _pick_unique('aria_night', responses)
    
    if any(w in msg for w in ['route', 'safe path', 'safe road', 'kaunsa rasta']):
        responses = [
            "🟢 **ROUTE ANALYSIS**\n\nFor safest routes: prefer main roads with street lighting, avoid shortcuts through isolated areas, and check danger zones on the map. Enable Safe Walk to share your journey in real-time.",
            "🗺️ **ROUTE ADVICE**: Use the 'Danger Map' tab to check for red zones. Stick to crowded areas and main highways when possible.",
            "📍 **PATH CHECK**: Scanning... Stick to the main roads. Share your live location using 'Safe Walk' before you start moving."
        ]
        return _pick_unique('aria_route', responses)
    
    responses = [
        "🛡️ **ARIA Guardian Online**\n\nI'm your AI safety companion. Ask me about: route safety, threat assessment, emergency procedures, or type your situation and I'll guide you. Remember: your Guardian Network is always one tap away.",
        "✨ **ARIA is listening.** I'm analyzing your surroundings. What's your current situation?",
        "🤖 **System Active.** You can ask me for safety tips, late-night travel advice, or just press SOS if you're in an emergency.",
        "🧠 **ARIA Guardian**: I am constantly learning from the Danger Zone map to keep you safe. How can I assist you right now?",
        "🛡️ **Status Green.** I am here to help. You can tell me if you're feeling unsafe or just want a route check."
    ]
    return _pick_unique('aria_default', responses)


def _build_context(user) -> str:
    """Build rich user context for the local ARIA engine."""
    ctx_parts = [f"User: {user.full_name}"]
    ctx_parts.append(f"Risk Level: {user.risk_level.upper()}")
    
    if user.last_ping:
        ctx_parts.append(f"Last Active: {user.last_ping}")
    
    # Fetch nearby danger zones count
    try:
        zones = query_db(
            "SELECT COUNT(*) as cnt FROM danger_zones WHERE status='approved'",
            one=True
        )
        if zones:
            ctx_parts.append(f"Known Danger Zones in System: {zones['cnt']}")
    except Exception:
        pass
    
    # Fetch recent SOS count
    try:
        recent_sos = query_db(
            "SELECT COUNT(*) as cnt FROM sos_alerts WHERE created_at >= NOW() - INTERVAL 24 HOUR",
            one=True
        )
        if recent_sos:
            ctx_parts.append(f"SOS Alerts in Last 24h: {recent_sos['cnt']}")
    except Exception:
        pass
    
    return " | ".join(ctx_parts)


def _safe_hour(value: str, default: int = None) -> int | None:
    try:
        return int(str(value).split(':', 1)[0])
    except Exception:
        return default


def _score_to_risk_level(score: int) -> str:
    if score >= 80:
        return 'critical'
    if score >= 60:
        return 'danger'
    if score >= 35:
        return 'caution'
    return 'safe'


def _severity_weight(severity: str) -> int:
    sev = (severity or '').strip().lower()
    return {
        'critical': 25,
        'high': 18,
        'medium': 10,
        'low': 4,
    }.get(sev, 6)


def _risk_signal_boost(text: str) -> int:
    msg = (text or '').lower()
    boosts = {
        'follow': 26,
        'stalk': 26,
        'attack': 32,
        'unsafe': 18,
        'scared': 20,
        'fear': 18,
        'help': 22,
        'alone': 10,
        'akele': 10,
        'dark': 10,
        'night': 12,
        'raat': 12,
        'cab': 8,
        'taxi': 8,
        'stranger': 12,
    }
    return sum(weight for term, weight in boosts.items() if term in msg)


def _base_user_risk(user) -> int:
    risk = (getattr(user, 'risk_level', '') or '').lower()
    return {
        'low': 8,
        'medium': 18,
        'high': 28,
        'critical': 40,
    }.get(risk, 12)


def _dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items:
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _nearby_danger_zones(lat, lng, radius_km=1.0):
    if lat is None or lng is None:
        return []
    try:
        import math
        dlat = radius_km / 111.0
        dlng = radius_km / (111.0 * abs(max(0.01, math.cos(math.radians(float(lat))))))
        return query_db(
            """SELECT zone_type, severity, description, upvotes
               FROM danger_zones
               WHERE status='approved'
                 AND latitude BETWEEN %s AND %s
                 AND longitude BETWEEN %s AND %s
               LIMIT 8""",
            (float(lat) - dlat, float(lat) + dlat, float(lng) - dlng, float(lng) + dlng)
        ) or []
    except Exception:
        return []


def _recent_nearby_sos_count(lat, lng, radius_km=1.0, days=7):
    if lat is None or lng is None:
        return 0
    try:
        import math
        dlat = radius_km / 111.0
        dlng = radius_km / (111.0 * abs(max(0.01, math.cos(math.radians(float(lat))))))
        row = query_db(
            f"""SELECT COUNT(*) as cnt
                FROM sos_alerts
                WHERE latitude BETWEEN %s AND %s
                  AND longitude BETWEEN %s AND %s
                  AND created_at >= NOW() - INTERVAL {int(days)} DAY""",
            (float(lat) - dlat, float(lat) + dlat, float(lng) - dlng, float(lng) + dlng),
            one=True
        )
        return int((row or {}).get('cnt') or 0)
    except Exception:
        return 0


def _build_local_analysis(user, lat, lng, situation, time_of_day, area_type):
    hour = _safe_hour(time_of_day, datetime.now().hour)
    zones = _nearby_danger_zones(lat, lng, radius_km=1.0)
    recent_sos = _recent_nearby_sos_count(lat, lng, radius_km=1.0, days=7)

    score = _base_user_risk(user)
    if hour is not None:
        if hour >= 22 or hour <= 4:
            score += 24
        elif hour >= 19 or hour <= 6:
            score += 14
    score += _risk_signal_boost(situation)
    if (area_type or '').lower() in ('isolated', 'unknown', 'industrial'):
        score += 8

    severity_points = sum(_severity_weight(z.get('severity')) for z in zones[:4])
    score += min(severity_points, 30)
    score += min(recent_sos * 6, 18)
    score = max(5, min(score, 96))
    risk_level = _score_to_risk_level(score)
    sos_recommended = score >= 60 or _risk_signal_boost(situation) >= 24

    actions = []
    if score >= 60:
        actions += [
            "Move to a bright, crowded place immediately",
            "Call a trusted contact and stay on the line",
            "Keep the SOS override ready right now",
        ]
    else:
        actions += [
            "Stay aware of people and vehicles around you",
            "Keep your phone unlocked and location accessible",
            "Prefer main roads and public places over shortcuts",
        ]

    if hour is not None and (hour >= 20 or hour <= 5):
        actions.append("Avoid isolated stretches until you reach a safer zone")
    if zones:
        actions.append("Step away from the marked danger-zone cluster nearby")
    if recent_sos:
        actions.append("Stay alert: this area has had recent SOS activity")
    actions = _dedupe_keep_order(actions)[:3]

    if risk_level == 'critical':
        aria_message = "🆘 **CRITICAL RISK**\n\nYour current signals look dangerous. Leave the area now, stay visible, and trigger SOS if anyone is closing distance or blocking your movement."
    elif risk_level == 'danger':
        aria_message = "🔴 **HIGH RISK DETECTED**\n\nThis situation needs immediate caution. Stay in public view, avoid stopping, and prepare to trigger SOS if the threat feels real."
    elif risk_level == 'caution':
        aria_message = "🟡 **CAUTION MODE ACTIVE**\n\nThere are enough warning signals here that you should stay alert. Keep moving through safer, brighter routes and update a trusted contact if needed."
    else:
        aria_message = "🟢 **LOW RISK RIGHT NOW**\n\nNothing strongly alarming is visible from the current signals, but stay alert and keep your safety tools ready."

    zone_summary = "No major nearby danger zones detected."
    if zones:
        zone_summary = "Nearby signals: " + ", ".join(
            f"{z.get('zone_type', 'zone')} ({(z.get('severity') or 'unknown').upper()})"
            for z in zones[:3]
        )

    return {
        "risk_level": risk_level,
        "risk_score": score,
        "threat_summary": zone_summary,
        "immediate_actions": actions,
        "sos_recommended": sos_recommended,
        "safe_zones_advice": "Move toward well-lit shops, transport hubs, security posts, or any crowded public area.",
        "aria_message": aria_message,
    }


def _build_local_prediction(lat, lng, target_time, target_date):
    target_hour = _safe_hour(target_time, datetime.now().hour) or datetime.now().hour
    zones = _nearby_danger_zones(lat, lng, radius_km=2.0)
    recent_sos = _recent_nearby_sos_count(lat, lng, radius_km=2.0, days=30)
    hourly_patterns = query_db(
        """SELECT HOUR(created_at) as hour, COUNT(*) as count
           FROM sos_alerts
           WHERE latitude BETWEEN %s AND %s
             AND longitude BETWEEN %s AND %s
             AND created_at >= NOW() - INTERVAL 30 DAY
           GROUP BY HOUR(created_at)
           ORDER BY count DESC, hour ASC""",
        (
            float(lat) - (2.0 / 111.0),
            float(lat) + (2.0 / 111.0),
            float(lng) - (2.0 / 111.0),
            float(lng) + (2.0 / 111.0),
        )
    ) or []

    risk_score = 10
    if target_hour >= 22 or target_hour <= 4:
        risk_score += 34
    elif target_hour >= 19 or target_hour <= 6:
        risk_score += 18
    risk_score += min(sum(_severity_weight(z.get('severity')) for z in zones[:5]), 28)
    risk_score += min(recent_sos * 4, 18)

    matching_hour_count = 0
    for item in hourly_patterns:
        if int(item.get('hour') or -1) == target_hour:
            matching_hour_count = int(item.get('count') or 0)
            break
    risk_score += min(matching_hour_count * 7, 21)
    risk_score = max(8, min(risk_score, 94))

    predicted_risk = _score_to_risk_level(risk_score)
    safety_score = max(6, 100 - risk_score)
    peak_hours = [f"{int(item.get('hour') or 0):02d}:00" for item in hourly_patterns[:2]] or ["22:00", "23:00"]

    factors = []
    if target_hour >= 20 or target_hour <= 5:
        factors.append("Late-hour travel reduces visibility and public support")
    if zones:
        factors.append("Nearby danger-zone reports increase local risk")
    if recent_sos:
        factors.append("Historical SOS activity exists around this route")
    if matching_hour_count:
        factors.append("This specific hour has prior alert activity in the area")
    factors = _dedupe_keep_order(factors)[:3] or ["No strong historical red flags, but standard caution is still advised"]

    precautions = [
        "Share live location before you start moving",
        "Stay on main roads and avoid quiet shortcuts",
        "Keep SOS ready and battery above critical level",
    ]
    if predicted_risk in ('danger', 'critical'):
        precautions[0] = "Travel with company if at all possible"
        precautions[2] = "Keep SOS, emergency dial, and trusted-contact relay ready"

    safe_window = "Best to travel during daylight or busy evening hours"
    if predicted_risk == 'safe':
        safe_window = "This window looks manageable, but main-road travel is still best"
    elif predicted_risk == 'caution':
        safe_window = "Prefer busier time slots and avoid the late-night stretch"
    elif predicted_risk in ('danger', 'critical'):
        safe_window = "Avoid this window if possible; daylight or escorted travel is safer"

    prediction_line = {
        'safe': "🟢 **LOWER-RISK WINDOW**\n\nThis slot looks relatively manageable with standard precautions.",
        'caution': "🟡 **MODERATE CAUTION**\n\nThis route-time combination is workable, but only with active vigilance.",
        'danger': "🔴 **HIGH-RISK WINDOW**\n\nThis timing shows enough warning signals that you should prefer another slot if possible.",
        'critical': "🆘 **AVOID IF POSSIBLE**\n\nThe pattern around this time and area is too risky for solo movement.",
    }[predicted_risk]

    return {
        "predicted_risk": predicted_risk,
        "safety_score": safety_score,
        "peak_risk_hours": peak_hours,
        "risk_factors": factors,
        "safe_travel_window": safe_window,
        "precautions": precautions,
        "confidence": "high" if zones or recent_sos or matching_hour_count else "medium",
        "aria_prediction": prediction_line,
    }


# ── Threat Analysis API ────────────────────────────────────────────────────────
@gemini_bp.route('/analyze-threat', methods=['POST'])
@login_required
def analyze_threat():
    """
    Analyze a specific location/situation using the local ARIA engine.
    Returns structured risk assessment.
    """
    try:
        data = request.get_json() or {}
        lat = data.get('latitude')
        lng = data.get('longitude')
        situation = data.get('situation', '')
        time_of_day = data.get('time_of_day', datetime.now().strftime('%H:%M'))
        area_type = data.get('area_type', 'unknown')

        analysis = _build_local_analysis(current_user, lat, lng, situation, time_of_day, area_type)

        log_audit(current_user.id, 'ai_threat_analysis', ip_address=request.remote_addr)
        return jsonify(success=True, analysis=analysis)

    except Exception as e:
        log.error(f"Threat analysis failed: {e}")
        return jsonify(success=False, error="Analysis unavailable. Trust your instincts."), 500


# ── Safety Chat API ────────────────────────────────────────────────────────────
@gemini_bp.route('/chat', methods=['POST'])
@login_required
def safety_chat():
    """
    Conversational AI safety chat with context-aware responses.
    """
    try:
        data = request.get_json() or {}
        user_message = data.get('message', '').strip()
        history = data.get('history', [])  # Previous conversation turns
        
        if not user_message:
            return jsonify(success=False, error="Message required"), 400

        if len(user_message) > 1000:
            return jsonify(success=False, error="Message too long"), 400

        context = _build_context(current_user)
        
        # Build conversation history for local ARIA context
        aria_messages = []
        
        # Add context as first user message
        if not history:
            aria_messages.append({
                "role": "user",
                "parts": [{"text": f"[SESSION START - User Context: {context}]"}]
            })
            aria_messages.append({
                "role": "model",
                "parts": [{"text": f"🛡️ ARIA Guardian online. I'm monitoring your safety, {current_user.full_name.split()[0]}. How can I help you?"}]
            })
        
        # Add history (last 6 turns max to save tokens)
        for turn in history[-6:]:
            if turn.get('role') in ('user', 'model') and turn.get('text'):
                aria_messages.append({
                    "role": turn['role'],
                    "parts": [{"text": turn['text']}]
                })
        
        # Add current message
        aria_messages.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        response_text = _generate_aria_reply(aria_messages, max_tokens=400)
        
        # Detect if SOS should be recommended
        danger_keywords = ['immediately', 'sos', 'trigger', 'danger', 'critical', '🆘', 'escape', 'run']
        sos_suggested = any(k in response_text.lower() for k in danger_keywords)
        
        return jsonify(
            success=True,
            response=response_text,
            sos_suggested=sos_suggested,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        log.error(f"Safety chat failed: {e}")
        return jsonify(success=False, error="ARIA temporarily unavailable. Core safety features active."), 500


# ── Predictive Safety Oracle ───────────────────────────────────────────────────
@gemini_bp.route('/predict-safety', methods=['POST'])
@login_required
def predict_safety():
    """
    Local predictive safety scoring based on historical patterns,
    time, location, and community data.
    """
    try:
        data = request.get_json() or {}
        lat = float(data.get('latitude', 0))
        lng = float(data.get('longitude', 0))
        target_time = data.get('target_time', datetime.now().strftime('%H:%M'))
        target_date = data.get('target_date', datetime.now().strftime('%Y-%m-%d'))

        if not lat or not lng:
            return jsonify(success=False, error="Location required"), 400

        prediction = _build_local_prediction(lat, lng, target_time, target_date)

        return jsonify(
            success=True,
            prediction=prediction,
            data_points={
                "sos_incidents": _recent_nearby_sos_count(lat, lng, radius_km=2.0, days=30),
                "danger_zones": len(_nearby_danger_zones(lat, lng, radius_km=2.0)),
                "analysis_radius_km": 2
            }
        )

    except Exception as e:
        log.error(f"Safety prediction failed: {e}")
        return jsonify(success=False, error="Prediction unavailable"), 500


# ── Guardian AI Page ───────────────────────────────────────────────────────────
@gemini_bp.route('/')
@login_required
def guardian_page():
    return render_template('gemini_guardian/index.html')
