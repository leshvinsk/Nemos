SELECT
    ngo_ngoavailability.id,
    ngo_ngo.name,
    ngo_ngoavailability.service_type,
    ngo_ngoavailability.max_slots,
    COUNT(registrations_registration.id) AS registration_count
FROM ngo_ngoavailability
JOIN ngo_ngo
    ON ngo_ngoavailability.ngo_id = ngo_ngo.id
LEFT JOIN registrations_registration
    ON ngo_ngoavailability.id = registrations_registration.activity_id
GROUP BY
    ngo_ngoavailability.id,
    ngo_ngo.name,
    ngo_ngoavailability.service_type,
    ngo_ngoavailability.max_slots
HAVING COUNT(registrations_registration.id) >= ngo_ngoavailability.max_slots
ORDER BY ngo_ngoavailability.service_date;
