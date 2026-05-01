"""External SOS notification dispatchers.

The core SOS flow must never fail just because an external provider is missing
or temporarily unavailable. These helpers therefore return per-channel status
objects and log errors instead of raising into the emergency path.
"""
import logging
import os
import socket
import smtplib
import ssl
import time
from base64 import urlsafe_b64encode
from datetime import datetime
from email.message import EmailMessage
from html import escape
from urllib.parse import quote

import requests

log = logging.getLogger('rakshak')

RESERVED_EMAIL_DOMAINS = {
    'example.com',
    'example.org',
    'example.net',
    'localhost',
    'invalid',
}


def _configured(*keys):
    return all(_env(k) for k in keys)


def _env(key, default=None):
    value = os.environ.get(key)
    if value is None:
        return default
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value or default


def _http_error_detail(resp, limit=180):
    try:
        payload = resp.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        err = payload.get('error')
        desc = payload.get('error_description') or payload.get('message')
        if isinstance(err, dict):
            desc = desc or err.get('message')
            err = err.get('status') or err.get('code') or err.get('message')
        parts = [str(p).strip() for p in (err, desc) if p and str(p).strip()]
        if parts:
            return ': '.join(parts)[:limit]

    text = (getattr(resp, 'text', '') or '').strip()
    return text[:limit]


def _contact_label(contact):
    return contact.get('contact_name') or contact.get('contact_email') or contact.get('contact_phone') or 'contact'


def _deliverable_email(email):
    email = (email or '').strip().lower()
    if '@' not in email:
        return False
    domain = email.rsplit('@', 1)[-1].rstrip('.')
    if (
        not domain
        or domain in RESERVED_EMAIL_DOMAINS
        or domain.endswith('.local')
        or domain.endswith('.localhost')
        or domain.endswith('.invalid')
    ):
        return False
    return True


def _pref_enabled(contact, key, default=True):
    value = contact.get(key)
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ('0', 'false', 'off', 'no', '')
    return bool(value)


def _safe_location(alert):
    lat = alert.get('latitude')
    lng = alert.get('longitude')
    if lat is None or lng is None:
        return 'Location unavailable'
    return f'{lat}, {lng}'


def _user_name(user):
    if isinstance(user, dict):
        return user.get('full_name') or user.get('name') or 'User'
    return getattr(user, 'full_name', 'User')


def _sos_text(user, alert):
    location = alert.get('address') or _safe_location(alert)
    trigger = alert.get('trigger_type') or 'manual'
    msg = alert.get('message') or 'Emergency assistance requested.'
    created = alert.get('created_at') or datetime.utcnow().isoformat() + 'Z'
    alert_id = alert.get('id') or 'N/A'
    lat = alert.get('latitude')
    lng = alert.get('longitude')
    maps = f'https://maps.google.com/?q={lat},{lng}' if lat is not None and lng is not None else 'N/A'
    return (
        'RAKSHAK SOS ALERT\n'
        '=================\n\n'
        f'Incident ID: {alert_id}\n'
        f'Time: {created}\n'
        f'User: {_user_name(user)}\n'
        f'Trigger: {str(trigger).upper()}\n'
        f'Location: {location}\n'
        f'Map: {maps}\n\n'
        f'Message:\n{msg}\n\n'
        'Action Required:\n'
        'Please contact or assist immediately.'
    )


