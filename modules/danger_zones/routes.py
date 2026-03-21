import math
import logging
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from models import query_db, log_audit
from socket_events import emit_danger_zone
from healer import validate_coords, sanitize_str

danger_bp = Blueprint('danger', __name__)
log = logging.getLogger('rakshak')

VALID_TYPES     = {'harassment', 'theft', 'poorly_lit', 'other'}
VALID_SEVERITIES = {'low', 'medium', 'high'}


def get_socketio():
    from app import socketio
    return socketio


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in metres between two GPS coordinates."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Map Page ──────────────────────────────────────────────────────────────────
@danger_bp.route('/')
@login_required
def map_view():
    return render_template('danger_zones/map.html')


# ── Report Danger Zone ────────────────────────────────────────────────────────
@danger_bp.route('/report', methods=['POST'])
@login_required
def report_zone():
    try:
        data        = request.get_json() or {}
        raw_lat     = data.get('latitude')
        raw_lng     = data.get('longitude')
        zone_type   = data.get('zone_type', 'other')
        description = sanitize_str(data.get('description', ''), 1000)
        severity    = data.get('severity', 'medium')
        radius      = data.get('radius_meters', 200)

        if raw_lat is None or raw_lng is None:
            return jsonify(success=False, error='Location required.'), 400

        try:
            lat, lng = validate_coords(raw_lat, raw_lng)
        except ValueError as ve:
            return jsonify(success=False, error=str(ve)), 400

        if not description or len(description) < 10:
            return jsonify(success=False,
                           error='Description must be at least 10 characters.'), 400

        if zone_type not in VALID_TYPES:
            zone_type = 'other'
        if severity not in VALID_SEVERITIES:
            severity = 'medium'

        try:
            radius = max(50, min(2000, int(radius)))
        except (TypeError, ValueError):
            radius = 200

        # Duplicate detection: same user + same spot (within 100m) in last 24h
        recent = query_db(
            """SELECT id FROM danger_zones
               WHERE reported_by=%s
                 AND ABS(latitude-%s) < 0.001
                 AND ABS(longitude-%s) < 0.001
                 AND created_at > NOW() - INTERVAL '24 hours'""",
            (current_user.id, lat, lng), one=True
        )
        if recent:
            return jsonify(
                success=False,
                error='You already reported a danger zone at this location recently.'
            ), 409

        zone_id = query_db(
            """INSERT INTO danger_zones
               (reported_by, latitude, longitude, radius_meters,
                zone_type, description, severity)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (current_user.id, lat, lng, radius, zone_type, description, severity),
            commit=True
        )
        log_audit(current_user.id, 'report_danger_zone', 'danger_zones', zone_id,
                  ip_address=request.remote_addr)
        return jsonify(success=True, zone_id=zone_id,
                       message='Danger zone reported! Pending admin approval.')

    except Exception as e:
        log.error(f'report_zone error: {e}')
        return jsonify(success=False, error='Could not report zone. Please try again.'), 500


# ── List Approved Zones ───────────────────────────────────────────────────────
@danger_bp.route('/list')
def list_zones():
    try:
        # Paginate: default 200 most recent
        limit  = min(int(request.args.get('limit', 200)), 500)
        offset = max(int(request.args.get('offset', 0)), 0)

        zones = query_db(
            """SELECT id, latitude, longitude, zone_type, description,
                      severity, radius_meters, upvotes, created_at
               FROM danger_zones WHERE status='approved'
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            (limit, offset)
        )
        features = []
        for z in zones:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(z['longitude']), float(z['latitude'])]
                },
                'properties': {
                    'id':          z['id'],
                    'zone_type':   z['zone_type'],
                    'description': z['description'],
                    'severity':    z['severity'],
                    'radius':      z['radius_meters'],
                    'upvotes':     z['upvotes'],
                    'created_at':  (z['created_at'].isoformat()
                                    if hasattr(z['created_at'], 'isoformat')
                                    else str(z['created_at']))
                }
            })
        return jsonify(success=True, geojson={
            'type': 'FeatureCollection', 'features': features
        })
    except Exception as e:
        log.error(f'list_zones error: {e}')
        return jsonify(success=False, error='Could not load zones.'), 500


# ── Proximity Check ───────────────────────────────────────────────────────────
@danger_bp.route('/proximity', methods=['POST'])
@login_required
def check_proximity():
    try:
        data = request.get_json() or {}
        try:
            user_lat, user_lng = validate_coords(
                data.get('lat', 0), data.get('lng', 0)
            )
        except ValueError as ve:
            return jsonify(success=False, error=str(ve)), 400

        zones = query_db("SELECT * FROM danger_zones WHERE status='approved'")
        nearby = []
        for z in zones:
            dist = haversine_distance(
                user_lat, user_lng,
                float(z['latitude']), float(z['longitude'])
            )
            if dist <= 500:
                nearby.append({
                    'id':          z['id'],
                    'zone_type':   z['zone_type'],
                    'description': z['description'],
                    'severity':    z['severity'],
                    'distance_m':  round(dist, 1)
                })

        nearby.sort(key=lambda x: x['distance_m'])
        return jsonify(success=True, nearby=nearby, count=len(nearby))

    except Exception as e:
        log.error(f'check_proximity error: {e}')
        return jsonify(success=False, error='Proximity check failed.'), 500


# ── Heatmap Data ──────────────────────────────────────────────────────────────
@danger_bp.route('/heatmap')
def heatmap_data():
    try:
        zones = query_db(
            "SELECT latitude, longitude, severity FROM danger_zones WHERE status='approved'"
        )
        intensity_map = {'low': 0.3, 'medium': 0.6, 'high': 1.0}
        points = [
            [float(z['latitude']), float(z['longitude']),
             intensity_map.get(z['severity'], 0.5)]
            for z in zones
        ]
        return jsonify(success=True, points=points)
    except Exception as e:
        log.error(f'heatmap_data error: {e}')
        return jsonify(success=False, error='Could not load heatmap.'), 500


# ── Upvote (idempotent — one vote per user per zone) ─────────────────────────
@danger_bp.route('/<int:zone_id>/upvote', methods=['POST'])
@login_required
def upvote_zone(zone_id):
    try:
        # Check if this user already upvoted this zone
        existing = query_db(
            """SELECT id FROM audit_logs
               WHERE user_id=%s AND action='upvote_zone'
                 AND record_id=%s AND table_name='danger_zones'
               LIMIT 1""",
            (current_user.id, zone_id), one=True
        )
        if existing:
            row = query_db(
                'SELECT upvotes FROM danger_zones WHERE id=%s', (zone_id,), one=True
            )
            return jsonify(
                success=False,
                error='You already upvoted this zone.',
                upvotes=row['upvotes'] if row else 0
            ), 409

        query_db(
            "UPDATE danger_zones SET upvotes=upvotes+1 WHERE id=%s AND status='approved'",
            (zone_id,), commit=True
        )
        log_audit(current_user.id, 'upvote_zone', 'danger_zones', zone_id,
                  ip_address=request.remote_addr)

        row = query_db('SELECT upvotes FROM danger_zones WHERE id=%s', (zone_id,), one=True)
        return jsonify(success=True, upvotes=row['upvotes'] if row else 0)

    except Exception as e:
        log.error(f'upvote_zone error zone={zone_id}: {e}')
        return jsonify(success=False, error='Upvote failed.'), 500
