-- Demo data: 9 destinations and 14 travel offers (realistic examples, not a real agency's prices).
-- Includes one SOLD_OUT and one ARCHIVED offer to test that the assistant never sells them.

INSERT INTO destinations (name, country, city, description) VALUES
  ('Hammamet Coast', 'Tunisia', 'Hammamet', 'Sandy beaches, the Yasmine marina and Tunisia''s best-known thalasso centers.'),
  ('Tozeur Sahara', 'Tunisia', 'Tozeur', 'Gateway to the Sahara: palm oases, mountain canyons and desert camps near Douz.'),
  ('Tabarka Coral Coast', 'Tunisia', 'Tabarka', 'Green north-west coast with coral reefs, cork oak forests and a Genoese fort.'),
  ('Djerba Island', 'Tunisia', 'Djerba', 'Mediterranean island of white beaches, palm groves and traditional villages.'),
  ('Istanbul', 'Turkey', 'Istanbul', 'The city on two continents: Ottoman mosques, Byzantine churches and the Bosphorus.'),
  ('Sharm El Sheikh', 'Egypt', 'Sharm El Sheikh', 'Red Sea resort town famous for coral reefs and Ras Mohammed national park.'),
  ('Marrakech', 'Morocco', 'Marrakech', 'The red city: riads, souks, the Jemaa el-Fna square and the Atlas mountains.'),
  ('Mecca & Medina', 'Saudi Arabia', 'Mecca', 'The two holy cities for Umrah pilgrimage.'),
  ('Dubai', 'UAE', 'Dubai', 'Skyscrapers, desert safaris and some of the world''s biggest shopping malls.');

INSERT INTO travel_offers (title, description, "destinationId", price, duration, "startDate", "endDate", "maxParticipants", "availableSeats", status)
SELECT o.title, o.descr, d.id, o.price, o.duration, o.s::timestamp, o.e::timestamp, o.maxp, o.seats, o.status::"OfferStatus"
FROM (VALUES
  ('Hammamet Family Beach Week', 'All-inclusive 4-star hotel in Yasmine Hammamet with kids club, daily access to the aquapark, and airport transfers. Children under 12 stay at half price.', 1450, '8 Days / 7 Nights', '2026-10-18', '2026-10-25', 40, 22, 'PUBLISHED', 'Hammamet Coast'),
  ('Hammamet Thalasso Weekend', 'Three nights in a 5-star seafront hotel with half board and four thalassotherapy treatments: hammam, seawater pool, algae wrap and massage.', 780, '4 Days / 3 Nights', '2026-11-06', '2026-11-09', 20, 8, 'PUBLISHED', 'Hammamet Coast'),
  ('Tozeur Sahara Desert Adventure', '4x4 tour to the Ong Jemel Star Wars film sets and the Chebika and Tamerza mountain oases, then one night in a desert camp near Douz with a camel ride at sunset.', 1100, '4 Days / 3 Nights', '2026-11-13', '2026-11-16', 16, 5, 'PUBLISHED', 'Tozeur Sahara'),
  ('New Year in the Sahara', 'Celebrate New Year in a desert camp near Douz with a traditional dinner show, camel trek and 4x4 dune drive.', 1650, '5 Days / 4 Nights', '2026-12-29', '2027-01-02', 30, 0, 'SOLD_OUT', 'Tozeur Sahara'),
  ('Tabarka Diving & Coral Coast', 'Three guided dives on the Tabarka coral reefs (beginners welcome), a hike in the cork oak forest of Ain Draham, and a 3-star hotel with half board.', 990, '5 Days / 4 Nights', '2026-10-23', '2026-10-27', 12, 6, 'PUBLISHED', 'Tabarka Coral Coast'),
  ('Tabarka Jazz Summer Nights', 'Tickets for the Tabarka Jazz Festival with a beach hotel stay.', 850, '4 Days / 3 Nights', '2026-07-10', '2026-07-13', 25, 0, 'ARCHIVED', 'Tabarka Coral Coast'),
  ('Djerba Budget Escape', 'A 3-star hotel in Midoun with half board, and a guided tour of the Guellala pottery village and the El Ghriba synagogue.', 690, '5 Days / 4 Nights', '2026-10-30', '2026-11-03', 30, 16, 'PUBLISHED', 'Djerba Island'),
  ('Istanbul City Discovery', 'Return flights Tunis-Istanbul, a 4-star hotel in Sultanahmet, guided visits of the Blue Mosque, Hagia Sophia and Topkapi Palace, a Bosphorus cruise and free time in the Grand Bazaar.', 2390, '6 Days / 5 Nights', '2026-11-20', '2026-11-25', 25, 12, 'PUBLISHED', 'Istanbul'),
  ('Istanbul & Cappadocia Combo', 'Four nights in Istanbul and three nights in a Cappadocia cave hotel, with domestic flight, guided tours and the underground city of Derinkuyu. Hot-air balloon flight available as an option for 450 DT.', 3450, '9 Days / 8 Nights', '2027-04-10', '2027-04-18', 20, 20, 'PUBLISHED', 'Istanbul'),
  ('Sharm El Sheikh Red Sea All-Inclusive', 'Return flights, a 5-star all-inclusive resort on Naama Bay, and a full-day snorkeling boat trip to Ras Mohammed national park.', 2750, '8 Days / 7 Nights', '2026-12-05', '2026-12-12', 30, 14, 'PUBLISHED', 'Sharm El Sheikh'),
  ('Marrakech Imperial Escape', 'Traditional riad in the medina, guided tour of the souks and Jemaa el-Fna, a day trip to the Atlas mountains, and dinner under the stars in the Agafay desert.', 2600, '7 Days / 6 Nights', '2027-02-14', '2027-02-20', 18, 9, 'PUBLISHED', 'Marrakech'),
  ('Umrah Economy Package', 'Return flights, Umrah visa, 3-star hotels 600 meters from the Haram: 5 nights in Mecca and 5 nights in Medina, with a religious guide and ground transport.', 4900, '11 Days / 10 Nights', '2027-01-15', '2027-01-25', 45, 18, 'PUBLISHED', 'Mecca & Medina'),
  ('Umrah Ramadan Premium', 'The last ten nights of Ramadan in 5-star hotels within walking distance of the Haram, with flights, visa, suhoor and iftar included.', 9800, '12 Days / 11 Nights', '2027-02-26', '2027-03-09', 30, 4, 'PUBLISHED', 'Mecca & Medina'),
  ('Dubai Shopping Festival', 'Flights, a 4-star hotel near Dubai Mall during the Dubai Shopping Festival, an evening desert safari and Burj Khalifa observation deck tickets.', 3900, '6 Days / 5 Nights', '2027-01-08', '2027-01-13', 20, 11, 'PUBLISHED', 'Dubai')
) AS o(title, descr, price, duration, s, e, maxp, seats, status, dest)
JOIN destinations d ON d.name = o.dest;
