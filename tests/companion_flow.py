"""FLO-001 of the example plan as the page index reads it: the reference flow for the character drawing."""

STEPS = [
 {
  "n": 1,
  "from": "[[website-building-blocks|Public website]]",
  "to": "[[booking-building-blocks|Booking]]",
  "text": "[[website-building-blocks|Public website]] → [[booking-building-blocks|Booking]]: asks to hold a seat, over [[booking-building-blocks#CON-001 Booking API|Booking API]]. The customer has found a crossing first: the website reads sailings from Vessel schedule, as it does today ([[CAP-011-find-a-crossing|Find a crossing]]). This is [[CAP-014-hold-a-seat|Hold a seat]]."
 },
 {
  "n": 2,
  "from": "[[call-center-building-blocks|Call center desktop]]",
  "to": "[[booking-building-blocks|Booking]]",
  "text": "[[call-center-building-blocks|Call center desktop]] → [[booking-building-blocks|Booking]]: asks to hold a seat, over [[booking-building-blocks#CON-001 Booking API|Booking API]]. The agent has found a crossing for the caller, the same way. This is [[CAP-014-hold-a-seat|Hold a seat]]."
 },
 {
  "n": 3,
  "from": "[[kiosks-building-blocks|Port kiosks]]",
  "to": "[[booking-building-blocks|Booking]]",
  "text": "[[kiosks-building-blocks|Port kiosks]] → [[booking-building-blocks|Booking]]: asks to hold a seat, over [[booking-building-blocks#CON-001 Booking API|Booking API]]. The customer has picked a crossing on the screen. This is [[CAP-014-hold-a-seat|Hold a seat]]."
 },
 {
  "n": 4,
  "from": "",
  "to": "",
  "text": "[[CAP-014-hold-a-seat|Hold the seat]]. Booking checks capacity, looks up the customer, gets the fare through [[CAP-012-quote-a-fare|Quote a fare]] and writes BKHOLD to FERRYMASTER. The hold lasts 10 minutes."
 },
 {
  "n": 5,
  "from": "",
  "to": "",
  "text": "[[CAP-015-take-payment|Take payment]]. The channel sends the customer to Tidepay's hosted payment page. Tidepay reports the outcome to Booking."
 },
 {
  "n": 6,
  "from": "",
  "to": "",
  "text": "[[CAP-013-reserve-a-crossing|Confirm booking]]. Booking writes BKCONF to FERRYMASTER and marks the booking confirmed once the ledger accepts it."
 },
 {
  "n": 7,
  "from": "[[booking-building-blocks|Booking]]",
  "to": "[[notifications-building-blocks|Notifications]]",
  "text": "[[booking-building-blocks|Booking]] → [[notifications-building-blocks|Notifications]]: publishes the state change, over [[booking-building-blocks#CON-002 Booking state changed|Booking state changed]]. Notifications then sends the confirmation ([[FLO-003-notify-on-change|Notify on change]]). This is [[CAP-022-notify-customer|Notify customer]]."
 }
]
