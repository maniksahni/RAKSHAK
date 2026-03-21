import random
from datetime import date
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required

safety_tips_bp = Blueprint('safety_tips', __name__)

# ── Hardcoded Safety Tips Database ─────────────────────────────────────────
SAFETY_TIPS = [
    # ── Walking Alone ──────────────────────────────────────────────────────
    {
        "id": 1, "category": "Walking Alone", "icon": "🚶‍♀️", "priority": 1,
        "title": "Stay in Well-Lit Areas at Night",
        "content": "Always choose well-lit, populated streets when walking at night. Avoid shortcuts through dark alleys, parks, or deserted areas. Street lighting deters potential attackers and ensures witnesses are nearby."
    },
    {
        "id": 2, "category": "Walking Alone", "icon": "🚶‍♀️", "priority": 2,
        "title": "Stay Alert — Remove Headphones",
        "content": "Avoid wearing headphones or being engrossed in your phone while walking alone. Stay aware of your surroundings and trust your instincts. If something feels wrong, change direction immediately and head toward a crowded area."
    },
    {
        "id": 3, "category": "Walking Alone", "icon": "🚶‍♀️", "priority": 2,
        "title": "Plan Your Route in Advance",
        "content": "Before heading out, plan your route and share it with a trusted contact. Use well-known, busy roads. Avoid varying your routine predictably — change routes periodically so you are not easy to track."
    },
    {
        "id": 4, "category": "Walking Alone", "icon": "🚶‍♀️", "priority": 3,
        "title": "Walk Confidently and Purposefully",
        "content": "Walk with confidence, head held high, and make brief eye contact with people around you. Attackers are more likely to target someone who appears distracted or vulnerable. A confident posture signals awareness."
    },
    {
        "id": 5, "category": "Walking Alone", "icon": "🚶‍♀️", "priority": 1,
        "title": "Share Live Location with Trusted Contacts",
        "content": "Use RAKSHAK or your phone's built-in location sharing to let a trusted contact track your real-time location when walking alone, especially at night. This ensures someone always knows where you are."
    },

    # ── Public Transport ───────────────────────────────────────────────────
    {
        "id": 6, "category": "Public Transport", "icon": "🚌", "priority": 1,
        "title": "Sit Near the Driver or Exit Doors",
        "content": "When using buses or metro, sit near the driver, conductor, or close to exit doors. These positions give you quick escape routes and keep you visible to authority figures on the vehicle."
    },
    {
        "id": 7, "category": "Public Transport", "icon": "🚌", "priority": 2,
        "title": "Stay Alert on Your Commute",
        "content": "Keep your belongings close and stay aware of who is around you. Avoid falling asleep on public transport, especially during late hours. Note the vehicle number and share it with someone before boarding."
    },
    {
        "id": 8, "category": "Public Transport", "icon": "🚌", "priority": 1,
        "title": "Verify Ride-Share Details Before Boarding",
        "content": "When using ride-sharing apps, always verify the driver's name, photo, car model, and license plate before getting in. Share your trip details with a trusted contact. Never get into an unmarked or unverified vehicle."
    },
    {
        "id": 9, "category": "Public Transport", "icon": "🚌", "priority": 2,
        "title": "Avoid Empty Compartments",
        "content": "Never board an empty bus, train compartment, or auto-rickshaw at night. Wait for a vehicle with other passengers. If you find yourself alone and uncomfortable, get off at the next well-lit stop."
    },
    {
        "id": 10, "category": "Public Transport", "icon": "🚌", "priority": 3,
        "title": "Keep Emergency Numbers Ready",
        "content": "Save local emergency numbers and transport helpline numbers on speed dial. Many cities have dedicated women's helplines for public transport safety. Know the numbers before you need them."
    },

    # ── Digital Safety ─────────────────────────────────────────────────────
    {
        "id": 11, "category": "Digital Safety", "icon": "🔒", "priority": 1,
        "title": "Control Your Location Sharing on Social Media",
        "content": "Never post real-time location updates on social media. Disable location tagging on photos. Share your whereabouts only with trusted contacts through secure channels, not publicly."
    },
    {
        "id": 12, "category": "Digital Safety", "icon": "🔒", "priority": 1,
        "title": "Recognize and Report Cyberstalking",
        "content": "If someone is repeatedly messaging, tracking, or monitoring you online without consent, it is cyberstalking. Document all evidence (screenshots, dates), block the person, and report to Cyber Crime helpline 1930."
    },
    {
        "id": 13, "category": "Digital Safety", "icon": "🔒", "priority": 2,
        "title": "Use Strong Privacy Settings",
        "content": "Set all social media profiles to private. Review app permissions regularly — many apps request unnecessary access to your location, camera, and contacts. Revoke permissions that are not essential."
    },
    {
        "id": 14, "category": "Digital Safety", "icon": "🔒", "priority": 2,
        "title": "Beware of Catfishing and Online Predators",
        "content": "Never share personal details (address, workplace, routine) with people you have only met online. Verify identities before meeting anyone from the internet, and always meet in public places."
    },
    {
        "id": 15, "category": "Digital Safety", "icon": "🔒", "priority": 3,
        "title": "Secure Your Devices",
        "content": "Use strong passwords and biometric locks on all devices. Enable two-factor authentication on important accounts. If your device is lost or stolen, use remote wipe features immediately."
    },

    # ── Home Safety ────────────────────────────────────────────────────────
    {
        "id": 16, "category": "Home Safety", "icon": "🏠", "priority": 1,
        "title": "Secure All Entry Points",
        "content": "Ensure all doors and windows have sturdy locks. Use a door chain or peephole before opening to strangers. Consider installing a video doorbell or security camera at entry points."
    },
    {
        "id": 17, "category": "Home Safety", "icon": "🏠", "priority": 1,
        "title": "Verify Visitors Before Opening the Door",
        "content": "Never open the door to unexpected visitors. Ask for identification from delivery personnel, maintenance workers, or anyone claiming official business. Call the company to verify if in doubt."
    },
    {
        "id": 18, "category": "Home Safety", "icon": "🏠", "priority": 2,
        "title": "Safe Delivery Practices",
        "content": "Use a pickup point or reception desk for deliveries when possible. Never invite delivery personnel inside. If you live alone, do not reveal this information to delivery workers or strangers."
    },
    {
        "id": 19, "category": "Home Safety", "icon": "🏠", "priority": 2,
        "title": "Know Your Neighbors",
        "content": "Build a friendly relationship with trusted neighbors. They can watch over your home when you are away and be first responders in an emergency. Exchange phone numbers for quick communication."
    },
    {
        "id": 20, "category": "Home Safety", "icon": "🏠", "priority": 3,
        "title": "Create an Emergency Exit Plan",
        "content": "Know all exit routes from your home. Keep a spare key with a trusted neighbor or friend. Have an emergency bag ready with essentials (ID copies, some cash, phone charger, basic medicines)."
    },

    # ── Workplace Safety ───────────────────────────────────────────────────
    {
        "id": 21, "category": "Workplace Safety", "icon": "💼", "priority": 1,
        "title": "Know Your Rights Against Harassment",
        "content": "Under the POSH Act (Prevention of Sexual Harassment), every workplace with 10+ employees must have an Internal Complaints Committee. You have the legal right to file a complaint. Document every incident with dates and witnesses."
    },
    {
        "id": 22, "category": "Workplace Safety", "icon": "💼", "priority": 1,
        "title": "Report Harassment Through Proper Channels",
        "content": "If you experience workplace harassment, report it to the Internal Complaints Committee (ICC) in writing. Keep copies of your complaint. If the ICC is unresponsive, approach the Local Complaints Committee or file an FIR."
    },
    {
        "id": 23, "category": "Workplace Safety", "icon": "💼", "priority": 2,
        "title": "Late Night Commute Safety",
        "content": "If your job requires late-night shifts, ensure your employer provides safe transport as mandated by law. Always share your cab details with a trusted contact. Avoid walking alone from the drop point to your home."
    },
    {
        "id": 24, "category": "Workplace Safety", "icon": "💼", "priority": 2,
        "title": "Set Boundaries Firmly",
        "content": "Do not tolerate inappropriate comments, touches, or behavior from colleagues regardless of their seniority. A firm, clear refusal is your right. Document boundary violations in case escalation is needed."
    },
    {
        "id": 25, "category": "Workplace Safety", "icon": "💼", "priority": 3,
        "title": "Build a Support Network at Work",
        "content": "Identify trusted colleagues who can support you. Having allies at work makes it easier to address uncomfortable situations. Share concerns with HR or a mentor if you sense a pattern of inappropriate behavior."
    },

    # ── Self Defense ───────────────────────────────────────────────────────
    {
        "id": 26, "category": "Self Defense", "icon": "🥋", "priority": 1,
        "title": "Target Vulnerable Areas",
        "content": "In a threatening situation, target the attacker's vulnerable points: eyes, nose, throat, groin, and knees. A strong palm strike to the nose or a knee to the groin can create enough time to escape."
    },
    {
        "id": 27, "category": "Self Defense", "icon": "🥋", "priority": 1,
        "title": "Carry Legal Self-Defense Tools",
        "content": "Carry pepper spray (legal in India for self-defense), a personal alarm, or a sturdy umbrella. Keep these items accessible — not buried in your bag. Practice reaching for them quickly."
    },
    {
        "id": 28, "category": "Self Defense", "icon": "🥋", "priority": 1,
        "title": "Break Free from Grabs — SING Method",
        "content": "If grabbed, remember SING: Solar plexus (elbow strike), Instep (stomp on foot), Nose (palm strike upward), Groin (knee strike). Focus on creating distance, then RUN toward people and light."
    },
    {
        "id": 29, "category": "Self Defense", "icon": "🥋", "priority": 2,
        "title": "Use Your Voice as a Weapon",
        "content": "Scream loudly and use authoritative commands like 'BACK OFF' or 'FIRE' (people respond faster to 'fire' than 'help'). Your voice can startle an attacker and attract attention from bystanders."
    },
    {
        "id": 30, "category": "Self Defense", "icon": "🥋", "priority": 3,
        "title": "Take a Self-Defense Class",
        "content": "Enroll in a self-defense class (Krav Maga, martial arts, or women's self-defense workshops). Regular practice builds muscle memory so you can react instinctively under stress. Many NGOs offer free workshops."
    },

    # ── Emergency Response ─────────────────────────────────────────────────
    {
        "id": 31, "category": "Emergency Response", "icon": "🚨", "priority": 1,
        "title": "What to Do During an Attack",
        "content": "Stay as calm as possible. Scream loudly, fight back if you can, and try to escape. If escape is not possible, try to remember the attacker's features (face, height, clothing, scars, vehicle). Your survival is the priority."
    },
    {
        "id": 32, "category": "Emergency Response", "icon": "🚨", "priority": 1,
        "title": "Preserve Evidence After an Incident",
        "content": "Do NOT wash, change clothes, or clean up after an assault. Go directly to a hospital or police station. Your clothes, body, and surroundings contain crucial forensic evidence. Take photos of injuries if possible."
    },
    {
        "id": 33, "category": "Emergency Response", "icon": "🚨", "priority": 1,
        "title": "Report to Police — Your Legal Right",
        "content": "You have the right to file an FIR at ANY police station regardless of jurisdiction (Zero FIR). The police CANNOT refuse to register your complaint. If they do, approach the SP/DCP or Women's Commission directly."
    },
    {
        "id": 34, "category": "Emergency Response", "icon": "🚨", "priority": 2,
        "title": "Seek Medical and Legal Support",
        "content": "After an incident, get a medical examination (MLC — Medico-Legal Certificate) at a government hospital. Contact a women's helpline (1091/181) for free legal aid. NGOs like NCW provide free counseling and legal support."
    },
    {
        "id": 35, "category": "Emergency Response", "icon": "🚨", "priority": 2,
        "title": "Use RAKSHAK SOS in Any Emergency",
        "content": "In an emergency, trigger the RAKSHAK SOS button. It will instantly share your GPS location with all trusted contacts and alert nearby users. The system continues tracking even if your phone is locked."
    },
]

CATEGORIES = [
    "Walking Alone",
    "Public Transport",
    "Digital Safety",
    "Home Safety",
    "Workplace Safety",
    "Self Defense",
    "Emergency Response",
]


def _tip_of_the_day():
    """Deterministic tip-of-the-day based on current date."""
    seed = date.today().toordinal()
    rng = random.Random(seed)
    return rng.choice(SAFETY_TIPS)


@safety_tips_bp.route('/')
@login_required
def index():
    """Main safety tips page."""
    tip_of_day = _tip_of_the_day()
    return render_template(
        'dashboard/safety_tips.html',
        tips=SAFETY_TIPS,
        categories=CATEGORIES,
        tip_of_day=tip_of_day,
    )


@safety_tips_bp.route('/api')
@login_required
def api():
    """JSON API returning tips, optionally filtered by category."""
    category = request.args.get('category')
    if category:
        filtered = [t for t in SAFETY_TIPS if t['category'] == category]
    else:
        filtered = SAFETY_TIPS
    return jsonify(success=True, tips=filtered, categories=CATEGORIES)
