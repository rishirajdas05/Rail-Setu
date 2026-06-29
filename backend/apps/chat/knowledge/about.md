# About RailSetu

RailSetu is a train discovery and booking demo for Indian Railways. You can search
trains between two stations, view schedules and coach layouts, check seat
availability and fares, book a ticket (which generates a 10 digit PNR), check PNR
status, see live running status, and use machine learning to predict waitlist
confirmation chances and arrival delays.

## Honesty about the data
RailSetu uses an open 2016 Indian Railways dataset (DataMeet, CC0) with about 5,200
trains, 8,900 stations, and 416,000 stops. Train names, numbers, routes, and
timings come from this real dataset. However, the dataset has no live data, so the
following are SIMULATED with deterministic generators and clearly labelled
"indicative" in the app: seat availability, fares, platform numbers, and coach
positions. Real IRCTC booking is not possible from this project, so bookings are
simulated. Live running status uses a third party data provider when configured.

## The machine learning
Three scikit-learn models run in a separate service:
1. A waitlist confirmation predictor (classification) that estimates the chance a
   waitlisted ticket gets confirmed.
2. An arrival delay predictor (regression) that estimates delay in minutes.
3. A "Recommended" ranking model that scores how good each train is for a route.
All three are trained on synthetic data for demonstration, the pipelines are real
but the numbers are illustrative, not learned from real outcomes.