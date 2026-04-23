"""External SOS notification dispatchers.

The core SOS flow must never fail just because an external provider is missing
or temporarily unavailable. These helpers therefore return per-channel status
objects and log errors instead of raising into the emergency path.
"""
import logging
import os
import smtplib
from email.message import EmailMessage
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
    return all(os.environ.get(k) for k in keys)


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
    return (
        f'RAKSHAK SOS ALERT\\n'
        f'User: {_user_name(user)}\\n'
        f'Trigger: {trigger}\\n'
        f'Location: {location}\\n'
        f'Message: {msg}\\n'
        f'Please contact or assist immediately.'
    )


def _send_email(contact, subject, body):
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

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = os.environ['SMTP_FROM']
        msg['To'] = recipient
        msg.set_content(body)

        host = os.environ['SMTP_HOST']
        port = int(os.environ.get('SMTP_PORT', '587'))
        use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() != 'false'
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
            smtp.send_message(msg)
        return {'channel': 'email', 'contact': recipient, 'success': True, 'configured': True, 'detail': 'sent'}
    except Exception as exc:
        log.warning('SOS email delivery failed for %s: %s', recipient, exc)
        return {'channel': 'email', 'contact': recipient, 'success': False, 'configured': True, 'detail': str(exc)}


def _send_twilio(contact, body, whatsapp=False):
    required = ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN')
    from_key = 'TWILIO_WHATSAPP_FROM' if whatsapp else 'TWILIO_SMS_FROM'
    channel = 'whatsapp' if whatsapp else 'sms'
    if not _configured(*required, from_key):
        return {'channel': channel, 'contact': _contact_label(contact), 'success': False, 'configured': False, 'detail': f'Twilio {channel} not configured'}

    phone = contact.get('contact_phone')
    if not phone:
        return {'channel': channel, 'contact': _contact_label(contact), 'success': False, 'configured': True, 'detail': 'missing contact phone'}

    sid = os.environ['TWILIO_ACCOUNT_SID']
    token = os.environ['TWILIO_AUTH_TOKEN']
    to_number = f'whatsapp:{phone}' if whatsapp and not phone.startswith('whatsapp:') else phone
    payload = {
        'From': os.environ[from_key],
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


def dispatch_sos_notifications(user, contacts, alert):
    """Send SOS where possible and always provide free manual share links.

    Free mode:
    - SMTP email sends automatically when SMTP_* env vars are configured.
    - WhatsApp/SMS are generated as wa.me and sms: links because automatic
      WhatsApp/SMS requires a gateway/provider.

    Optional gateway mode:
    - Twilio SMS/WhatsApp sends automatically only when TWILIO_* env vars exist.
    """
    contacts = contacts or []
    alert = dict(alert or {})
    body = _sos_text(user, alert)
    subject = f'RAKSHAK SOS Alert from {_user_name(user)}'
    results = []
    for contact in contacts:
        contact = dict(contact)
        if _pref_enabled(contact, 'notify_email'):
            results.append(_send_email(contact, subject, body))
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
