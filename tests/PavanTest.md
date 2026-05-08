# Tests for Login, Register, and Strava Integration

I focused my testing on the core foundation of the app — making sure users can sign up and log in securely, and that the Strava integration works smoothly for pulling in activity data. I also spent a lot of time on the security side to make sure passwords are safe and that the OAuth flow handles errors correctly.

Main things I was checking:
- User registration and login flows (including error handling)
- Password hashing and session security
- Strava account connection and disconnection
- Synchronising activities and handling API rate limits
- Calorie estimation when Strava data is missing

---

## Test Table

| Test ID | Feature | Test Type | What I Tested | Test Data | Expected Result | Actual Result | Pass/Fail |
|---|---|---|---|---|---|---|---|
| P01 | User Signup | Manual | Register a new customer account | Valid email, username, password | Account created, redirected to survey | Account created and survey page shown | Pass |
| P02 | Signup Validation | Validation | Signup with email already in use | Existing email | Error message shown, no account created | Flash message: "Email address already registered" | Pass |
| P03 | Signup Password | Validation | Password too short | Password: "abc" | Front-end or back-end validation error | Browser validation blocked submission | Pass |
| P04 | Login flow | Manual | Login with valid account | user: pavan, pass: correct | Redirected to home page | Logged in successfully | Pass |
| P05 | Login Security | Security | Login with case-insensitive username | user: PAVAN | Login should still work | User logged in regardless of casing | Pass |
| P06 | Logout | Manual | Logout from active session | Click logout | Session cleared, cannot visit home via back button | Logged out and redirected to login | Pass |
| P07 | Strava Connect | Manual | Click connect to Strava button | Valid Strava credentials | Redirects to Strava, then back to settings with tokens saved | Tokens saved and Strava status updated | Pass |
| P08 | Strava Sync | Manual | Sync activities from Strava | 5 new activities on Strava | Activities appear in local database with maps and calories | All activities synced with correct data | Pass |
| P09 | Strava Sync Rate Limit | Edge Case | Try syncing twice within 15 minutes | Click sync twice | Second sync is skipped to protect API limits | Redirected to activities page without redundant API call | Pass |
| P10 | Strava Calorie Fallback | Manual | Sync activity without Strava calories | Run (5km, 70kg weight) | App calculates fallback calories based on MET | Fallback calories calculated (approx 363 kcal) | Pass |
| P11 | Strava Disconnect | Manual | Disconnect Strava account | Click disconnect | Tokens cleared from database | Strava disconnected and tokens removed | Pass |

---

## Security Testing

| Test ID | Risk | What I Tested | Expected Result | Actual Result | Pass/Fail |
|---|---|---|---|---|---|
| PS01 | Password Hashing | Check `password_hash` in User table | DB inspection | Hashed string, not plain text | Stored as pbkdf2:sha256 hash | Pass |
| PS02 | Session Hijacking | Access home after clearing cookies | Browser cookies cleared | Redirected to login | Access denied as expected | Pass |
| PS03 | Strava Token Security | Check if tokens are visible to other users | Request via API | Only accessible by owner | Tokens correctly scoped to user session | Pass |
| PS04 | Parameter Tampering | Change user ID in URL to view someone else's settings | `/settings?user_id=1` | Should only show current user's settings | Settings page uses session user, not URL ID | Pass |

---

## Bugs Found During Testing

| Bug | Cause | Fix |
|---|---|---|
| Signup allowed duplicate emails | The query only checked for duplicate usernames | Added `User.query.filter_by(email=email).first()` check to signup route |
| Strava sync duplicated activities | Incremental sync check was only looking at time, not unique IDs | Added a check for `StravaActivity.query.filter_by(strava_id=a['id']).first()` |
| Password change allowed empty password | Validation was missing for the change-password form | Added `if not new_password:` check and flash message |
| Strava map didn't load | Polyline was being escaped in the template | Added the `|safe` filter to the polyline string |
| Contact Admin button did nothing | Form action was pointing to a missing route | Updated the form to post to `/messages/send` with the admin's fixed ID |

---

## Team Testing Responsibility

I swapped testing with Moham. I checked the Home dashboard, the Admin features, the Events system, and the Leaderboard he built. It was interesting to see how the admin tools manage the whole platform.

| Feature Area | Main Developer | Main Tester | Testing Type |
|---|---|---|---|
| Home & Leaderboard | Moham | Pavan | Manual, Data integrity |
| Admin & Events | Moham | Pavan | Manual, Security, Validation |
| Login & Register | Pavan | Moham | Manual, Validation, Security |
| Strava Integration | Pavan | Moham | Manual, API Integration, Edge case |

---

## Test Table for Moham's Pages

| Test ID | Feature | Test Type | What I Tested | Test Data | Expected Result | Actual Result | Pass/Fail | Tested By |
|---|---|---|---|---|---|---|---|---|
| PT01 | Home Page Stats | Manual | View stats after logging activities | Logged 2 runs (10km total) | Total distance shows 10.0km | Home page updated correctly | Pass | Pavan |
| PT02 | Home Page Cards | Manual | Check session count this week | Log 3 sessions | Session card shows 3 | Count was accurate | Pass | Pavan |
| PT03 | Admin Dashboard | Manual | Search for users in admin dashboard | Search: "John" | Only users matching "John" are displayed | Search filtered correctly | Pass | Pavan |
| PT04 | Admin User Delete | Security | Admin deletes a customer user | User ID: 15 | User and all related data deleted | User removed and cascading delete worked | Pass | Pavan |
| PT05 | PT Approval | Manual | Approve a pending PT application | New PT user | User role approved and TrainerProfile created | User approved and profile initialized | Pass | Pavan |
| PT06 | Event Creation | Manual | Create a new marathon event | Name: City Run | Event appears on events page | Event created successfully | Pass | Pavan |
| PT07 | Event Join | Manual | Customer joins an event | Click "Join" | User appears in participant list for admin | Joined correctly | Pass | Pavan |
| PT08 | Leaderboard Ranking | Manual | Check top 3 rankings | Users with 500, 300, 100 pts | Users appear in order: 500, 300, 100 | Ranking order correct | Pass | Pavan |
| PT09 | Leaderboard Search | Manual | Search for user on leaderboard | Search: "moham" | Only moham appears in the list | Search filtered correctly | Pass | Pavan |
| PT10 | Settings Update | Manual | Change profile display name | New name: "Pavan S." | Name updates across the app | Name updated successfully | Pass | Pavan |

---

## Testing Conclusion

Overall, the core systems are very stable. The OAuth flow for Strava is secure and handles token refreshes perfectly. Cross-testing with Moham was vital, especially for the role-based access to the admin features. The home page and leaderboard are correctly pulling the activity data we sync from Strava and manual logs. Everything is ready for the final hand-in.
