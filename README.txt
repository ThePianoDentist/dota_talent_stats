
random notes:

postgresql setup:

CREATE TABLE matches (ID BIGINT NOT NULL PRIMARY KEY, data json NOT NULL);


issues:
no sqlalchemy integration.
is it worth it when just storing and using json?
open_dota api used because gives damage breakdowns which allow me to calculate physical damage/magical damage
# TODO first damage breakdowns may be naive and wrong. i.e bb quills is a spell but does physical
# which does it get put in?