def _sos_html(user, alert):
    location = alert.get('address') or _safe_location(alert)
    trigger = str(alert.get('trigger_type') or 'manual').upper()
    msg = escape((alert.get('message') or 'Emergency assistance requested.').strip())
    user_name = escape(_user_name(user))
    alert_id = escape(str(alert.get('id') or 'N/A'))
    created = escape(str(alert.get('created_at') or (datetime.utcnow().isoformat() + 'Z')))
    severity = 'HIGH'
    sev_bg = 'rgba(239,68,68,.18)'
    sev_border = 'rgba(239,68,68,.48)'
    if trigger in {'PREVIEW', 'TEST'}:
        severity = 'TEST'
        sev_bg = 'rgba(59,130,246,.18)'
        sev_border = 'rgba(59,130,246,.48)'
    elif trigger in {'MANUAL', 'BUTTON'}:
        severity = 'CRITICAL'
    lat = alert.get('latitude')
    lng = alert.get('longitude')
    maps_link = f'https://maps.google.com/?q={lat},{lng}' if lat is not None and lng is not None else ''
    maps_cta = (
        f'<a href="{maps_link}" target="_blank" '
        'style="display:inline-block;margin-top:12px;padding:10px 14px;background:#1f1f3a;'
        'border:1px solid rgba(139,92,246,.35);border-radius:10px;color:#e9ddff;'
        'text-decoration:none;font-size:13px;font-weight:600;">Open Live Location in Maps</a>'
        if maps_link else ''
    )
    return f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#08070a;font-family:Inter,Arial,sans-serif;color:#efeefe;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;">
      [RAKSHAK] {severity} SOS alert for {user_name}. Immediate response requested.
    </div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#08070a;padding:14px 8px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;background:#0d0c14;border:1px solid rgba(139,92,246,.32);border-radius:14px;overflow:hidden;">
            <tr>
              <td style="padding:12px 14px;background:#151327;border-bottom:1px solid rgba(139,92,246,.35);">
                <div style="font-family:'Space Grotesk','Rajdhani',Arial,sans-serif;font-size:18px;font-weight:800;letter-spacing:.12em;color:#c4b5fd;">RAKSHAK</div>
                <div style="font-family:'Courier New',monospace;font-size:10px;letter-spacing:.12em;color:#9b87d7;margin-top:2px;">TACTICAL INCIDENT CHANNEL</div>
              </td>
            </tr>
            <tr><td style="height:2px;background:linear-gradient(90deg,transparent,rgba(139,92,246,.85),transparent);"></td></tr>
            <tr>
              <td style="padding:14px;">
                <div style="font-family:'Space Grotesk','Rajdhani',Arial,sans-serif;color:#ffffff;font-size:22px;font-weight:800;line-height:1.15;">SOS INCIDENT ALERT</div>
                <div style="font-family:'Courier New',monospace;font-size:11px;color:#9b87d7;letter-spacing:.09em;margin-top:4px;">INCIDENT #{alert_id}</div>

                <div style="margin-top:10px;">
                  <span style="display:inline-block;margin:0 6px 6px 0;padding:6px 10px;border-radius:999px;background:{sev_bg};border:1px solid {sev_border};color:#ffe5e5;font-size:11px;font-weight:800;letter-spacing:.06em;font-family:'Courier New',monospace;">SEVERITY • {severity}</span>
                  <span style="display:inline-block;margin:0 6px 6px 0;padding:6px 10px;border-radius:999px;background:rgba(16,185,129,.14);border:1px solid rgba(16,185,129,.35);color:#c9ffe6;font-size:11px;font-weight:700;letter-spacing:.06em;font-family:'Courier New',monospace;">SHIELD • ACTIVE</span>
                </div>

                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;background:rgba(255,255,255,.02);border:1px solid rgba(139,92,246,.2);border-radius:10px;">
                  <tr><td style="padding:10px 12px;border-bottom:1px solid rgba(139,92,246,.12);color:#9b87d7;font-family:'Courier New',monospace;font-size:11px;letter-spacing:.06em;">TIME</td><td style="padding:10px 12px;border-bottom:1px solid rgba(139,92,246,.12);color:#ffffff;font-weight:600;word-break:break-word;">{created}</td></tr>
                  <tr><td style="padding:10px 12px;border-bottom:1px solid rgba(139,92,246,.12);color:#9b87d7;font-family:'Courier New',monospace;font-size:11px;letter-spacing:.06em;">USER</td><td style="padding:10px 12px;border-bottom:1px solid rgba(139,92,246,.12);color:#ffffff;font-weight:700;word-break:break-word;">{user_name}</td></tr>
                  <tr><td style="padding:10px 12px;border-bottom:1px solid rgba(139,92,246,.12);color:#9b87d7;font-family:'Courier New',monospace;font-size:11px;letter-spacing:.06em;">TRIGGER</td><td style="padding:10px 12px;border-bottom:1px solid rgba(139,92,246,.12);color:#ffffff;font-weight:700;word-break:break-word;">{trigger}</td></tr>
                  <tr><td style="padding:10px 12px;color:#9b87d7;font-family:'Courier New',monospace;font-size:11px;letter-spacing:.06em;">LOCATION</td><td style="padding:10px 12px;color:#ffffff;font-weight:600;word-break:break-word;">{escape(location)}</td></tr>
                </table>

                <div style="margin-top:12px;">{maps_cta}</div>

                <div style="margin-top:12px;padding:12px;background:linear-gradient(180deg,rgba(139,92,246,.08),rgba(124,58,237,.04));border:1px solid rgba(139,92,246,.24);border-radius:10px;">
                  <div style="font-size:11px;color:#9b87d7;letter-spacing:.1em;margin-bottom:7px;font-weight:700;font-family:'Courier New',monospace;">MESSAGE PAYLOAD</div>
                  <div style="color:#f4f2ff;line-height:1.55;font-size:15px;white-space:pre-wrap;word-break:break-word;">{msg}</div>
                </div>

                <div style="margin-top:12px;padding:11px;background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.35);border-radius:10px;color:#ffd6d6;font-size:13px;font-weight:600;">
                  Immediate action required: Contact or assist the user now.
                </div>
                <div style="margin-top:12px;font-size:10px;color:#7f74aa;letter-spacing:.06em;font-family:'Courier New',monospace;">
                  AUTOGENERATED BY RAKSHAK EMERGENCY PROTOCOL
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _smtp_variants(host, port, use_tls, allow_ssl_fallback=True):
    variants = [(host, port, use_tls, False, 'primary')]
    # Gmail and some providers are more reliable over implicit SSL on 465.
    if allow_ssl_fallback and host == 'smtp.gmail.com' and port != 465:
        variants.append((host, 465, False, True, 'ssl-fallback'))
    return variants


