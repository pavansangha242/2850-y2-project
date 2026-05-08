# Tests for Home, Admin Dashboard, Events, and Leaderboard

I went through and manually tested all the core components I built for the app — the main Home dashboard, the Admin management tools, the Events system, and the Leaderboard. I wanted to make sure all the data was pulling through correctly and that the admin could manage the platform without any hitches.

Main things I was checking:
- Home page statistics and activity cards
- Admin dashboard (searching users, deleting accounts, approving PTs)
- Event creation and participant lists
- Leaderboard rankings and points calculation
- Role-based access (making sure only admins can see admin tools)

---

## Test Table

| Test ID | Feature | Test Type | What I Tested | Test Data | Expected Result | Actual Result | Pass/Fail |
|---|---|---|---|---|---|---|---|
| M01 | Home Page Stats | Manual | View total stats for a new user | New account | All stats show 0 | Stats showed 0 as expected | Pass |
| M02 | Home Page Stats | Manual | View stats after logging activities | Logged 2 runs (10km total) | Total distance shows 10.0km | Home page updated correctly | Pass |
| M03 | Home Page Cards | Manual | Check session count this week | Log 3 sessions | Session card shows 3 | Count was accurate | Pass |
| M04 | Admin Dashboard | Manual | Search for users in admin dashboard | Search: "John" | Only users matching "John" are displayed | Search filtered correctly | Pass |
| M05 | Admin User Delete | Security | Admin deletes a customer user | User ID: 15 | User and all related data (messages, results) deleted | User removed and cascading delete worked | Pass |
| M06 | PT Approval | Manual | Approve a pending PT application | New PT user | User role approved and TrainerProfile created | User approved and profile initialized | Pass |
| M07 | PT Rejection | Manual | Reject a pending PT application | New PT user | PT user is deleted from the system | User removed from database | Pass |
| M08 | Event Creation | Manual | Create a new marathon event | Name: City Run, Date: 2026-06-01 | Event appears on events page | Event created successfully | Pass |
| M09 | Event Validation | Validation | Create event with missing date | Name: "Marathon" | Error message appears, event not saved | Error message shown: "Please enter an event name and date." | Pass |
| M10 | Participant View | Manual | View participants for an event | Event with 3 signups | List of users registered for the event is shown | All 3 participants displayed | Pass |
| M11 | Leaderboard | Manual | Check top 3 rankings | Users with 500, 300, 100 pts | Users appear in order: 500, 300, 100 | Ranking order correct | Pass |
| M12 | Leaderboard Search | Manual | Search for user on leaderboard | Search: "moham" | Only moham appears in the list | Search filtered correctly | Pass |
| M13 | Leaderboard Points | Manual | Verify points for activity | Log a gym workout | Points increase on leaderboard | Points updated after refresh | Pass |

---

## Security Testing

| Test ID | Risk | What I Tested | Expected Result | Actual Result | Pass/Fail |
|---|---|---|---|---|---|
| MS01 | Admin Route Access | Access `/admin` as a regular customer | Redirected to home with access denied message | Redirected with "Administrator privileges required" flash | Pass |
| MS02 | Unauthorized Admin POST | Try to POST to `/admin/add-event` as customer | Postman/CURL request | 302 redirect with error | Request blocked by admin check | Pass |
| MS03 | Leaderboard Privacy | Check if admins appear on leaderboard | Admin account | Admins should be excluded from rankings | Admins do not show on leaderboard | Pass |
| MS04 | SQL Injection | Search for users with `' OR 1=1 --` | Admin search field | No data leak, literal search performed | Handled safely by SQLAlchemy | Pass |

---

## Bugs Found During Testing

| Bug | Cause | Fix |
|---|---|---|
| Home page stats didn't update instantly | Browser was caching the response | Added `Cache-Control: no-cache` headers to the home route |
| Leaderboard showed admins | The query was getting all users regardless of role | Added `.filter(User.role != 'administrator')` to leaderboard query |
| Admin dashboard crashed with no events | Template tried to loop over `None` | Added a default empty list in the route and `{% if %}` check in template |
| PT Approval didn't create profile | The logic was skipping profile creation if the user already existed | Added a check to create `TrainerProfile` if one doesn't exist during approval |
| Leaderboard crash on empty DB | Calculation function didn't handle zero users | Added a check to return an empty list if no users exist |

---

## Teammate Testing

Me and Pavan swapped testing — she built the login, register, and strava integration pages and I went through all of them. Testing someone else's code is much better because you don't have the same biases as the person who wrote it.

| Feature Area | Main Developer | Main Tester | Testing Type |
|---|---|---|---|
| Login & Register | Pavan | Moham | Manual, Validation, Security |
| Strava Integration | Pavan | Moham | Manual, API Integration, Edge case |
| Home & Leaderboard | Moham | Pavan | Manual, Data integrity |
| Admin & Events | Moham | Pavan | Manual, Security, Validation |

---

## Test Table for Pavan's Pages

| Test ID | Feature | Test Type | What I Tested | Test Data | Expected Result | Actual Result | Pass/Fail | Tested By |
|---|---|---|---|---|---|---|---|---|
| MT01 | Signup | Manual | Register new user with valid data | user: test, pass: test1234 | Account created and logged in | Account created and redirected to home | Pass | Moham |
| MT02 | Signup Validation | Validation | Register with existing username | user: moham | Error message: "Username already taken" | Correct error message shown | Pass | Moham |
| MT03 | Login | Manual | Login with valid credentials | user: moham, pass: valid | Redirected to dashboard | Logged in successfully | Pass | Moham |
| MT04 | Login Failure | Validation | Login with wrong password | user: moham, pass: wrong | Error message: "Invalid username or password" | Correct error message shown | Pass | Moham |
| MT05 | Logout | Manual | Click logout button | Active session | Session cleared, redirected to login | Logged out correctly | Pass | Moham |
| MT06 | Strava Connect | Manual | Click connect to Strava button | Valid Strava credentials | Redirects to Strava, then back to settings with tokens saved | Tokens saved and Strava status updated | Pass | Moham |
| MT07 | Strava Sync | Manual | Sync activities from Strava | 5 new activities on Strava | Activities appear in local database with maps and calories | All activities synced correctly | Pass | Moham |
| MT08 | Strava Sync Rate Limit | Edge Case | Try syncing twice within 15 minutes | Click sync twice | Second sync is skipped to protect API limits | Redirected without redundant API call | Pass | Moham |
| MT09 | Strava Calorie Fallback | Manual | Sync activity without Strava calories | Run (5km, 70kg weight) | App calculates fallback calories based on MET | Fallback calories calculated (approx 363 kcal) | Pass | Moham |
| MT10 | Password Security | Security | Check if password is plain text in DB | SQL query | Should be hashed | Password stored as pbkdf2:sha256 hash | Pass | Moham |

---

## Testing Conclusion

The testing process was really useful for catching some admin dashboard crashes and the leaderboard filtering bug. Working with Pavan on the cross-testing meant we could be sure that the core auth and the new admin features worked well together. The Strava integration was the trickiest bit to test because of the API limits, but the 15-minute rate limit Pavan added handles it well. Everything is ready for the final submission.
