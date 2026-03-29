from flask import Blueprint, render_template, jsonify
from flask_login import login_required

emergency_bp = Blueprint('emergency', __name__)

# ── Hardcoded Emergency Numbers (India) ────────────────────────────────────
EMERGENCY_NUMBERS = [
    {
        "id": 1,
        "name": "Police",
        "number": "100",
        "icon": "🚔",
        "description": "For any crime, threat, or law and order emergency. Available 24/7 across India.",
        "priority": 1,
        "color": "#b8860b",
    },
    {
        "id": 2,
        "name": "Women Helpline",
        "number": "1091",
        "icon": "👩‍🦰",
        "description": "Dedicated helpline for women in distress. Report harassment, stalking, domestic violence, or any threat.",
        "priority": 1,
        "color": "#e11d48",
    },
    {
        "id": 3,
        "name": "Women Helpline (NCW)",
        "number": "7827170170",
        "icon": "🛡️",
        "description": "National Commission for Women helpline. For complaints, legal advice, and support for women's rights.",
        "priority": 2,
        "color": "#db2777",
    },
    {
        "id": 4,
        "name": "Ambulance",
        "number": "102",
        "icon": "🚑",
        "description": "Medical emergency ambulance service. Free government ambulance available nationwide.",
        "priority": 2,
        "color": "#f59e0b",
    },
    {
        "id": 5,
        "name": "Fire Brigade",
        "number": "101",
        "icon": "🚒",
        "description": "Fire and rescue services. Also responds to building collapses and rescue operations.",
        "priority": 2,
        "color": "#ea580c",
    },
    {
        "id": 6,
        "name": "Child Helpline",
        "number": "1098",
        "icon": "👶",
        "description": "For children in distress. Report child abuse, trafficking, or any threat to a child's safety.",
        "priority": 2,
        "color": "#8b5cf6",
    },
    {
        "id": 7,
        "name": "Domestic Violence",
        "number": "181",
        "icon": "🏠",
        "description": "Women in distress due to domestic violence. Provides immediate assistance, shelter info, and legal aid.",
        "priority": 1,
        "color": "#ec4899",
    },
    {
        "id": 8,
        "name": "Cyber Crime",
        "number": "1930",
        "icon": "💻",
        "description": "Report cyberstalking, online harassment, financial fraud, and all forms of cybercrime.",
        "priority": 2,
        "color": "#3b82f6",
    },
    {
        "id": 9,
        "name": "Senior Citizen",
        "number": "14567",
        "icon": "👴",
        "description": "Helpline for senior citizens facing abuse, neglect, or any safety concern.",
        "priority": 3,
        "color": "#14b8a6",
    },
    {
        "id": 10,
        "name": "Anti-Stalking",
        "number": "1091",
        "icon": "👁️",
        "description": "Report stalking incidents. Available 24/7. Shares the Women Helpline number for immediate response.",
        "priority": 2,
        "color": "#d4af37",
    },
]


@emergency_bp.route('/')
@login_required
def index():
    """Emergency quick-dial panel page."""
    return render_template(
        'dashboard/emergency.html',
        numbers=EMERGENCY_NUMBERS,
    )


@emergency_bp.route('/numbers')
@login_required
def numbers():
    """JSON API returning emergency numbers."""
    return jsonify(success=True, numbers=EMERGENCY_NUMBERS)
