# Codebook

Code the marked joke with three fields. Every example below is invented; none comes from any film.

## Target: whom or what the joke is about

Exactly one value. When a joke has several targets, give the first that applies in this order: group of people,
america, genre, character.

- `america`: the United States as a nation or its national identity, its institutions (government, courts, the
  military, schools and universities as institutions, the media, corporations), its competition culture (winning,
  rankings, trophies, sport and contest culture treated as national habit) and US college life as an institution
  (fraternities, sororities, campus rituals, college sport).
  - "We're Americans. If it isn't a competition, we'll make it one and then sue the judges."
  - "Freshman orientation: three hours on fire safety, five minutes on where the library is."
- `group`: a group of people defined by a shared trait, where the trait is what the joke is about. Give the group
  type: `gender`, `race`, `weight`, `sexuality`, `nationality`, `religion`, `disability`, or `other` with the group
  written down (age, class, occupation and any other group). Americans as a nation are `america`, not `group`. A joke
  at any other nationality or national origin is `group` with type `nationality`. A joke at a racial or ethnic group
  within the United States is `group` with type `race`.
  - gender: "Of course she can't read the map, she's been holding it like a handbag."
  - weight: "He sat on the bench and the bench filed a complaint."
  - nationality: "The Swiss team arrived exactly on time, which is how you know they're not from here."
  - religion: "Ask the vicar's daughter to judge the talent show, she only knows hymns and guilt."
  - disability: "He uses a wheelchair, so obviously he's the one we leave to guard the stairs."
- `character`: an individual character or a situation in the story, where no group trait and no national institution
  is what the joke is about: a character's habits, a mishap, an absurd turn of events, wordplay with no target.
  - "I've rehearsed this apology so much it now has a bridge and a key change."
  - "The van broke down, so naturally we're now lost on foot instead."
- `genre`: musicals, films, pop music or showbusiness and their conventions, including allusions to other works and
  performers when the joke is about them as entertainment.
  - "This is the part of the movie where we all learn something and the music swells."
  - "Nobody spontaneously bursts into harmony at a bus stop. Except, apparently, us."

## Butt: on whom the laugh falls

Exactly one value, for every joke. For a target that is not a group of people, `group` means the target itself (the
institution, the character, the genre).

- `speaker`: the laugh is on the person who speaks, or on the view they voice: their ignorance, prejudice, vanity or
  self-deprecation is what is funny. For a joke at a group, the stereotype is shown as the speaker's failing.
  - "As a man, I am naturally excellent at directions," said while walking into a lake.
  - "I'm not racist, I have a playlist."
- `group`: the laugh is on the target (for a joke at a group, the group itself, through the stereotype). For a joke
  at a group, the stereotype is offered as the truth that makes the joke work.
  - "Don't let the vegan cook, the soup will just be a lecture." (group, type other, vegans, with the laugh on them)
  - The weight example above, where the laugh is on the man on the bench.
- `unclear`: both readings are open from the text, or the delivery (tone, face, a cut) would decide and the
  subtitles do not show it. Use it when you cannot choose, not as a middle value.
