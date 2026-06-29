"""Downloadable PDF e-ticket for a booking, styled like a real rail ticket."""

import io

from django.http import Http404, HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import Booking

NAVY = colors.HexColor("#16224a")
AMBER = colors.HexColor("#e08a1e")
LINE = colors.HexColor("#d7dce6")
MUTED = colors.HexColor("#6b7488")
SOFT = colors.HexColor("#f3f5fb")

STATUS_COLOR = {
    "CNF": colors.HexColor("#2f9e69"),
    "RAC": colors.HexColor("#3f78c8"),
    "WL": colors.HexColor("#d98324"),
    "CAN": colors.HexColor("#c0392b"),
}


def build_ticket_pdf(booking) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"RailSetu e-Ticket {booking.pnr}",
    )
    styles = getSampleStyleSheet()
    h_brand = ParagraphStyle("brand", parent=styles["Title"], fontSize=20,
                             textColor=NAVY, spaceAfter=0)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8,
                           textColor=MUTED)
    label = ParagraphStyle("label", parent=styles["Normal"], fontSize=7.5,
                           textColor=MUTED, spaceAfter=1)
    value = ParagraphStyle("value", parent=styles["Normal"], fontSize=11,
                           textColor=NAVY, leading=14)

    el = []

    # header band: brand + PNR
    header = Table(
        [[Paragraph("Rail<font color='#e08a1e'>Setu</font> &nbsp;<font size=9 color='#6b7488'>e-Ticket</font>", h_brand),
          Paragraph(f"<font size=8 color='#6b7488'>PNR</font><br/><font size=17 color='#16224a'><b>{booking.pnr}</b></font>", value)]],
        colWidths=[110 * mm, 64 * mm],
    )
    header.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -1), 1.4, NAVY),
    ]))
    el += [header, Spacer(1, 12)]

    # status pill
    st = booking.status
    st_color = STATUS_COLOR.get(st, MUTED)
    status_tbl = Table(
        [[Paragraph(f"<font color='white'><b>{booking.get_status_display()}</b></font>", value)]],
        colWidths=[44 * mm],
    )
    status_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), st_color),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    el += [status_tbl, Spacer(1, 14)]

    # journey block
    frm = f"{booking.from_station.name} ({booking.from_station_id})"
    to = f"{booking.to_station.name} ({booking.to_station_id})"
    journey = Table([
        [Paragraph("TRAIN", label), Paragraph("DATE OF JOURNEY", label)],
        [Paragraph(f"{booking.train_id} &nbsp; {booking.train.name}", value),
         Paragraph(booking.journey_date.strftime("%d %b %Y"), value)],
        [Paragraph("FROM", label), Paragraph("TO", label)],
        [Paragraph(frm, value), Paragraph(to, value)],
        [Paragraph("CLASS", label), Paragraph("QUOTA", label)],
        [Paragraph(booking.get_travel_class_display(), value),
         Paragraph(booking.get_quota_display(), value)],
    ], colWidths=[87 * mm, 87 * mm])
    journey.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (1, 0), 12),
        ("BOTTOMPADDING", (0, 5), (1, 5), 12),
    ]))
    el += [journey, Spacer(1, 16)]

    # passengers table
    head = ["#", "Name", "Age", "Gender", "Coach", "Berth", "Status"]
    rows = [head]
    for i, p in enumerate(booking.passengers.all(), start=1):
        rows.append([
            str(i), p.name, str(p.age), p.get_gender_display(),
            p.coach or "-", p.berth or "-",
            p.booked_status or p.get_status_display(),
        ])
    ptab = Table(rows, colWidths=[8 * mm, 56 * mm, 14 * mm, 24 * mm, 22 * mm, 26 * mm, 24 * mm])
    ptab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]))
    el += [Paragraph("Passengers", ParagraphStyle("ph", parent=value, fontSize=12, spaceAfter=6)), ptab, Spacer(1, 14)]

    # fare
    fare = Table([[Paragraph("Total fare", value),
                   Paragraph(f"<b>Rs {int(booking.total_fare)}</b>", ParagraphStyle('f', parent=value, fontSize=13))]],
                 colWidths=[140 * mm, 34 * mm])
    fare.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEABOVE", (0, 0), (-1, -1), 0.6, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    el += [fare, Spacer(1, 18)]

    el.append(Paragraph(
        "This is a demonstration ticket generated by RailSetu. Bookings are "
        "simulated and not valid for travel on Indian Railways.", small))

    doc.build(el)
    return buf.getvalue()


class TicketView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pnr):
        try:
            booking = (Booking.objects
                       .select_related("train", "from_station", "to_station")
                       .prefetch_related("passengers")
                       .get(pnr=pnr, user=request.user))
        except Booking.DoesNotExist:
            raise Http404("Ticket not found.")
        pdf = build_ticket_pdf(booking)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="RailSetu-{pnr}.pdf"'
        return resp