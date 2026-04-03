SELECT
    auth_user.username,
    ngo_ngo.name,
    ngo_ngoavailability.service_type,
    ngo_ngoavailability.location,
    ngo_ngoavailability.service_date,
    registrations_registration.registered_at
FROM registrations_registration
JOIN auth_user
    ON registrations_registration.employee_id = auth_user.id
JOIN ngo_ngoavailability
    ON registrations_registration.activity_id = ngo_ngoavailability.id
JOIN ngo_ngo
    ON ngo_ngoavailability.ngo_id = ngo_ngo.id
ORDER BY auth_user.username, ngo_ngoavailability.service_date;