def _smtp_endpoints(host, port):
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    seen = set()
    ordered = []
    for family, socktype, proto, canonname, sockaddr in sorted(
        infos,
        key=lambda info: 0 if info[0] == socket.AF_INET else 1
    ):
        key = (family, sockaddr[0], sockaddr[1])
        if key in seen:
            continue
        seen.add(key)
        ordered.append((family, socktype, proto, canonname, sockaddr))
    return ordered


def _smtp_connect(host, port, *, use_ssl=False, timeout_seconds=20):
    last_error = None
    for family, socktype, proto, _canonname, sockaddr in _smtp_endpoints(host, port):
        smtp = None
        ip_address = sockaddr[0]
        family_label = 'ipv4' if family == socket.AF_INET else 'ipv6'
        try:
            if use_ssl:
                smtp = smtplib.SMTP_SSL(timeout=timeout_seconds, context=ssl.create_default_context())
            else:
                smtp = smtplib.SMTP(timeout=timeout_seconds)
            # Preserve the original hostname for TLS SNI/certificate validation
            # while connecting to a resolved address directly.
            smtp._host = host
            smtp.connect(ip_address, sockaddr[1])
            smtp._host = host
            return smtp, f'{ip_address} [{family_label}]'
        except Exception as exc:
            last_error = f'{type(exc).__name__}: {exc}'
            log.warning('SOS SMTP connect failed for %s:%s via %s [%s]: %s',
                        host, port, ip_address, family_label, exc)
            if smtp is not None:
                try:
                    smtp.close()
                except Exception:
                    pass
    raise OSError(last_error or f'Unable to connect to SMTP host {host}:{port}')


