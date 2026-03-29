import uuid
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime

def draw_watermark(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 100)
    # Using a literal color code with alpha for pure reportlab safety
    # if alpha isn't supported in HexColor by default in this version, we can fake it with light gray/red.
    # We will just use #fecada for a very light red watermark.
    canvas.setFillColor(colors.HexColor('#fee2e2'))
    # Set stroke and fill opacity manually if possible, or just rely on the light color.
    try:
        canvas.setFillAlpha(0.15)
    except:
        pass
    # Center and rotate
    canvas.translate(doc.width/2 + doc.leftMargin, doc.height/2 + doc.bottomMargin)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, 'CLASSIFIED')
    canvas.restoreState()

def generate_sos_report(alert: dict, user: dict, contacts: list) -> BytesIO:
    """Generate a highly official PDF incident dossier for an SOS alert."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    # ── Color Palette ──────────────────────────────────────────────
    CRIMSON  = colors.HexColor('#7c3aed')
    BLOOD    = colors.HexColor('#991b1b')
    DARK_BG  = colors.HexColor('#0a0a0f')
    STEEL    = colors.HexColor('#cbd5e1')
    WHITE    = colors.white
    BLACK    = colors.black
    GRAY     = colors.HexColor('#6b7280')

    styles = getSampleStyleSheet()

    # Define custom styles
    title_style = ParagraphStyle(
        'DossierTitle', parent=styles['Title'],
        textColor=CRIMSON, fontSize=28, spaceAfter=2, alignment=TA_LEFT,
        fontName='Helvetica-Bold', textTransform='uppercase'
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        textColor=GRAY, fontSize=11, spaceAfter=15, alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    confidential_style = ParagraphStyle(
        'Confidential', parent=styles['Normal'],
        textColor=BLOOD, fontSize=14, spaceAfter=8, alignment=TA_RIGHT,
        fontName='Helvetica-Bold'
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading2'],
        textColor=BLACK, fontSize=14, spaceBefore=18, spaceAfter=8,
        fontName='Helvetica-Bold', textTransform='uppercase'
    )
    body_style  = ParagraphStyle(
        'Body', parent=styles['Normal'],
        textColor=colors.HexColor('#1f2937'), fontSize=10, leading=16
    )

    story = []

    # ── Header Layer ─────────────────────────────────────────────────
    # Generate cryptographic-looking evidence hash
    raw_hash_data = f"{alert.get('id', 0)}-{alert.get('created_at', '')}-{user.get('id', 0)}"
    evidence_hash = hashlib.sha256(raw_hash_data.encode()).hexdigest()[:16].upper()
    tracking_id   = f"RAKS-DOSSIER-{str(uuid.uuid4()).split('-')[0].upper()}"

    story.append(Paragraph("TOP SECRET // CONFIDENTIAL", confidential_style))
    story.append(Paragraph("RAKSHAK COMMAND CENTER", title_style))
    story.append(Paragraph("OFFICIAL INCIDENT RESPONSE DOSSIER", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=3, color=DARK_BG))
    story.append(Spacer(1, 0.5*cm))

    # ── Alert Meta Data ──────────────────────────────────────────────
    created_at = alert.get('created_at', datetime.now())
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at).replace(tzinfo=None)

    story.append(Paragraph("I. INCIDENT CLASSIFICATION", section_style))
    meta_data = [
        ['TRACKING ID', tracking_id],
        ['EVIDENCE HASH', evidence_hash],
        ['TIMESTAMP (LOCAL)', datetime.now().strftime('%d %b %Y  %H:%M:%S')],
        ['INCIDENT TIME', created_at.strftime('%d %b %Y  %H:%M:%S')],
        ['TRIGGER PROTOCOL', alert.get('trigger_type', 'manual').replace('_', ' ').upper()],
        ['MISSION STATUS', alert.get('status', 'active').upper()],
    ]
    meta_table = Table(meta_data, colWidths=[6*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), DARK_BG),
        ('TEXTCOLOR', (0, 0), (0, -1), WHITE),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (1, 0), (1, -1), BLACK),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 1, STEEL),
        ('PADDING', (0, 0), (-1, -1), 10),
        # Highlight status row if active
        ('TEXTCOLOR', (1, 5), (1, 5), CRIMSON if alert.get('status') == 'active' else colors.HexColor('#16a34a')),
    ]))
    story.append(meta_table)

    # ── Subject Overview ─────────────────────────────────────────────
    story.append(Paragraph("II. SUBJECT OVERVIEW", section_style))
    user_data = [
        ['SUBJECT NAME', user.get('full_name', 'N/A').upper()],
        ['CONTACT EMAIL', user.get('email', 'N/A')],
        ['PRIMARY PHONE', user.get('phone', 'N/A')],
        ['REGISTERED ADDRESS', user.get('address') or 'Classified / Not provided'],
    ]
    user_table = Table(user_data, colWidths=[6*cm, 12*cm])
    user_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, STEEL),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(user_table)

    # ── Tactical Coordinates ─────────────────────────────────────────
    story.append(Paragraph("III. TACTICAL COORDINATES", section_style))
    lat  = alert.get('latitude', 0)
    lng  = alert.get('longitude', 0)
    maps_url = f"https://maps.google.com/?q={lat},{lng}"
    loc_data = [
        ['LATITUDE',  str(lat)],
        ['LONGITUDE', str(lng)],
        ['APPROX. ADDRESS', alert.get('address') or 'Signal Lost / Not available'],
        ['GPS ACCURACY', f"Â±{alert.get('accuracy', 'N/A')} METERS"],
        ['DEVICE BATTERY', f"{alert.get('battery_level', 'N/A')}% (AT TIME OF INCIDENT)"],
        ['LIVE TRACKING LINK', maps_url],
    ]
    loc_table = Table(loc_data, colWidths=[6*cm, 12*cm])
    loc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), DARK_BG),
        ('TEXTCOLOR', (0, 0), (0, -1), WHITE),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, STEEL),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (1, 5), (1, 5), colors.blue),
    ]))
    story.append(loc_table)

    # ── Emergency Contacts Broadcast ─────────────────────────────────
    if contacts:
        story.append(Paragraph("IV. EMERGENCY BROADCAST LOG", section_style))
        contact_rows = [['#', 'PROTOCOL NAME', 'PHONE', 'RELATION']]
        for i, c in enumerate(contacts, 1):
            contact_rows.append([
                str(i),
                c.get('contact_name', 'N/A').upper(),
                c.get('contact_phone', 'N/A'),
                c.get('relationship', 'N/A').upper(),
            ])
        contact_table = Table(contact_rows, colWidths=[1.5*cm, 6.5*cm, 5*cm, 5*cm])
        contact_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), CRIMSON),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, STEEL),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(contact_table)

    # ── Additional Intel ─────────────────────────────────────────────
    if alert.get('message'):
        story.append(Paragraph("V. ADDITIONAL INTEL / COMMUNIQUE", section_style))
        story.append(Paragraph(
            f"<b>Intercepted Message:</b> {alert['message']}", 
            ParagraphStyle('Intel', parent=styles['Normal'], fontSize=11, leading=16, 
                           backColor=colors.HexColor('#fef2f2'), textColor=BLOOD, borderPadding=10)
        ))
        story.append(Spacer(1, 0.5*cm))

    # ── Footer ───────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK_BG))
    story.append(Spacer(1, 0.3*cm))
    
    footer_text = (
        "<b>WARNING:</b> THIS DOCUMENT CONTAINS HIGHLY SENSITIVE LOCATION AND PERSONAL IDENTIFICATION DATA. "
        "UNAUTHORIZED DISTRIBUTION IS STRICTLY PROHIBITED. <br/>"
        "GENERATED BY RAKSHAK THREAT ENGINE INFRASTRUCTURE. FOR EMERGENCY USE EXCLUSIVELY."
    )
    story.append(Paragraph(
        footer_text,
        ParagraphStyle('Footer', parent=styles['Normal'], textColor=GRAY,
                       fontSize=7, alignment=TA_CENTER, leading=10)
    ))

    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    buffer.seek(0)
    return buffer
