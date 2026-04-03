SELECT
    ngo_ngoavailability.id,
    ngo_ngo.name,
    ngo_ngoavailability.service_type,
    COUNT(registrations_registration.id) AS registration_count
FROM ngo_ngoavailability
JOIN ngo_ngo
    ON ngo_ngoavailability.ngo_id = ngo_ngo.id
LEFT JOIN registrations_registration
    ON ngo_ngoavailability.id = registrations_registration.activity_id
GROUP BY
    ngo_ngoavailability.id,
    ngo_ngo.name,
    ngo_ngoavailability.service_type
ORDER BY ngo_ngoavailability.service_date;
