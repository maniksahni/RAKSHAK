"""
RAKSHAK — Community Safety Score Module
Calculates a 0-100 safety score based on nearby danger zones and recent SOS alerts.
"""
import logging
import math
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from models import query_db

log = logging.getLogger('rakshak')

safety_score_bp = Blueprint('safety_score', __name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _haversine_km(lat1, lon1, lat2, lon2):
    """Return distance in km between two lat/lng points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


SEVERITY_WEIGHTS = {'high': 15, 'medium': 8, 'low': 3}

# Time-of-day risk multipliers (hour ranges)
_TIME_RISK = {
    'late_night': (0, 5, 1.5, 'Late Night (12am-5am) — Higher risk, avoid isolated areas'),
    'early_morning': (5, 7, 1.1, 'Early Morning (5am-7am) — Moderate visibility'),
    'daytime': (7, 18, 1.0, 'Daytime (7am-6pm) — Generally safer'),
    'evening': (18, 21, 1.2, 'Evening (6pm-9pm) — Stay in well-lit areas'),
    'night': (21, 24, 1.4, 'Night (9pm-12am) — Exercise caution'),
}


def _time_advisory(hour=None):
    """Return (multiplier, advisory_text) for the given hour."""
    if hour is None:
        hour = datetime.now().hour
    for _name, (start, end, mult, text) in _TIME_RISK.items():
        if start <= hour < end:
            return mult, text
    return 1.0, 'Stay alert at all times'


def calculate_safety_score(lat, lng):
    """
    Calculate safety score 0-100 for a location.
    Formula: base 100 - danger_zone_penalty - recent_sos_penalty
    Minimum score: 10
    """
    # ── Danger zones within 1km ──────────────────────────────────────────────
    # Rough bounding box filter first (±0.01 deg ~ 1.1 km), then haversine
    zones = query_db(
        """SELECT latitude, longitude, severity, radius_meters, zone_type, description
           FROM danger_zones
           WHERE status = 'approved'
             AND latitude BETWEEN %s AND %s
             AND longitude BETWEEN %s AND %s""",
        (lat - 0.01, lat + 0.01, lng - 0.01, lng + 0.01)
    ) or []

    danger_zone_penalty = 0
    nearby_zones = []
    for z in zones:
        dist = _haversine_km(lat, lng, float(z['latitude']), float(z['longitude']))
        if dist <= 0.5:
            weight = SEVERITY_WEIGHTS.get(z['severity'], 8)
            danger_zone_penalty += weight
            nearby_zones.append({
                'distance_m': round(dist * 1000),
                'severity': z['severity'],
                'zone_type': z['zone_type'],
                'description': z['description'],
                'penalty': weight,
            })
        elif dist <= 1.0:
            # Zones between 500m-1km get half penalty
            weight = SEVERITY_WEIGHTS.get(z['severity'], 8) // 2
            danger_zone_penalty += weight
            nearby_zones.append({
                'distance_m': round(dist * 1000),
                'severity': z['severity'],
                'zone_type': z['zone_type'],
                'description': z['description'],
                'penalty': weight,
            })

    # ── Recent SOS alerts within 1km (last 7 days) ──────────────────────────
    cutoff = datetime.now() - timedelta(days=7)
    alerts = query_db(
        """SELECT latitude, longitude, created_at
           FROM sos_alerts
           WHERE created_at >= %s
             AND latitude BETWEEN %s AND %s
             AND longitude BETWEEN %s AND %s""",
        (cutoff, lat - 0.01, lat + 0.01, lng - 0.01, lng + 0.01)
    ) or []

    recent_sos_count = 0
    for a in alerts:
        dist = _haversine_km(lat, lng, float(a['latitude']), float(a['longitude']))
        if dist <= 1.0:
            recent_sos_count += 1

    recent_sos_penalty = recent_sos_count * 5

    # ── Time-of-day adjustment ───────────────────────────────────────────────
    time_mult, time_advisory = _time_advisory()

    adjusted_score = 100 - (danger_zone_penalty + recent_sos_penalty) * time_mult
    final_score = max(10, min(100, round(adjusted_score)))

    return {
        'score': final_score,
        'danger_zone_penalty': danger_zone_penalty,
        'recent_sos_penalty': recent_sos_penalty,
        'nearby_zones': sorted(nearby_zones, key=lambda x: x['distance_m']),
        'recent_sos_count': recent_sos_count,
        'time_advisory': time_advisory,
        'time_multiplier': time_mult,
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@safety_score_bp.route('/')
@login_required
def index():
    """Page showing safety score for current location."""
    return render_template('dashboard/safety_score.html')


@safety_score_bp.route('/check', methods=['POST'])
@login_required
def check():
    """JSON API: given lat/lng, calculate safety score."""
    try:
        data = request.get_json() or {}
        lat = float(data.get('latitude', 0))
        lng = float(data.get('longitude', 0))

        if lat == 0 and lng == 0:
            return jsonify(success=False, error='Valid coordinates required'), 400

        result = calculate_safety_score(lat, lng)
        return jsonify(success=True, **result)

    except (ValueError, TypeError):
        return jsonify(success=False, error='Invalid coordinates'), 400
    except Exception as e:
        log.error(f'Safety score check failed: {e}')
        return jsonify(success=False, error='Internal error calculating score'), 500


@safety_score_bp.route('/area-report')
@login_required
def area_report():
    """Detailed breakdown for an area (JSON)."""
    try:
        lat = float(request.args.get('lat', 0))
        lng = float(request.args.get('lng', 0))

        if lat == 0 and lng == 0:
            return jsonify(success=False, error='Valid coordinates required'), 400

        result = calculate_safety_score(lat, lng)

        # Enrich with hourly forecast
        hourly = []
        for h in range(24):
            mult, advisory = _time_advisory(h)
            penalty = (result['danger_zone_penalty'] + result['recent_sos_penalty']) * mult
            hourly.append({
                'hour': h,
                'score': max(10, min(100, round(100 - penalty))),
                'label': f'{h:02d}:00',
            })

        result['hourly_forecast'] = hourly
        return jsonify(success=True, **result)

    except (ValueError, TypeError):
        return jsonify(success=False, error='Invalid coordinates'), 400
    except Exception as e:
        log.error(f'Area report failed: {e}')
        return jsonify(success=False, error='Internal error'), 500