def _send_gmail_api_email(contact, subject, body, html_body=None):
    required = (
        'GMAIL_API_CLIENT_ID',
        'GMAIL_API_CLIENT_SECRET',
        'GMAIL_API_REFRESH_TOKEN',
        'GMAIL_API_SENDER',
    )
    if not _configured(*required):
        return {
            'channel': 'email',
            'contact': _contact_label(contact),
            'success': False,
            'configured': False,
            'detail': 'Gmail API not configured',
        }

    recipient = contact.get('contact_email')
    if not recipient:
        return {'channel': 'email', 'contact': _contact_label(contact), 'success': False, 'configured': True, 'detail': 'missing contact email'}
    if not _deliverable_email(recipient):
        return {
            'channel': 'email',
            'contact': recipient,
            'success': False,
            'configured': True,
            'detail': 'undeliverable contact email domain',
        }

    sender = _env('GMAIL_API_SENDER')
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype='html')

    token_payload = {
        'client_id': _env('GMAIL_API_CLIENT_ID'),
        'client_secret': _env('GMAIL_API_CLIENT_SECRET'),
        'refresh_token': _env('GMAIL_API_REFRESH_TOKEN'),
        'grant_type': 'refresh_token',
    }

    try:
        token_resp = requests.post(
            'https://oauth2.googleapis.com/token',
            data=token_payload,
            timeout=15,
        )
        if not token_resp.ok:
            detail = _http_error_detail(token_resp) or 'unknown token refresh error'
            return {
                'channel': 'email',
                'contact': recipient,
                'success': False,
                'configured': True,
                'detail': f'Gmail token refresh failed: {token_resp.status_code} {detail}',
            }

        access_token = token_resp.json().get('access_token')
        if not access_token:
            return {
                'channel': 'email',
                'contact': recipient,
                'success': False,
                'configured': True,
                'detail': 'Gmail token refresh returned no access token',
            }

        raw_message = urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        send_resp = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            json={'raw': raw_message},
            timeout=20,
        )
        ok = 200 <= send_resp.status_code < 300
        detail = 'sent via Gmail API' if ok else f'Gmail API {send_resp.status_code}: {send_resp.text[:180]}'
        return {
            'channel': 'email',
            'contact': recipient,
            'success': ok,
            'configured': True,
            'detail': detail,
        }
    except Exception as exc:
        log.warning('Gmail API delivery failed for %s: %s', recipient, exc)
        return {
            'channel': 'email',
            'contact': recipient,
            'success': False,
            'configured': True,
            'detail': f'Gmail API error: {exc}',
        }


def _send_email(contact, subject, body, smtp_options=None, html_body=None):
    required = ('SMTP_HOST', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'SMTP_FROM')
    if not _configured(*required):
        return {'channel': 'email', 'contact': _contact_label(contact), 'success': False, 'configured': False, 'detail': 'SMTP not configured'}

    recipient = contact.get('contact_email')
    if not recipient:
        return {'channel': 'email', 'contact': _contact_label(contact), 'success': False, 'configured': True, 'detail': 'missing contact email'}
    if not _deliverable_email(recipient):
        return {
            'channel': 'email',
            'contact': recipient,
            'success': False,
            'configured': True,
            'detail': 'undeliverable contact email domain',
        }

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = _env('SMTP_FROM')
    msg['To'] = recipient
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype='html')

    smtp_options = dict(smtp_options or {})
    host = smtp_options.get('host') or _env('SMTP_HOST')
    port = int(smtp_options.get('port') or _env('SMTP_PORT', '587'))
    use_tls = bool(smtp_options.get('use_tls', _env('SMTP_USE_TLS', 'true').lower() != 'false'))
    username = _env('SMTP_USERNAME')
    password = _env('SMTP_PASSWORD')
    timeout_seconds = int(smtp_options.get('timeout_seconds') or _env('SMTP_TIMEOUT_SECONDS', '20'))
    attempts_per_variant = max(1, int(smtp_options.get('retry_attempts') or _env('SMTP_RETRY_ATTEMPTS', '2')))
    allow_ssl_fallback = bool(smtp_options.get('allow_ssl_fallback', True))

    last_error = 'SMTP delivery failed'
    for variant_host, variant_port, variant_tls, variant_ssl, variant_label in _smtp_variants(host, port, use_tls, allow_ssl_fallback=allow_ssl_fallback):
        for attempt in range(1, attempts_per_variant + 1):
            smtp = None
            try:
                smtp, endpoint_label = _smtp_connect(
                    variant_host,
                    variant_port,
                    use_ssl=variant_ssl,
                    timeout_seconds=timeout_seconds,
                )
                smtp.ehlo()
                if variant_tls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(msg)
                return {
                    'channel': 'email',
                    'contact': recipient,
                    'success': True,
                    'configured': True,
                    'detail': f'sent via {variant_label} ({endpoint_label})',
                }
            except (socket.timeout, TimeoutError) as exc:
                last_error = f'timed out via {variant_label} (attempt {attempt}/{attempts_per_variant})'
                log.warning('SOS email timeout for %s via %s: %s', recipient, variant_label, exc)
            except smtplib.SMTPException as exc:
                last_error = f'{exc.__class__.__name__}: {exc}'
                log.warning('SOS email SMTP error for %s via %s: %s', recipient, variant_label, exc)
                # Auth / recipient / permanent SMTP errors should not be spam-retried endlessly.
                if getattr(exc, 'smtp_code', 0) >= 500:
                    break
            except Exception as exc:
                last_error = str(exc)
                log.warning('SOS email delivery failed for %s via %s: %s', recipient, variant_label, exc)
            finally:
                if smtp is not None:
                    try:
                        smtp.quit()
                    except Exception:
                        try:
                            smtp.close()
                        except Exception:
                            pass
            if attempt < attempts_per_variant:
                time.sleep(1.2 * attempt)

    if (
        'ENETUNREACH' in str(last_error)
        or 'Network is unreachable' in str(last_error)
        or 'timed out' in str(last_error).lower()
    ):
        last_error = (
            'SMTP unreachable from host. Railway Free/Trial/Hobby blocks outbound SMTP. '
            'Use Gmail API instead, or upgrade Railway to Pro for outbound SMTP.'
        )

    return {'channel': 'email', 'contact': recipient, 'success': False, 'configured': True, 'detail': last_error}


