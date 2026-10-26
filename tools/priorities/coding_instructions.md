# Coding instructions: CAP major topic of a Czech parliamentary speech

You read speeches from the Czech Chamber of Deputies (Poslanecká sněmovna), one per line of a JSONL file (`key`, `words`,
`cut`, `text`; `cut` = the text was cut at 1 500 words). For each speech, choose the **one** Comparative Agendas Project
(CAP) major topic that the speech is mainly about, following the CAP master codebook. Code from the text alone; there is
no other information, and do not look anything up.

## Major topics (CAP master codebook)

1. **Macroeconomics** — the economy as a whole: budget and deficit, taxation and tax policy, inflation, interest rates,
   monetary policy, economic growth, public debt.
2. **Civil Rights** — civil liberties, discrimination, minority rights, gender and LGBT rights, privacy, freedom of
   speech, voting rights.
3. **Health** — health care system, insurance, hospitals, drugs, public health, disease prevention.
4. **Agriculture** — farming, food production and safety, fisheries, agricultural subsidies.
5. **Labor** — employment and unemployment, labour law, wages and minimum wage, working conditions, unions, workplace
   safety, employment services.
6. **Education** — schools, universities, teachers, vocational training, research and education funding.
7. **Environment** — pollution, climate change, conservation, waste, water quality, environmental protection.
8. **Energy** — energy supply and prices, electricity, nuclear, gas, oil, renewables, energy security.
9. **Immigration** — immigration, refugees and asylum, citizenship and naturalisation, foreigners' residence.
10. **Transportation** — roads, rail, public transport, aviation, transport infrastructure and safety.
12. **Law and Crime** — crime, police, courts and criminal justice, prisons, corruption as crime, family law.
13. **Social Welfare** — social security, pensions, poverty, social services, family and child benefits, disability.
14. **Housing** — housing policy, rents, mortgages, construction of housing, urban and regional development.
15. **Domestic Commerce** — business regulation, banking and finance, consumer protection, small business, insurance
   industry, tourism, sports regulation.
16. **Defense** — military, armed forces, defence spending, NATO, military procurement, civil defence.
17. **Technology** — science and technology, telecommunications, internet, digital policy, space.
18. **Foreign Trade** — trade agreements, tariffs, exports and imports, foreign investment.
19. **International Affairs** — foreign policy, EU affairs and institutions, international organisations, diplomacy,
   development aid, conflicts abroad.
20. **Government Operations** — government and parliament organisation, public administration, civil service,
   elections, procedure of the Chamber, constitutional matters, public procurement, state property.
21. **Public Lands** — public lands and natural resources management, forests, water management, national parks.
23. **Culture** — arts, culture, media and broadcasting policy, heritage, churches.

Use **Other** only if the speech has no policy topic at all (greetings, pure procedure such as "I ask for the floor",
personal remarks, objections about speaking time without a subject).

## Rules

- One topic per speech: the main subject. If several are discussed, choose the one that takes most of the speech or
  that the speaker's proposal is about.
- A speech about the procedure of a bill is coded by the bill's subject if the subject is clear; pure procedure is
  Government Operations if it is about how the Chamber or government works, Other if it has no content.
- Do not guess from the speaker's party or name.

## Output

Write a JSON file: a list of objects `{"key": ..., "topic": "<exact topic name above, or Other>", "confidence":
"high" | "medium" | "low"}`, one per input line, in input order, nothing else.
