SELECT
    ngo_ngo.id,
    ngo_ngo.name,
    COUNT(registrations_registration.id) AS total_registrations
FROM ngo_ngo
LEFT JOIN ngo_ngoavailability
    ON ngo_ngo.id = ngo_ngoavailability.ngo_id
LEFT JOIN registrations_registration
    ON ngo_ngoavailability.id = registrations_registration.activity_id
GROUP BY
    ngo_ngo.id,
    ngo_ngo.name
ORDER BY total_registrations DESC, ngo_ngo.name;
