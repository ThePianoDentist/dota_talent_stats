
random notes:

postgresql setup:

CREATE TABLE matches (ID BIGINT NOT NULL PRIMARY KEY, data jsonb NOT NULL); ???
(I think. I started with json and converted to jsonb so I could just query the parts of the json I wanted
...turns out loading 12billion lines of json into memory is too much for my 4gb RAM laptop)


issues:
Could put a where on the query to only get games with our_hero in
(this would be way easier if it was proper relational db)
probably best to just keep whole hero query, train the models for each at the same time

no sqlalchemy integration.

- Should switch to using https://github.com/odota/dotaconstants/blob/master/build/hero_abilities.json
that I added to odota. However this is only 'current' ability data.
would mean it would not be applicable to past patches where talents change....
but does anyone really care about making new choices based on past patches?
Maybe when straight after a very small patch. meta roughly the same, but now this script either has to use insufficient data
to avoid overfitting...or just breaks using the large mass of older data

maybe think of smart way to, after small patch, not allow searches for talent-patched heroes, but still allow searching on old data for
unchanged heroes.

thats a good point, i probably need to be filtering query by patch or timestamps (index this)

- Properly learn boosting/bagging stuff and which if any I should be doing