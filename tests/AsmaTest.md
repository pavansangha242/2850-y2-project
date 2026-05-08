# Tests for Swimming, Cycling, Walking, Running, and Gym

So I went through all my pages manually — swimming, running, cycling, walking and gym. I basically just used them like a normal user would, trying to log workouts, break things with bad inputs, and make sure nothing crashes. I also checked some security stuff like whether you can delete someone elses workout by messing with the URL, which you obviously shouldnt be able to do.

The main things I was checking:
- Logging workouts
- Whether speed and pace gets worked out automatically
- Whether calories get calculated when you dont enter them yourself
- That your recent workouts actually show up after logging
- Deleting workouts
- That the dashboard updates properly
- That the app doesnt just fall apart when something is missing or wrong

---

## Test Table

| Test ID | Feature | Test Type | What I Tested | Test Data | Expected Result | Actual Result | Pass/Fail |
|---|---|---|---|---|---|---|---|
| T01 | Swimming log form | Manual | Submit valid swim workout | Distance: 1km, Duration: 30, Laps: 40 | Swim is saved and shown in recent swims table | Swim appeared in recent swims table | Pass |
| T02 | Swimming page | Manual | Leave distance blank but enter laps | Laps: 20, Duration: 30 | Distance is estimated from laps and workout saves | Workout saved and distance was estimated from laps | Pass |
| T03 | Swimming page | Manual/Validation | Submit swim with no duration | Distance: 1.0, Duration blank | App should not crash; duration saved as 0 or validation message appears | App did not crash and handled the missing duration | Pass |
| T04 | Swimming page | Manual | Delete a swim workout | Click Delete | Workout is removed from the table | Swim was removed from the table | Pass |
| T05 | Running page | Manual | Log a valid run | Distance: 5km, Duration: 30 | Pace is calculated and run appears in table | Run appeared in table with calculated pace | Pass |
| T06 | Running page | Manual | Leave calories blank | Distance: 5km, Duration: 30 | Calories are auto-calculated | Calories were calculated automatically | Pass |
| T07 | Walking page | Manual | Log a walk with steps | Distance: 2km, Duration: 25, Steps: 3000 | Walk saves and appears in recent walks | Walk appeared in recent walks table | Pass |
| T08 | Cycling page | Manual | Log cycling without speed | Distance: 20km, Duration: 60 | Average speed is calculated automatically | Average speed was calculated automatically | Pass |
| T09 | Cycling page | Manual | Leave calories blank | Distance: 20km, Duration: 60 | Calories are calculated using cycling MET | Calories were calculated using cycling MET | Pass |
| T10 | Progress page | Manual | Check progress after logging workouts | Logged swim, run, walk, and cycle activities | Progress page shows updated sessions, distance, calories, and charts | Progress page updated correctly | Pass |
| T11 | Swimming page | Validation | Submit negative distance | Distance: -5 | App should reject it or avoid broken calculations | App avoided crashing and handled the invalid value safely | Pass |
| T12 | Running page | Validation | Submit duration as 0 | Distance: 5, Duration: 0 | App should not divide by zero or crash | App did not crash | Pass |
| T13 | Cycling page | Validation | Submit text in number field | Distance: abc | Browser prevents input or backend handles safely | Browser prevented invalid numeric input | Pass |
| T14 | Walking page | Validation | Submit empty form | Blank fields | App should not crash and should use defaults or show an error | App did not crash and handled missing values | Pass |
| T15 | Delete route | Security | Try deleting another user's workout by changing URL ID | `/running/delete/5` | App should only delete if workout belongs to logged-in user | Other user's workout was not deleted | Pass |

---

## Security Testing

| Test ID | Risk | What I Tested | Expected Result | Actual Result | Pass/Fail |
|---|---|---|---|---|---|
| S01 | Unauthenticated access | Visit exercise page without logging in | User is redirected to login | User was redirected to login | Pass |
| S02 | ID manipulation | Change delete URL to another user's activity ID | Activity is not deleted | Activity was not deleted | Pass |
| S03 | Invalid numeric input | Submit negative or empty distance/duration | App does not crash | App handled the input safely | Pass |
| S04 | Form tampering | Submit missing fields through browser dev tools | Backend handles missing values safely | Missing values were handled safely | Pass |
| S05 | Cross-user data | Log in as another user and check progress page | Only that user's activities are shown | Only the logged-in user's activities were shown | Pass |

