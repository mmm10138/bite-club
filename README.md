## Bite Club 

Restaurant discovery and reviews for New York. 

Search the city's restaurants, see their official health grade, and read what the Bite Club community thinks about the food, the room and the service. 

Built solo for NYU Tandon LeetCode Bootcamp, Fall 2026.

**Live**: https://https://bite-club-pt95.onrender.com/

The assignment suggested the Yelp Fusion API. Yelp has since moved it to paid plans with a free trial. I pickee NYC Open Data because it costs nothing, and it had the Department of Health letter grade for every restaurant in the city.

The trade-off is that it has no ratings nor photos. That turned out to suit the project. With no Yelp score to sit beside it, the Bite Club community rating is the only rating on the page.


## What it does
- **Search** restaurants by keyword across roughly 27,000 NYC establishments
- **Restaurant pages** with cuisine, address, phone and the city's health grade
- **Reviews** rated on four axes: food, atmosphere, service, overall, what you ordered, when
  you went, and whether you'd go back
- **Community averages** per axis, computed across all reviews

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Flask | Four routes and two tables. Django would be weight with no payoff |
| Database | SQLite | File-based, no server to run, right size for this |
| Data source | NYC Open Data (Socrata) | Free, keyless, and it has health grades |
| Frontend | Jinja templates, hand-written CSS | No build step, nothing to break during a demo |

## The data problem

The city publishes **inspections**, not restaurants. The dataset has
~297,000 rows and a restaurant inspected eight times appears eight
times. Three things had to happen before it was usable:

**Deduplication.** Rows are requested newest-first, then collapsed by
`camis`, the city's permanent restaurant ID. The first row seen for each
ID is its most recent inspection.

**Grades are not all grades.** The `grade` column mixes A, B and C with
status codes: N (not yet graded), Z and P (grade pending). Showing a Z
next to an A would imply it's a grade. They're separated, and only real
grades get a badge.

**Formatting.** Names arrive in ALL CAPS, addresses split across two
columns. Both are normalised in one place, so templates never see the
city's column names.

## Failure handling
**Caching.** Results are held in memory for an hour. Inspections update
daily at most, so nothing is lost in freshness, and it keeps the app
well inside the API's rate limit. Failures are deliberately not cached,
or one bad response would blank the site for an hour.

**Graceful degradation.** A failed API call returns an empty result
rather than raising, and the page says which of two things happened:
nothing matched the search, or the city's service is unavailable. Those
are different problems and the user deserves to know which one they hit.

I hit real 503s from rate limiting during development, which is what
prompted both.

## Known limits

- **Usernames are not authenticated.** A name identifies a reviewer, it
  doesn't prove anything. Real accounts were cut to keep the scope
  honest for a solo build in eight days
- **Grade coverage is patchy.** Most restaurants show no grade at any
  given moment, because their latest inspection hasn't produced one.
  Older graded inspections are used where they fall inside the fetched
  window, but not always
- **No pagination.** Search returns the first 20 results
- **SQLite doesn't persist on serverless hosts**, so deployment needs a
  host with a disk

## Next

1. Password authentication
2. Filter and sort by community rating rather than by city grade
3. Map view, using coordinates the API already returns