def _send_email_with_fallbacks(contact, subject, body, smtp_options=None, html_body=None):
    providers = []
    if _configured('GMAIL_API_CLIENT_ID', 'GMAIL_API_CLIENT_SECRET', 'GMAIL_API_REFRESH_TOKEN', 'GMAIL_API_SENDER'):
        providers.append(lambda: _send_gmail_api_email(contact, subject, body, html_body=html_body))
    providers.append(lambda: _send_email(contact, subject, body, smtp_options=smtp_options, html_body=html_body))

    last_result = None
    configured_failure = None
    for provider in providers:
        result = provider()
        last_result = result
        if result.get('success'):
            return result
        if result.get('configured'):
            if configured_failure is None:
                configured_failure = result
            log.warning('SOS email provider failed for %s: %s', result.get('contact'), result.get('detail'))
    return configured_failure or last_result or {
        'channel': 'email',
        'contact': _contact_label(contact),
        'success': False,
        'configured': False,
        'detail': 'No email provider configured',
    }


def email_provider_diagnostics():
    providers = {
        'gmail_api': (
            'GMAIL_API_CLIENT_ID',
            'GMAIL_API_CLIENT_SECRET',
            'GMAIL_API_REFRESH_TOKEN',
            'GMAIL_API_SENDER',
        ),
        'smtp': (
            'SMTP_HOST',
            'SMTP_USERNAME',
            'SMTP_PASSWORD',
            'SMTP_FROM',
        ),
    }
    diagnostics = {}
    for name, keys in providers.items():
        missing = [key for key in keys if not _env(key)]
        diagnostics[name] = {
            'configured': not missing,
            'missing': missing,
        }
    return diagnostics


def _send_twilio(contact, body, whatsapp=False):
    required = ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN')
    from_key = 'TWILIO_WHATSAPP_FROM' if whatsapp else 'TWILIO_SMS_FROM'
    channel = 'whatsapp' if whatsapp else 'sms'
    if not _configured(*required, from_key):
        return {'channel': channel, 'contact': _contact_label(contact), 'success': False, 'configured': False, 'detail': f'Twilio {channel} not configured'}

    phone = contact.get('contact_phone')
    if not phone:
        return {'channel': channel, 'contact': _contact_label(contact), 'success': False, 'configured': True, 'detail': 'missing contact phone'}

    sid = _env('TWILIO_ACCOUNT_SID')
    token = _env('TWILIO_AUTH_TOKEN')
    to_number = f'whatsapp:{phone}' if whatsapp and not phone.startswith('whatsapp:') else phone
    payload = {
        'From': _env(from_key),
        'To': to_number,
        'Body': body,
    }
    try:
        resp = requests.post(
            f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json',
            data=payload,
            auth=(sid, token),
            timeout=10,
        )
        ok = 200 <= resp.status_code < 300
        detail = 'sent' if ok else f'{resp.status_code}: {resp.text[:180]}'
        return {'channel': channel, 'contact': phone, 'success': ok, 'configured': True, 'detail': detail}
    except Exception as exc:
        log.warning('SOS %s delivery failed for %s: %s', channel, phone, exc)
        return {'channel': channel, 'contact': phone, 'success': False, 'configured': True, 'detail': str(exc)}