---

## Bugs Found During Testing

Honestly this is where it got a bit painful. Some of these took me a while to figure out, especially the calories one because the numbers just showed as 0 and it wasnt obvious why at first. Once I actually dug into it the causes made sense but finding them in the first place was annoying.

| Bug | Cause | Fix |
|---|---|---|
| Calories sometimes showed as 0 | User weight was missing, so calorie calculation returned `None` | Added a fallback weight value when user weight is missing |
| Cycling calorie calculation crashed | Cycling route called `get_running_met()` instead of `get_cycling_met()` | Replaced it with `get_cycling_met(final_speed)` |
| Swimming progress chart did not show | Swimming uses `pace_per_100m`, while other sports use `pace_per_km` or speed | Added separate logic for swimming pace in the progress page |
| Progress page showed no data for the logged-in user | Progress route used `User.query.first()` instead of the session user | Changed it to get the current user from `session["username"]` |
| Home page calories showed as 0 | Activities were saved under a different user ID because `get_current_user_id()` returned a fixed value | Updated user lookup to use the logged-in session user |
| Survey page crashed when survey did not exist | Template tried to access `survey.last_updated` when `survey` was `None` | Added an `{% if survey %}` check before displaying survey fields |

---

## Gym Page Testing

I tested the gym page the same way as the others — logging workouts, deleting them, and checking that the PT assignment stuff works properly. I also made sure that customers cant assign exercises since thats only supposed to be for trainers.

The main things I checked:
- Logging a gym workout with valid data
- That the exercise list loads properly
- Deleting a workout
- That submitting without choosing an exercise shows an error
- That only PTs can assign exercises to clients
- That customers cant access things they shouldnt

| Test ID | Feature | Test Type | What I Tested | Test Data | Expected Result | Actual Result | Pass/Fail |
|---|---|---|---|---|---|---|---|
| G01 | Gym page | Manual | Open gym page while logged in | Customer account | Page loads with exercise list and workout history | Page loaded correctly with all exercises | Pass |
| G02 | Gym log form | Manual | Log a valid gym workout | Exercise: Squat, Sets: 3, Reps: 10, Weight: 80kg | Workout is saved and appears in recent workouts | Workout appeared in the table | Pass |
| G03 | Gym log form | Validation | Submit without selecting an exercise | No exercise selected | Error message shown, nothing saved | Error message appeared | Pass |
| G04 | Gym log form | Validation | Submit with empty sets and reps | Sets: blank, Reps: blank | App saves with 0 values and doesnt crash | Workout saved with 0 defaults | Pass |
| G05 | Gym page | Manual | Check weekly sessions count after logging | Log 2 workouts this week | Sessions this week shows 2 | Correct count displayed | Pass |
| G06 | Gym page | Manual | Check top muscle group updates after logging | Log chest exercises | Top muscle group shows Chest | Chest displayed correctly | Pass |
| G07 | Gym delete | Manual | Delete a gym workout | Click Delete | Workout removed from the table | Workout was removed | Pass |
| G08 | Gym delete | Security | Try deleting another user's workout via URL | `/gym/delete/999` | App returns 404, workout not deleted | 404 returned, workout untouched | Pass |
| G09 | Assign exercise | Manual | PT assigns exercise to a client | Exercise: Bench Press, Sets: 4, Reps: 8 | Assignment saved and visible to client | Assignment appeared on client's gym page | Pass |
| G10 | Assign exercise | Security | Customer tries to assign an exercise | Customer account | Error message shown, blocked | Customer was blocked with error message | Pass |
| G11 | Assign exercise | Validation | PT tries to assign without selecting a client | No client selected | Error message shown | Error message appeared | Pass |
| G12 | Gym page | Security | Visit gym page without logging in | No session | Redirected to login | Redirected to login page | Pass |
| G13 | Gym exercises | Manual | Check default exercises are seeded on first load | Fresh database | 16 default exercises appear in the list | All 16 exercises loaded correctly | Pass |
| G14 | Gym log form | Validation | Submit with text in weight field | Weight: abc | Browser or backend handles it safely | Browser blocked invalid input | Pass |

