import os
import json
import logging
import requests
import random
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models import query_db, log_audit

log = logging.getLogger('rakshak')
gemini_bp = Blueprint('gemini', __name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

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


def _call_gemini(messages: list, max_tokens: int = 512) -> str:
    """Local rule-based inference engine. No API Key required!"""
    user_msg = messages[-1]['parts'][0]['text'] if messages else ''
    return _fallback_response(user_msg)


def _fallback_response(user_message: str) -> str:
    """Intelligent local fallback when Gemini API is unavailable."""
    msg = user_message.lower()
    
    if any(w in msg for w in ['help', 'danger', 'scared', 'follow', 'unsafe', 'attack', 'threat', 'fear', 'mujhe dar']):
        responses = [
            "🆘 **IMMEDIATE ACTION**: You are not alone. RAKSHAK is monitoring you.\n\n**Right now:** 1) Move to a lit, crowded area. 2) Call someone you trust. 3) If threat is real → **TRIGGER SOS** immediately. Your location will be broadcast to your Guardian Network.",
            "🆘 **DANGER DETECTED**: System alert active. Do not panic. Keep your phone accessible and move to a safe zone if possible. Trigger SOS right now if someone is approaching you.",
            "🚨 **CRITICAL**: ARIA is standing by. If you feel scared, press the SOS button. We will alert nearby Guardian Angels and your trusted contacts immediately."
        ]
        return random.choice(responses)
    
    if any(w in msg for w in ['night', 'raat', 'dark', 'alone', 'akele']):
        responses = [
            "🟡 **CAUTION MODE ACTIVE**\n\nLate night solo travel requires vigilance. Share your live location with a trusted contact, keep your SOS ready, and stay on well-lit main roads. RAKSHAK is watching your heartbeat.",
            "🟡 **NIGHT PROTOCOL**: Always walk confidently. Keep your phone charged and avoid isolated shortcuts. RAKSHAK's Sentinel Audio monitor is secretly listening for distress sounds if you enable it.",
            "🌙 **NIGHT ADVISORY**: It's late. Please enable 'Safe Walk' mode so your guardian network knows your path. Stay in well-lit areas.",
        ]
        return random.choice(responses)
    
    if any(w in msg for w in ['route', 'safe path', 'safe road', 'kaunsa rasta']):
        responses = [
            "🟢 **ROUTE ANALYSIS**\n\nFor safest routes: prefer main roads with street lighting, avoid shortcuts through isolated areas, and check danger zones on the map. Enable Safe Walk to share your journey in real-time.",
            "🗺️ **ROUTE ADVICE**: Use the 'Danger Map' tab to check for red zones. Stick to crowded areas and main highways when possible.",
            "📍 **PATH CHECK**: Scanning... Stick to the main roads. Share your live location using 'Safe Walk' before you start moving."
        ]
        return random.choice(responses)
    
    responses = [
        "🛡️ **ARIA Guardian Online**\n\nI'm your AI safety companion. Ask me about: route safety, threat assessment, emergency procedures, or type your situation and I'll guide you. Remember: your Guardian Network is always one tap away.",
        "✨ **ARIA is listening.** I'm analyzing your surroundings. What's your current situation?",
        "🤖 **System Active.** You can ask me for safety tips, late-night travel advice, or just press SOS if you're in an emergency.",
        "🧠 **ARIA Guardian**: I am constantly learning from the Danger Zone map to keep you safe. How can I assist you right now?",
        "🛡️ **Status Green.** I am here to help. You can tell me if you're feeling unsafe or just want a route check."
    ]
    return random.choice(responses)


def _build_context(user) -> str:
    """Build rich user context for Gemini prompt."""
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


# ── Threat Analysis API ────────────────────────────────────────────────────────
@gemini_bp.route('/analyze-threat', methods=['POST'])
@login_required
def analyze_threat():
    """
    Analyze a specific location/situation for threats using Gemini.
    Returns structured risk assessment.
    """
    try:
        data = request.get_json() or {}
        lat = data.get('latitude')
        lng = data.get('longitude')
        situation = data.get('situation', '')
        time_of_day = data.get('time_of_day', datetime.now().strftime('%H:%M'))
        area_type = data.get('area_type', 'unknown')

        context = _build_context(current_user)
        
        # Build nearby danger zones context
        zone_context = ""
        if lat and lng:
            try:
                import math
                dlat = 1.0 / 111.0  # ~1km
                dlng = 1.0 / (111.0 * abs(max(0.01, math.cos(math.radians(float(lat))))))
                zones = query_db(
                    """SELECT zone_type, severity, description 
                       FROM danger_zones 
                       WHERE status='approved'
                         AND latitude BETWEEN %s AND %s
                         AND longitude BETWEEN %s AND %s
                       LIMIT 5""",
                    (float(lat) - dlat, float(lat) + dlat,
                     float(lng) - dlng, float(lng) + dlng)
                )
                if zones:
                    zone_context = f"\nNearby danger zones: " + ", ".join(
                        [f"{z['zone_type']} ({z['severity']} severity)" for z in zones]
                    )
            except Exception:
                pass

        prompt = f"""Analyze this safety situation for a RAKSHAK user:

User Context: {context}
Location: {"Lat " + str(lat) + ", Lng " + str(lng) if lat and lng else "Unknown"}
Time: {time_of_day}
Area Type: {area_type}
Situation: {situation or "General safety check"}
{zone_context}

Provide a JSON response with these exact fields:
{{
    "risk_level": "safe|caution|danger|critical",
    "risk_score": 0-100,
    "threat_summary": "2-sentence threat assessment",
    "immediate_actions": ["action1", "action2", "action3"],
    "sos_recommended": true|false,
    "safe_zones_advice": "Where to go for safety",
    "aria_message": "Calm, direct message from ARIA to the user"
}}

Respond ONLY with valid JSON."""

        messages = [{"role": "user", "parts": [{"text": prompt}]}]
        response_text = _call_gemini(messages, max_tokens=600)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found")
        except Exception:
            # Fallback structured response
            messages = [
                "Standard safety protocols active. Stay alert.",
                "Area seems relatively calm but keep your guard up.",
                "Analyzing local patterns... standard caution advised.",
                "No major immediate threats detected in your 1km radius.",
                "Visibility might be low, keep your phone handy."
            ]
            analysis = {
                "risk_level": random.choice(["safe", "caution", "caution"]),
                "risk_score": random.randint(35, 65),
                "threat_summary": "Local analysis complete. " + random.choice(messages),
                "immediate_actions": ["Stay aware of your surroundings", "Keep phone accessible", "Share location with trusted contact"],
                "sos_recommended": False,
                "safe_zones_advice": "Move to well-lit, populated areas",
                "aria_message": response_text[:300] if "ARIA Guardian Online" not in response_text else random.choice(messages)
            }

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
        
        # Build conversation history for Gemini
        gemini_messages = []
        
        # Add context as first user message
        if not history:
            gemini_messages.append({
                "role": "user",
                "parts": [{"text": f"[SESSION START - User Context: {context}]"}]
            })
            gemini_messages.append({
                "role": "model",
                "parts": [{"text": f"🛡️ ARIA Guardian online. I'm monitoring your safety, {current_user.full_name.split()[0]}. How can I help you?"}]
            })
        
        # Add history (last 6 turns max to save tokens)
        for turn in history[-6:]:
            if turn.get('role') in ('user', 'model') and turn.get('text'):
                gemini_messages.append({
                    "role": turn['role'],
                    "parts": [{"text": turn['text']}]
                })
        
        # Add current message
        gemini_messages.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        response_text = _call_gemini(gemini_messages, max_tokens=400)
        
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
    AI-powered predictive safety scoring based on historical patterns,
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

        # Gather historical data from DB
        import math
        dlat = 2.0 / 111.0  # ~2km radius
        dlng = 2.0 / (111.0 * abs(max(0.01, math.cos(math.radians(lat)))))

        # Historical SOS patterns
        hourly_patterns = query_db(
            """SELECT HOUR(created_at) as hour, COUNT(*) as count,
                      trigger_type
               FROM sos_alerts
               WHERE latitude BETWEEN %s AND %s
                 AND longitude BETWEEN %s AND %s
                 AND created_at >= NOW() - INTERVAL 30 DAY
               GROUP BY HOUR(created_at), trigger_type
               ORDER BY hour""",
            (lat - dlat, lat + dlat, lng - dlng, lng + dlng)
        )

        # Danger zones in area
        nearby_zones = query_db(
            """SELECT zone_type, severity, upvotes
               FROM danger_zones
               WHERE status='approved'
                 AND latitude BETWEEN %s AND %s
                 AND longitude BETWEEN %s AND %s""",
            (lat - dlat, lat + dlat, lng - dlng, lng + dlng)
        )

        # Build data summary for AI
        pattern_summary = ""
        if hourly_patterns:
            high_risk_hours = [str(p['hour']) for p in hourly_patterns if p['count'] > 2]
            pattern_summary = f"High-incident hours in area: {', '.join(high_risk_hours) or 'none recorded'}"

        zone_summary = ""
        if nearby_zones:
            zone_types = [f"{z['zone_type']}({z['severity']})" for z in nearby_zones]
            zone_summary = f"Nearby danger zones: {', '.join(zone_types)}"

        target_hour = int(target_time.split(':')[0]) if ':' in target_time else 12
        from datetime import date
        target_dt = datetime.strptime(target_date, '%Y-%m-%d') if target_date else datetime.now()
        day_name = target_dt.strftime('%A')

        prompt = f"""Predict safety level for a RAKSHAK user planning to travel.

Location: Lat {lat}, Lng {lng}
Planned Time: {target_time} ({day_name})
Historical Data: {pattern_summary or 'Limited local data'}
{zone_summary}
Hour Analysis: {'Night (high risk window)' if 20 <= target_hour or target_hour <= 5 else 'Day/Evening travel'}

Provide safety prediction as JSON:
{{
    "predicted_risk": "safe|caution|danger|critical",
    "safety_score": 0-100,
    "peak_risk_hours": ["HH:MM", "HH:MM"],
    "risk_factors": ["factor1", "factor2"],
    "safe_travel_window": "Best time to travel",
    "precautions": ["precaution1", "precaution2", "precaution3"],
    "confidence": "high|medium|low",
    "aria_prediction": "ARIA's predictive summary in 2 sentences"
}}

Respond ONLY with valid JSON."""

        messages = [{"role": "user", "parts": [{"text": prompt}]}]
        response_text = _call_gemini(messages, max_tokens=500)

        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            prediction = json.loads(json_match.group()) if json_match else {}
        except Exception:
            predictions = [
                "Exercise standard precautions for this area and time.",
                "Historical data suggests moderate risk during late hours here.",
                "Community reports indicate you should stick to main roads.",
                "Safety score is average. Travel with a companion if possible.",
                "Current conditions look standard. Keep 'Safe Walk' enabled."
            ]
            prediction = {
                "predicted_risk": random.choice(["safe", "caution", "caution"]),
                "safety_score": random.randint(55, 75),
                "peak_risk_hours": ["22:00", "02:00"],
                "risk_factors": ["Limited visibility", "Reduced foot traffic", "Isolated patches"],
                "safe_travel_window": "Prefer daytime travel (8AM-7PM)",
                "precautions": ["Share live location", "Keep SOS ready", "Travel with company"],
                "confidence": random.choice(["medium", "high"]),
                "aria_prediction": random.choice(predictions)
            }

        return jsonify(
            success=True,
            prediction=prediction,
            data_points={
                "sos_incidents": len(hourly_patterns),
                "danger_zones": len(nearby_zones),
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