def _free_share_links(contact, subject, body):
    """Generate zero-cost user-initiated WhatsApp/SMS/Email links."""
    phone = (contact.get('contact_phone') or '').replace(' ', '').replace('-', '')
    email = contact.get('contact_email') or ''
    encoded_body = quote(body)
    encoded_subject = quote(subject)
    links = {}

    if _pref_enabled(contact, 'notify_phone') and phone:
        links['whatsapp'] = f'https://wa.me/{phone.replace("+", "")}?text={encoded_body}'
        links['sms'] = f'sms:{phone}?&body={encoded_body}'
    if _pref_enabled(contact, 'notify_email') and email:
        links['mailto'] = f'mailto:{email}?subject={encoded_subject}&body={encoded_body}'

    return {
        'channel': 'free_share_links',
        'contact': _contact_label(contact),
        'success': bool(links),
        'configured': True,
        'detail': 'generated' if links else 'missing phone/email',
        'links': links,
    }


def dispatch_sos_notifications(user, contacts, alert, smtp_options=None):
    """Send SOS where possible and always provide free manual share links.

    Free mode:
    - Gmail API sends automatically over HTTPS when GMAIL_API_* env vars exist.
    - Otherwise SMTP email sends automatically when SMTP_* env vars are configured.
    - WhatsApp/SMS are generated as wa.me and sms: links because automatic
      WhatsApp/SMS requires a gateway/provider.

    Optional gateway mode:
    - Twilio SMS/WhatsApp sends automatically only when TWILIO_* env vars exist.
    """
    contacts = contacts or []
    alert = dict(alert or {})
    body = _sos_text(user, alert)
    html_body = _sos_html(user, alert)
    trigger = str(alert.get('trigger_type') or 'manual').lower()
    if trigger == 'preview':
        prefix = '[TEST]'
    elif trigger in {'manual', 'button'}:
        prefix = '[CRITICAL]'
    else:
        prefix = '[ALERT]'
    subject = f'{prefix} RAKSHAK SOS - {_user_name(user)}'
    results = []
    for contact in contacts:
        contact = dict(contact)
        if _pref_enabled(contact, 'notify_email'):
            results.append(_send_email_with_fallbacks(contact, subject, body, smtp_options=smtp_options, html_body=html_body))
        else:
            results.append({'channel': 'email', 'contact': _contact_label(contact), 'success': False, 'configured': True, 'detail': 'disabled for contact'})
        results.append(_free_share_links(contact, subject, body))
        if _pref_enabled(contact, 'notify_phone') and _configured('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN'):
            results.append(_send_twilio(contact, body, whatsapp=False))
            results.append(_send_twilio(contact, body, whatsapp=True))
    return results


def summarize_delivery(results):
    email_sent = 0
    sms_sent = 0
    whatsapp_sent = 0
    manual_links_generated = 0
    email_disabled = 0
    email_not_configured = 0
    email_failed = 0
    first_email_error = ''
    email_failure_contacts = []

    for r in results:
        channel = r.get('channel')
        success = bool(r.get('success'))
        configured = bool(r.get('configured'))
        detail = (r.get('detail') or '').strip().lower()

        if channel == 'email':
            if success:
                email_sent += 1
            elif detail == 'disabled for contact':
                email_disabled += 1
            elif not configured:
                email_not_configured += 1
            else:
                email_failed += 1
                if not first_email_error:
                    first_email_error = (r.get('detail') or '').strip()[:180]
                if r.get('contact'):
                    email_failure_contacts.append(r.get('contact'))
        elif channel == 'sms' and success:
            sms_sent += 1
        elif channel == 'whatsapp' and success:
            whatsapp_sent += 1
        elif channel == 'free_share_links' and success:
            manual_links_generated += 1

    auto_delivered = email_sent + sms_sent + whatsapp_sent
    summary = {
        'attempted': len(results),
        'sent': sum(1 for r in results if r.get('success')),
        'configured': sum(1 for r in results if r.get('configured')),
        'not_configured': sum(1 for r in results if not r.get('configured')),
        'auto_delivered': auto_delivered,
        'email_sent': email_sent,
        'sms_sent': sms_sent,
        'whatsapp_sent': whatsapp_sent,
        'manual_links_generated': manual_links_generated,
        'email_disabled': email_disabled,
        'email_not_configured': email_not_configured,
        'email_failed': email_failed,
        'first_email_error': first_email_error,
        'email_failure_contacts': email_failure_contacts,
        'channels': results,
    }
    return summary