### Gym Bugs Found

| Bug | Cause | Fix |
|---|---|---|
| Top muscle group showed None even after logging | Weekly filter was using wrong date comparison | Fixed the monday date filter to use `>=` correctly |
| PT client list was empty on gym page | Session booking status wasnt being checked properly | Added filter for `status == "confirmed"` in the client query |

---

## Teammate Testing

Me and Jawaher swapped testing — she built the trainer, progress, history and messages pages and I went through all of them. The reason we did it this way is pretty obvious really, if you test your own code you already know how it works and what to avoid so you're way less likely to actually find anything. Having someone else go through it fresh is just better.

I went through everything manually, tried to break things with dodgy inputs and also checked the security stuff like making sure customers cant just open trainer pages by typing the URL. Anything I found I told Jawaher and then checked it again after she fixed it.

---

## Team Testing Responsibility

| Feature Area | Main Developer | Main Tester | Testing Type |
|---|---|---|---|
| Trainer pages | Jawaher | Asma | Manual, validation, security |
| Progress page | Jawaher | Asma | Manual, integration, validation |
| History page | Jawaher | Asma | Manual, filtering, security |
| Messages page | Jawaher | Asma | Manual, validation, security |

---

## Test Table for Jawaher's Pages

| Test ID | Feature | Test Type | What I Tested | Test Data | Expected Result | Actual Result | Pass/Fail | Tested By |
|---|---|---|---|---|---|---|---|---|
| TT01 | Trainer page | Manual | Open trainer listing page while logged in as customer | Customer account | Approved trainers are displayed | Trainers displayed correctly | Pass | Asma |
| TT02 | Trainer page | Manual | Search for a trainer by name | Search: Daniel | Matching trainer appears | Matching trainer appeared | Pass | Asma |
| TT03 | Trainer page | Manual | Filter trainers by specialty | Filter: strength | Relevant trainers are shown | Filter worked correctly | Pass | Asma |
| TT04 | Trainer page | Manual | Select a trainer profile | Click trainer card | Trainer details, booking form, and message form appear | Trainer profile displayed | Pass | Asma |
| TT05 | Trainer booking | Manual | Book a session with valid data | Date: future date, Time: 10:00 | Booking is saved as pending | Booking appeared on trainer dashboard | Pass | Asma |
| TT06 | Trainer booking | Validation | Submit booking with missing date | Time only | Error message shown and booking not saved | Error message shown | Pass | Asma |
| TT07 | Trainer booking | Validation | Submit booking with missing time | Date only | Error message shown and booking not saved | Error message shown | Pass | Asma |
| TT08 | Trainer booking | Validation | Try to book same trainer on same date twice | Same date and trainer | Duplicate booking is prevented | Duplicate booking blocked | Pass | Asma |
| TT09 | Trainer dashboard | Manual | Log in as trainer and view dashboard | Trainer account | Pending bookings are displayed | Booking displayed | Pass | Asma |
| TT10 | Trainer dashboard | Manual | Trainer confirms booking | Click Accept | Booking status changes to confirmed | Booking confirmed | Pass | Asma |
| TT11 | Trainer dashboard | Manual | Trainer declines booking | Click Decline | Booking status changes to cancelled | Booking cancelled | Pass | Asma |
| TT12 | My Clients page | Manual | Check confirmed client appears after booking accepted | Accepted booking | Client appears in My Clients page | Client displayed | Pass | Asma |
| TT13 | My Clients page | Security | Customer tries to open `/pt-clients` | Customer account | Access denied or redirected | Customer redirected/blocked | Pass | Asma |
| TT14 | Trainer dashboard | Security | Customer tries to open `/trainer-dashboard` | Customer account | Access denied or redirected | Customer redirected/blocked | Pass | Asma |
| TT15 | Trainer survey view | Edge case | Open client survey when client has no survey | Client without survey | Page shows "no survey submitted" instead of crashing | Message shown | Pass | Asma |
| TT16 | Trainer messages | Manual | Customer sends message to trainer | Message: Hello | Message saves and trainer can see it | Trainer received message | Pass | Asma |
| TT17 | Trainer messages | Validation | Submit empty message | Blank message | Message is not saved and error appears | Empty message blocked | Pass | Asma |
| TT18 | Trainer inbox | Manual | Trainer replies to client | Message: Thanks | Client can see trainer reply | Reply displayed | Pass | Asma |
| TT19 | Trainer inbox | Manual | Open a conversation | Existing client message | Full message thread appears in order | Thread displayed correctly | Pass | Asma |
| TT20 | Trainer inbox | Security | Customer tries to open `/trainer/inbox` | Customer account | Access denied or redirected | Customer redirected/blocked | Pass | Asma |
| TT21 | Messages page | Manual | Open messages page as customer | Customer account | Conversations are listed | Conversations displayed | Pass | Asma |
| TT22 | Messages page | Manual | Select a trainer conversation | Click conversation | Chat thread opens | Thread opened correctly | Pass | Asma |
| TT23 | Messages page | Manual | Send valid direct message | Message: Hi trainer | Message appears in conversation | Message displayed | Pass | Asma |
| TT24 | Messages page | Validation | Submit message with only spaces | `"   "` | Message should not save | Message blocked | Pass | Asma |
| TT25 | Messages page | Manual | Check unread count after new message | New unread message | Unread badge updates | Badge updated | Pass | Asma |
| TT26 | Messages page | Manual | Open group/event chat if available | Event chat | Group messages appear | Group messages displayed | Pass | Asma |
| TT27 | Messages page | Edge case | Open messages page with no conversations | New account | Empty state shown, no crash | Empty state shown | Pass | Asma |
| TT28 | Messages page | Security | Tamper with trainer ID in URL | `/messages?trainer_id=99999` | App should not crash | Page handled invalid ID safely | Pass | Asma |
| TT29 | Progress page | Manual | Open progress page with existing activities | User with workouts | Stats and charts are displayed | Progress data displayed | Pass | Asma |
| TT30 | Progress page | Manual | Filter progress by Running | `/progress?sport=Running` | Running-only stats shown | Running stats displayed | Pass | Asma |
| TT31 | Progress page | Manual | Filter progress by Swimming | `/progress?sport=Swimming` | Swimming stats and pace chart shown | Swimming stats displayed | Pass | Asma |
| TT32 | Progress page | Manual | Filter progress by Cycling | `/progress?sport=Cycling` | Cycling speed/pace data shown | Cycling stats displayed | Pass | Asma |
| TT33 | Progress page | Manual | Filter progress by Walking | `/progress?sport=Walking` | Walking stats shown | Walking stats displayed | Pass | Asma |
| TT34 | Progress page | Edge case | Open progress page with no activities | New user | "No data yet" message appears | Empty state displayed | Pass | Asma |
| TT35 | Progress page | Validation | Check charts after activity with zero distance | Distance: 0 | App should not divide by zero or crash | No crash occurred | Pass | Asma |
| TT36 | Progress page | Security | Log in as another user and view progress | Different user account | Only that user's data appears | Only correct user data shown | Pass | Asma |
| TT37 | History page | Manual | Open history page with logged workouts | User with activities | Activity history appears | History displayed | Pass | Asma |
| TT38 | History page | Manual | Filter history by sport | Sport: Running | Only running activities appear | Filter worked | Pass | Asma |
| TT39 | History page | Manual | Filter history by date range if available | Start/end date | Only matching activities appear | Matching activities displayed | Pass | Asma |
| TT40 | History page | Edge case | Open history page with no activities | New user | Empty state shown, no crash | Empty state shown | Pass | Asma |
| TT41 | History page | Security | Check another user's activities do not appear | Different user account | Only logged-in user's history appears | Only correct data shown | Pass | Asma |
| TT42 | History page | Validation | Invalid filter or missing query parameters | Invalid URL query | Page handles safely without crashing | No crash occurred | Pass | Asma |

---

## Testing Conclusion

Overall everything passed in the end but it definitely wasnt smooth the whole way through. The bugs took some time to hunt down, especially the calories showing as 0 and the progress page loading the wrong user — those two in particular took a bit of digging. Testing Jawaher's pages was actually really useful because I had no idea how she built any of it so I was just using it like a real user would, which meant I noticed things that felt off straight away. I think cross testing like this is way more effective than just checking your own work.