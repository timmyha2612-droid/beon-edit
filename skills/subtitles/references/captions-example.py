"""Hand-written clean-verbatim captions: WORK/captions.py for plan_captions.py.

CAPTIONS = {"<timeline name prefix>": [(index of the caption's first word in words.json, "text"), ...]}

- Indices come from show_words.py and must increase. The caption runs until the next one starts.
- "\n" is the line break (at most 2 lines, ~24-28 characters each).
- Write the clean text: ums, stutters, false starts and the other person's one-word reactions
  are left out by starting the next caption after them. Numbers as written ("$10 million").
- Real examples from the Beon SEO shorts (Oct 2026), approved style:
"""

CAPTIONS = {
"C2b": [
    (0, "If any agency\never says"),
    (5, "you don't need\nto worry"),
    (10, "about giving it\nthree months,"),
    (15, "because that's a cowboy\nmove right there."),
    (22, "That's a red flag."),
    (26, "If a client signs on\ntoday with us, right,"),
    (35, "how long would it be"),
    (40, "until they start\nseeing results?"),
    (45, "What we always recommend"),
    (49, "is to give us\nat least three months."),
    (58, "And the reason\nfor that is,"),
    (64, "Google obviously runs\nalgorithm updates"),
    (69, "over a certain\nperiod of time."),
    (75, "Give it some time."),
    (79, "Get the data in"),
    (83, "and let's see\nwhat happens."),
    (88, "Nothing good comes easy."),
],
"C3a": [
    (1, "Because you can rent\nlead generation, right,"),
    (8, "with ads and\npaid performance."),
    (14, "Yeah, and with SEO,"),
    (18, "you get to own\nthat channel."),
    (24, "From your perspective,"),
    (27, "what is the difference"),
    (31, "between paid\nand organic SEO?"),
    (35, "Overall, I see that both"),
    (40, "SEO and paid ads have\nthe right place to be."),
    (50, "They have a space to be\nin almost every business."),
    (60, "We see it as, again,\nrenting traffic"),
    (67, "versus owning\nthat channel"),
    (71, "of long-term\nlead generation."),
    (76, "What do you value,"),
    (80, "and can you afford\nto get there?"),
],
}
