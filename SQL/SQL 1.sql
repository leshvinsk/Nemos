SELECT
    ngo_ngoavailability.id,
    ngo_ngo.name,
    ngo_ngoavailability.service_type,
    ngo_ngoavailability.location,
    ngo_ngoavailability.service_date,
    ngo_ngoavailability.cutoff_time,
    ngo_ngoavailability.max_slots
FROM ngo_ngoavailability
JOIN ngo_ngo
    ON ngo_ngoavailability.ngo_id = ngo_ngo.id
WHERE ngo_ngoavailability.is_active = 1
  AND ngo_ngo.is_active = 1
ORDER BY ngo_ngoavailability.service_date;
