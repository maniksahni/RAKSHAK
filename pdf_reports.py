from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from datetime import datetime


def generate_sos_report(alert: dict, user: dict, contacts: list) -> BytesIO:
    """Generate a PDF incident report for an SOS alert using ReportLab."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # ── Colour Palette ──────────────────────────────────────────────
    RED      = colors.HexColor('#dc2626')
    DARK_BG  = colors.HexColor('#1a1a2e')
    LIGHT    = colors.HexColor('#f0f0f0')
    WHITE    = colors.white
    GRAY     = colors.HexColor('#6b7280')

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Title'],
        textColor=RED, fontSize=22, spaceAfter=6, alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        textColor=DARK_BG, fontSize=10, spaceAfter=4, alignment=TA_CENTER
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading2'],
        textColor=DARK_BG, fontSize=13, spaceBefore=14, spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    body_style  = ParagraphStyle(
        'Body', parent=styles['Normal'],
        textColor=colors.HexColor('#1f2937'), fontSize=10, leading=16
    )

    story = []

    # ── Header ───────────────────────────────────────────────────────
    story.append(Paragraph("🛡 RAKSHAK", title_style))
    story.append(Paragraph("Real-time Alert & Knowledge System for Hazard And Crisis", subtitle_style))
    story.append(Paragraph("INCIDENT REPORT", ParagraphStyle(
        'IR', parent=styles['Normal'], textColor=RED, fontSize=12,
        alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=6
    )))
    story.append(HRFlowable(width="100%", thickness=2, color=RED))
    story.append(Spacer(1, 0.4*cm))

    # ── Alert Meta ───────────────────────────────────────────────────
    created_at = alert.get('created_at', datetime.now())
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    meta_data = [
        ['Report ID', f"RAKS-{alert.get('id', 'N/A'):05d}"],
        ['Generated At', datetime.now().strftime('%d %b %Y  %H:%M:%S')],
        ['Alert Triggered At', created_at.strftime('%d %b %Y  %H:%M:%S')],
        ['Trigger Type', alert.get('trigger_type', 'manual').replace('_', ' ').upper()],
        ['Status', alert.get('status', 'active').upper()],
    ]
    meta_table = Table(meta_data, colWidths=[5*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fef2f2')),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('TEXTCOLOR', (0, 0), (0, -1), RED),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK_BG),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#fef2f2'), WHITE]),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5*cm))

    # ── User Details ─────────────────────────────────────────────────
    story.append(Paragraph("User Information", section_style))
    user_data = [
        ['Full Name', user.get('full_name', 'N/A')],
        ['Email', user.get('email', 'N/A')],
        ['Phone', user.get('phone', 'N/A')],
        ['Address', user.get('address') or 'Not provided'],
    ]
    user_table = Table(user_data, colWidths=[5*cm, 12*cm])
    user_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(user_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Location ─────────────────────────────────────────────────────
    story.append(Paragraph("Location Details", section_style))
    lat  = alert.get('latitude', 0)
    lng  = alert.get('longitude', 0)
    maps_url = f"https://maps.google.com/?q={lat},{lng}"
    loc_data = [
        ['Latitude',  str(lat)],
        ['Longitude', str(lng)],
        ['Address',   alert.get('address') or 'Not available'],
        ['Google Maps', maps_url],
        ['Battery Level', f"{alert.get('battery_level', 'N/A')}%"],
        ['GPS Accuracy', f"±{alert.get('accuracy', 'N/A')} m"],
    ]
    loc_table = Table(loc_data, colWidths=[5*cm, 12*cm])
    loc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (1, 3), (1, 3), colors.blue),
    ]))
    story.append(loc_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Trusted Contacts Notified ────────────────────────────────────
    if contacts:
        story.append(Paragraph("Trusted Contacts Notified", section_style))
        contact_rows = [['#', 'Name', 'Phone', 'Email', 'Relationship']]
        for i, c in enumerate(contacts, 1):
            contact_rows.append([
                str(i),
                c.get('contact_name', 'N/A'),
                c.get('contact_phone', 'N/A'),
                c.get('contact_email', 'N/A'),
                c.get('relationship', 'N/A'),
            ])
        contact_table = Table(contact_rows, colWidths=[1*cm, 4*cm, 3.5*cm, 5*cm, 3.5*cm])
        contact_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), RED),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#f9fafb')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(contact_table)
        story.append(Spacer(1, 0.5*cm))

    # ── Message ──────────────────────────────────────────────────────
    if alert.get('message'):
        story.append(Paragraph("Additional Information", section_style))
        story.append(Paragraph(alert['message'], body_style))
        story.append(Spacer(1, 0.3*cm))

    # ── Footer ───────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "This report was automatically generated by RAKSHAK — Women Safety System. "
        "For emergencies, please contact local authorities immediately.",
        ParagraphStyle('Footer', parent=styles['Normal'], textColor=GRAY,
                       fontSize=8, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
