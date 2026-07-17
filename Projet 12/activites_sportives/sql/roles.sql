-- Creation du role sport_role
CREATE ROLE sport_role;

-- Attribution des droits sur la base
GRANT CONNECT ON DATABASE activitessportives TO sport_role;
GRANT USAGE ON SCHEMA public TO sport_role;

-- Attribution des droits sur kestra
GRANT ALL ON DATABASE kestra TO sport_role;

-- Attribution du role sport_role a l'utilisateur sport_user
GRANT sport_role TO sport_user;