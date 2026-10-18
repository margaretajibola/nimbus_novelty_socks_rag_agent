# Test Questions and Answer Key

Use these to check your RAG agent. Keep this file outside the `docs` folder so it does not get indexed.

## Single document

| # | Question | Expected answer | Source |
| --- | --- | --- | --- |
| 1 | What are the core hours? | 10:00 to 15:00 Eastern Time | 01 handbook |
| 2 | Which days do Halifax employees work from the office? | Tuesdays and Thursdays | 01 handbook |
| 3 | How much is the learning budget per year? | $1,200 CAD, does not roll over | 01 handbook |
| 4 | What is the referral bonus and when is it paid? | $1,500 CAD, after the hire stays 6 months | 01 handbook |
| 5 | How many sick days do I get and when do I need a note? | 8 per year, note needed for 4 or more consecutive days | 02 PTO |
| 6 | How long is parental leave top-up for a non-birth parent? | 8 weeks at 80 percent of salary | 02 PTO |
| 7 | What is the hotel limit per night? | $220 CAD | 03 expenses |
| 8 | Is alcohol reimbursed? | No | 03 expenses |
| 9 | How soon must I report a lost laptop? | Within 1 hour | 04 IT security |
| 10 | What is the minimum password length? | 14 characters | 04 IT security |
| 11 | When can I bring my dog to the office? | Wednesdays only, after registering with the office manager | 05 FAQ |
| 12 | When is payday? | Every second Friday, the business day before if it is a holiday | 05 FAQ |

## Needs more than one document

| # | Question | Expected answer | Sources |
| --- | --- | --- | --- |
| 13 | I have worked here 4 years. How many PTO days do I get and how many can I carry over? | 25 days per year, up to 5 carried over, must be used by March 31 | 02 PTO |
| 14 | I am travelling to Toronto for a client. What can I spend on hotel and food per day? | Hotel up to $220 per night, meals up to $75 per day, and client entertainment up to $100 per person with director approval | 03 expenses |
| 15 | How do I claim my learning budget and who approves it? | Submit in Receipto within 30 days, category "Learning budget", manager approval needed first if over $500 | 01 handbook, 03 expenses |
| 16 | I want to work from abroad for 3 weeks. Is that allowed? | No, the limit is 2 weeks outside Canada per year, with manager approval and 30 days' notice to HR | 01 handbook |
| 17 | A customer emailed me their credit card number. What do I do? | Do not copy it, delete the message, tell the customer to use checkout. Nimbus never stores card numbers and uses Stripe | 04 IT security |
| 18 | When does my salary change after a promotion? | Promotions are decided at June and December reviews and take effect at the start of the next quarter | 01 handbook, 05 FAQ |

## Should say "I don't know"

The documents do not cover these. A good agent says the information is not in the documents instead of guessing.

| # | Question |
| --- | --- |
| 19 | Do employees get stock options? |
| 20 | What is the company's policy on pets other than dogs? |
| 21 | How much does the CEO earn? |
| 22 | What is the dental plan coverage? |

## Tricky cases

| # | Question | What to look for |
| --- | --- | --- |
| 23 | Do winter break days use up my PTO? | No, Dec 24 to Jan 1 does not count against PTO |
| 24 | Can I carry over 10 days? | No, the maximum is 5, and they expire March 31 |
| 25 | I submitted an expense 6 weeks ago. Will it be paid? | It may be declined, since claims are due within 30 days |
