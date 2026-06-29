"""Booking and cancellation emails.

Best-effort: a failure to send never breaks the booking/cancel request, and
users without an email on file are simply skipped. In development the default
console backend prints the message to the terminal, so no SMTP setup is needed.
Set EMAIL_BACKEND + SMTP values in .env to send real email.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

log = logging.getLogger(__name__)
BRAND = "RailSetu"


def _recipient(booking):
    email = (getattr(booking.user, "email", "") or "").strip()
    return email or None


def _greeting(booking):
    return booking.user.first_name or booking.user.username


def _journey(booking):
    return f"{booking.from_station_id} \u2192 {booking.to_station_id} on {booking.journey_date:%d %b %Y}"


def _pax_text(booking):
    lines = []
    for i, p in enumerate(booking.passengers.all(), 1):
        lines.append(f"  {i}. {p.name} ({p.age}{p.gender}) - {p.booked_status or p.get_status_display()}")
    return "\n".join(lines)


def _pax_rows_html(booking):
    rows = ""
    for i, p in enumerate(booking.passengers.all(), 1):
        rows += (
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eef1f6'>{i}. {p.name}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eef1f6'>{p.age}{p.gender}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eef1f6'>{p.booked_status or p.get_status_display()}</td></tr>"
        )
    return rows


def _send(subject, text, html, to):
    try:
        msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to])
        if html:
            msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=True)
        return True
    except Exception:
        log.exception("Could not send email to %s", to)
        return False


def send_booking_confirmation(booking):
    to = _recipient(booking)
    if not to:
        return None
    subject = f"{BRAND}: Booking {booking.get_status_display()} \u2014 PNR {booking.pnr}"
    text = (
        f"Hi {_greeting(booking)},\n\n"
        f"Your {BRAND} booking is {booking.get_status_display()}.\n\n"
        f"PNR: {booking.pnr}\n"
        f"Train: {booking.train_id} {booking.train.name}\n"
        f"Journey: {_journey(booking)}\n"
        f"Class / Quota: {booking.travel_class} / {booking.quota}\n"
        f"Total fare: \u20b9{booking.total_fare}\n\n"
        f"Passengers:\n{_pax_text(booking)}\n\n"
        f"View this ticket and its live status anytime in your {BRAND} account.\n"
        f"This is a demo project; no real travel is booked.\n\n\u2014 {BRAND}\n"
    )
    html = (
        f"<div style='font-family:system-ui,Segoe UI,Arial,sans-serif;color:#16224a;max-width:560px'>"
        f"<div style='background:#16224a;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0'>"
        f"<strong style='font-size:18px'>Rail<span style='color:#e08a1e'>Setu</span></strong>"
        f"<div style='font-size:13px;opacity:.85;margin-top:2px'>Booking {booking.get_status_display()}</div></div>"
        f"<div style='border:1px solid #eef1f6;border-top:0;border-radius:0 0 12px 12px;padding:18px 20px'>"
        f"<p>Hi {_greeting(booking)}, your booking is confirmed below.</p>"
        f"<table style='border-collapse:collapse;font-size:14px;margin:8px 0 14px'>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>PNR</td><td><strong>{booking.pnr}</strong></td></tr>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>Train</td><td>{booking.train_id} {booking.train.name}</td></tr>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>Journey</td><td>{_journey(booking)}</td></tr>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>Class / Quota</td><td>{booking.travel_class} / {booking.quota}</td></tr>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>Total fare</td><td>\u20b9{booking.total_fare}</td></tr>"
        f"</table>"
        f"<table style='border-collapse:collapse;width:100%;font-size:13px'>"
        f"<thead><tr><th align='left' style='padding:6px 10px;color:#64748b;border-bottom:2px solid #eef1f6'>Passenger</th>"
        f"<th align='left' style='padding:6px 10px;color:#64748b;border-bottom:2px solid #eef1f6'>Age</th>"
        f"<th align='left' style='padding:6px 10px;color:#64748b;border-bottom:2px solid #eef1f6'>Status</th></tr></thead>"
        f"<tbody>{_pax_rows_html(booking)}</tbody></table>"
        f"<p style='color:#94a3b8;font-size:12px;margin-top:16px'>Demo project; no real travel is booked.</p>"
        f"</div></div>"
    )
    return _send(subject, text, html, to)


def send_booking_cancellation(booking, charge, refund, rule):
    to = _recipient(booking)
    if not to:
        return None
    subject = f"{BRAND}: Booking cancelled \u2014 PNR {booking.pnr}"
    text = (
        f"Hi {_greeting(booking)},\n\n"
        f"Your {BRAND} booking (PNR {booking.pnr}) has been cancelled.\n\n"
        f"Train: {booking.train_id} {booking.train.name}\n"
        f"Journey: {_journey(booking)}\n\n"
        f"Fare paid: \u20b9{booking.total_fare}\n"
        f"Cancellation charge: \u20b9{round(charge, 2)}  ({rule})\n"
        f"Refund: \u20b9{round(refund, 2)}\n\n"
        f"This is a demo project; no real refund is issued.\n\n\u2014 {BRAND}\n"
    )
    html = (
        f"<div style='font-family:system-ui,Segoe UI,Arial,sans-serif;color:#16224a;max-width:560px'>"
        f"<div style='background:#16224a;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0'>"
        f"<strong style='font-size:18px'>Rail<span style='color:#e08a1e'>Setu</span></strong>"
        f"<div style='font-size:13px;opacity:.85;margin-top:2px'>Booking cancelled</div></div>"
        f"<div style='border:1px solid #eef1f6;border-top:0;border-radius:0 0 12px 12px;padding:18px 20px'>"
        f"<p>Hi {_greeting(booking)}, your booking <strong>{booking.pnr}</strong> has been cancelled.</p>"
        f"<table style='border-collapse:collapse;font-size:14px;margin:8px 0'>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>Train</td><td>{booking.train_id} {booking.train.name}</td></tr>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>Journey</td><td>{_journey(booking)}</td></tr>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>Fare paid</td><td>\u20b9{booking.total_fare}</td></tr>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>Charge</td><td>\u20b9{round(charge, 2)} ({rule})</td></tr>"
        f"<tr><td style='padding:3px 12px 3px 0;color:#64748b'>Refund</td><td><strong>\u20b9{round(refund, 2)}</strong></td></tr>"
        f"</table>"
        f"<p style='color:#94a3b8;font-size:12px;margin-top:14px'>Demo project; no real refund is issued.</p>"
        f"</div></div>"
    )
    return _send(subject, text, html, to)