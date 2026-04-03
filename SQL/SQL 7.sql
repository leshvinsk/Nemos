SELECT
    auth_user.username,
    auth_user.email,
    auth_user.password,
    auth_group.name AS role_name
FROM auth_user
JOIN auth_user_groups
    ON auth_user.id = auth_user_groups.user_id
JOIN auth_group
    ON auth_user_groups.group_id = auth_group.id
ORDER BY auth_group.name, auth_user.username;
