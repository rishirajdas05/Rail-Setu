# Booking status: CNF, RAC, WL

- CNF (Confirmed): you have a confirmed berth or seat.
- RAC (Reservation Against Cancellation): you can board and you get a shared side
  berth, often confirmed fully closer to departure as others cancel.
- WL (Waitlisted): you do not yet have a berth. Your number (for example WL 12)
  drops as confirmed passengers cancel. If it reaches zero or below you get RAC or
  CNF; if it does not clear, the ticket is not valid for travel.

## Will my waitlist confirm?
RailSetu has a machine learning predictor that estimates the chance a waitlisted
ticket confirms, based on the class, quota, waitlist position, how many days are
left before the journey, and the day of the week. It returns a percentage and a
band (high, moderate, or low). It is trained on synthetic data, so treat it as a
rough guide, not a guarantee. You can use it on the Predict page or it appears on
PNR and availability views.