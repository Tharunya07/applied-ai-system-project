# Medical Task Guidelines

## Why Medication Tasks Should Never Be Skipped

Medication tasks represent the highest-priority category in any pet care schedule. Skipping or delaying medications carries serious, sometimes life-threatening consequences:

1. **Therapeutic window violations:** Many medications (e.g., insulin for diabetic pets, anti-seizure drugs) require consistent plasma concentration to be effective. Missed doses can drop levels below the therapeutic threshold, triggering medical emergencies such as diabetic ketoacidosis or breakthrough seizures.

2. **Resistance development:** Antibiotic and antiparasitic medications that are taken inconsistently can promote drug-resistant strains of bacteria or parasites, making future infections harder or impossible to treat with standard drugs.

3. **Rebound effects:** Abrupt discontinuation of corticosteroids, cardiac medications, or thyroid treatments can cause dangerous rebound reactions including adrenal crisis, arrhythmia, or thyroid storm.

4. **Disease progression:** Chronic disease management medications (e.g., for arthritis, kidney disease, hyperthyroidism) slow disease progression only when given consistently. Even occasional skips over weeks can meaningfully accelerate decline.

5. **Preventive medications:** Heartworm preventatives, flea/tick treatments, and deworming medications have strict schedule dependencies. Missing a single heartworm dose by more than a few days may require the pet to be retested and restarted, and a missed dose during active exposure can result in infection.

**Rule: In the PawPal+ system, any task tagged as `medication` or `medical` must be given `HIGH` priority and should never be removed from the daily plan regardless of time budget constraints. If a time conflict exists, reduce or remove LOW-priority tasks first.**

---

## Recommended Frequency for Common Pet Medications

| Medication Type                  | Species       | Recommended Frequency                  |
|----------------------------------|---------------|----------------------------------------|
| Insulin (diabetes management)    | Dog, Cat      | Twice daily (every 12 hours), with meals |
| Thyroid medication (methimazole) | Cat           | Twice daily (every 12 hours)           |
| Anti-seizure medication          | Dog, Cat      | As prescribed — often twice daily; never miss |
| Heartworm preventative           | Dog, Cat      | Once monthly (specific calendar date)  |
| Flea/tick preventative (topical) | Dog, Cat      | Once monthly or as product label specifies |
| Flea/tick preventative (oral)    | Dog           | Once monthly or once every 3 months    |
| Dewormer (routine)               | Dog, Cat      | Every 3 months (adults); monthly for puppies/kittens |
| Joint supplement (glucosamine)   | Dog, Cat      | Daily (once daily with food)           |
| Antibiotics (short course)       | Dog, Cat      | As prescribed — typically 1–2x daily for 7–14 days |
| Allergy medication (oclacitinib) | Dog           | Twice daily for 14 days, then once daily |
| Ear medication (post-infection)  | Dog, Cat      | Once or twice daily for prescribed duration |
| Eye drops (glaucoma/infection)   | Dog, Cat      | 1–3 times daily as prescribed          |
| Cardiac medication (atenolol)    | Dog, Cat      | Once or twice daily (do not skip)      |
| Kidney support diet supplement   | Dog, Cat      | Daily with meals                       |

**Notes:**
- "Twice daily" always means every 12 hours, not just morning and evening at convenience — spacing matters for pharmacokinetics.
- Never split a single dose to make up for a missed dose without consulting a veterinarian.
- Store medications per label instructions (some require refrigeration).

---

## Warning Signs That a Medical Task Is Being Under-Scheduled

The following flags in a task schedule should trigger a warning in the PawPal+ system:

1. **Medication task frequency is lower than the minimum recommended frequency** — e.g., a "daily insulin" task is scheduled only every other day.

2. **Medication task is marked as LOW priority** — all medication tasks should be HIGH priority regardless of user input; the system should override or warn.

3. **Medication task appears in the task list but not in the generated plan** — if the scheduler skipped a medical task due to time budget constraints, this must be flagged as a critical warning, not a routine skipped task.

4. **No medication task exists for a pet whose profile or task history implies chronic disease** — e.g., a senior pet (8+ years) with no medication tasks may be fine, but the absence should be noted for the owner's awareness.

5. **A medication task has not been marked complete in 2+ consecutive scheduled occurrences** — this suggests the task is being systematically ignored and warrants a high-visibility alert.

6. **The medication task duration is set to 0 minutes** — this is likely a data entry error; medications require real time to administer safely.

---

## Vet Visit Frequency Guidelines by Pet Age

| Species | Life Stage          | Age Range       | Recommended Vet Visit Frequency              |
|---------|---------------------|-----------------|----------------------------------------------|
| Dog     | Puppy               | 0–6 months      | Every 3–4 weeks for vaccination series; 1 visit at 8, 12, and 16 weeks minimum |
| Dog     | Adolescent/Young Adult | 6 mo–2 yr    | Every 6 months (spay/neuter check, booster vaccines) |
| Dog     | Adult               | 2–7 years       | Annually (wellness exam, vaccines, heartworm test) |
| Dog     | Senior              | 7–10 years      | Every 6 months (bloodwork, urinalysis, blood pressure) |
| Dog     | Geriatric           | 10+ years       | Every 3–6 months depending on health status  |
| Cat     | Kitten              | 0–6 months      | Every 3–4 weeks for vaccination series       |
| Cat     | Young Adult         | 6 mo–3 yr       | Annually                                     |
| Cat     | Adult               | 3–10 years      | Annually (many cats go undiagnosed for years due to infrequent visits) |
| Cat     | Senior              | 10–15 years     | Every 6 months (thyroid panel, kidney values) |
| Cat     | Geriatric           | 15+ years       | Every 3–4 months                             |
| Rabbit  | Adult               | 1–5 years       | Annually (dental check is critical for rabbits) |
| Rabbit  | Senior              | 5+ years        | Every 6 months                               |
| Bird    | Adult (Parakeet)    | 1–5 years       | Annually                                     |
| Bird    | Senior (Parrot)     | Varies by species| Every 6 months for large parrots 15+ years  |

**Key notes:**
- New pets of any age should have a baseline wellness exam within the first 1–2 weeks of adoption.
- Any acute illness, behavior change, or weight change of more than 10% should prompt an unscheduled vet visit regardless of when the last appointment was.
- Dental disease is the most commonly under-treated condition across all species; ask about professional dental cleaning at every annual visit.
- Establish care with a vet before an emergency arises — emergency-only relationships make triage harder for the veterinarian.
