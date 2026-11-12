# Footage sort taxonomy

Tables for `resolve-footage-sort`. Claude uses these words in `looks.json` and the shot log. Scripts match exact tokens, so never invent a new word silently. Propose it at the gate. Adding it here is a general lesson: the editor approves it, then the plugin owner commits it or another editor opens a pull request (learn-from-tim).

## 1. Families by shoot kind (place sort)

Stored in `place.family`. Bins follow journey order: outside to in, arrival to leave, walk order.

| Shoot kind | Families in journey order (bin name) |
|---|---|
| Property | exterior (Exterior and Street), entry (Hallways Entry and Stairs), feature (Skylight and Void, Study, Garage), kitchen (Kitchen and Dining), living (Living), outdoor (Pool Backyard and Studio, Balcony and Terrace, Garden), bedrooms (Bedrooms), bathrooms (Bathrooms and Laundry), views (Views), details (Details and Joinery) |
| Suburb or area | landmark (one bin per named landmark), street (Main Street and Shops), dining (Cafes and Dining), park (Park), residential (Residential Streets), transport (Transport), details (Nature and Details) |
| Event or lunch | venue (Venue and Arrivals), stage (Speeches), guests (Guests and Mingling), setting (Tables and Setting), food (Food and Drink), branding (Branding and Signage), details (Details) |
| Office or teaser | exterior (Exterior and Lobby), reception (Reception and Branding), floor (Office Floor), meeting (Meeting Rooms), breakout (Kitchen and Breakout), team (Team Moments), details (Desks and Details) |
| Signboards | one flat bin per address (`12 Example St`). Board, context and agent are subject tags, not sub-bins |
| Interview | one bin per person (A and B cams together, cam in the shot log). The multicam clip stays where the editor made it (`shoot.multicam.clip`). B-roll by the families above |
| Aerial | aerial (Aerials) |

Mixed shoots use families from more than one row, in journey order. Granularity on area shoots: fine (one bin per named landmark) by default. Show the coarse version (landmarks folded into one street bin) at the gate when it exists. The shot log keeps fine place ids either way.

## 2. Subject and concept sorts

- **Subject sort:** one bin per thing the subject does, in shoot order. Examples: `01 Arrival`, `02 Walking the Site`, `03 Talking to Camera`, `04 Hands and Tools`. When the subject does one thing all day, bin by setup instead (`02 Window Light Setup`).
- **Concept sort:** one bin per motif. Examples: `01 Doors and Handles`, `02 Light Through Glass`, `03 Textures`, `04 Hands`. Motifs come from what the frames show, not from the brief.
- Both still get Details (when it is not the concept itself), A-roll and Audio when present.
- Place, subject and concept are always filled in the shot log, whatever the axis.

## 3. Vocabularies (closed lists)

- **subject:** landmark, facade, interior_room, street_life, shopfront, signage, nature, texture, people, food, vehicle, animal, sky, detail.
- **concept:** free short kebab-case motif (`light-through-glass`), reused across the shoot. A new motif is listed at the gate.
- **shot_size:** wide, medium, close, detail. Start from focal and framing, confirm by eye.
- **angle:** eye, low, high, overhead.
- **light:** sun, overcast, shade, golden, night, interior, mixed.
- **roles** (1 to 3, first is primary): aroll, establishing, place, people, detail, transition, junk. This is the content list Claude writes. The manifest's rule role (aroll, multicam_angle, audio, broll, junk_candidate) goes in its own key, `sort_role`.
- **vertical:** ok, pan (needs a Pan to subject_x), hard.
- **subject_x:** 0 to 1 across the 16:9 frame. 9:16 Pan = (0.5 - x) * 1080.
- **confidence:** high, med, low. Low always gets a second look.
- **people_detail:** `{count, role, faces, names, minors_visible}`. role: subject, passer-by, crowd. faces: recognisable, back, none. names only from the people registry (`shoot.people`) or the editor. Never write it as `people`: that key is the shot log's existing people list.

## 4. good_for grammar (exact tokens)

- `names_place:<place-id>`: the clip clearly shows a place a line could name.
- `match:<thing>`: literal things (fountain, tram, tree, letterbox).
- `topic:<word>`: from the client profile topic list only (lifestyle, community, heritage, greenery, transport, cafe, families, pets, architecture, property, team, food). A new word is proposed at the gate.
- Edit roles: `opener`, `closer`, `breathing_gap`, `transition_in`, `transition_out`, `cover_jump_cut`, `cutaway`, `text_space`.

## 5. not_for (content reasons only)

`political_signage`, `third_party_brand:<name>`, `recognisable_stranger`, `minors`, `implies_specific_property`, `person_unconfirmed`, `subject_edge_916`, plus short free text.

- `recognisable_stranger` and `minors` come from `people_detail`, never set by hand.
- Technical reasons (shaky, reject, clipping, no select) are never stored here. Scripts read them live from Footage Prep.

## 6. Not stored (computed live at use time)

`broll_ready`, `hero_moment`, best select. hero_moment = FP tier hero AND a clean select with stability 0.9 or more AND a strong role or tag (opener, breathing_gap, closer). The sort only stores the content half.

## 7. Ids

- Place ids: kebab-case (`corner-park`).
- Scene ids: `<place-id>-<n>`, a new n each time the place comes back in a later session or light.
- Setup ids: `<scene-id>-s<nn>`.
- Take family ids (one shot filmed more than once, partial takes included): `<scene-id>-shot<nn>`. Per clip `take: {n, of, cover: full|start|middle|end|false_start, best}`, one `best` per family. A setup can hold several shots, and a shot's takes can sit in different setups (the fingerprint splits reframed takes).
- `sort.editor_changes` entries: `{field: place|scene|roles|good_for|bin, from, to, date, editor}` (`editor` = editor.json `name`). Older logs call the list `sort.tim` (no `editor`): read both, write `editor_changes`. learn-from-tim counts these per field and per client.
