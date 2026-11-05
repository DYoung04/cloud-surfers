# Course Final Projects
## CSC 4913 / CSC 5573: Model Selection and Validation (Fall 2026)
### Louisiana Tech University — Computer Science

Welcome to the Course Final Project repository. This repository contains the complete dataset packages, data dictionaries, and problem statements for all five course projects.

---

## 1. Project Directory & Topic Overview

| Topic # | Domain | Project Name | Folder Link |
|:---:|:---|:---|:---|
| **Topic 1** | Healthcare | **The "Best" Hospital Paradox** | [`Topic1_Healthcare_The_Best_Hospital_Paradox/`](./Topic1_Healthcare_The_Best_Hospital_Paradox/) |
| **Topic 2** | Retail & Supply Chain | **The Empty Shelves Paradox** | [`Topic2_Supply_Chain_The_Empty_Shelves_Paradox/`](./Topic2_Supply_Chain_The_Empty_Shelves_Paradox/) |
| **Topic 3** | Energy & Climate | **The "Green" Tech Carbon Spike** | [`Topic3_Climate_Energy_The_Green_Tech_Carbon_Spike/`](./Topic3_Climate_Energy_The_Green_Tech_Carbon_Spike/) |
| **Topic 4** | Sports Analytics | **The "Unbeatable" Underdog** | [`Topic4_Sports_Analytics_The_Unbeatable_Underdog/`](./Topic4_Sports_Analytics_The_Unbeatable_Underdog/) |
| **Topic 5** | Education | **The Tutoring Paradox** | [`Topic5_Education_The_Tutoring_Paradox/`](./Topic5_Education_The_Tutoring_Paradox/) |

---

## 2. Topic Summaries

### Topic 1. Healthcare: The "Best" Hospital Paradox
* **Domain**: Clinical Healthcare Informatics & Patient Acuity
* **The Core Question**: Top research hospitals report higher raw mortality rates than small community clinics. Does an insurance algorithm correctly conclude that funding should be cut, or is this an artifact of patient illness severity, age, and inter-hospital transfer selection bias?
* **Contents**: [`PROJECT.md`](./Topic1_Healthcare_The_Best_Hospital_Paradox/PROJECT.md), [`data/DATA_DICTIONARY.md`](./Topic1_Healthcare_The_Best_Hospital_Paradox/data/DATA_DICTIONARY.md), admissions, transfers, hospitals, diagnoses.

### Topic 2. Supply Chain: The Empty Shelves Paradox
* **Domain**: Grocery Point-of-Sale & Distribution Logistics
* **The Core Question**: Big discount promotion weeks generate record foot traffic but paradoxically collapse profit margins and leave non-sale essentials out of stock. Is promotion strategy flawed, or is inventory delivery cadence and truck capacity the true operational bottleneck?
* **Contents**: [`PROJECT.md`](./Topic2_Supply_Chain_The_Empty_Shelves_Paradox/PROJECT.md), [`data/DATA_DICTIONARY.md`](./Topic2_Supply_Chain_The_Empty_Shelves_Paradox/data/DATA_DICTIONARY.md), sales, inventory, orders, prices, products, stores.

### Topic 3. Climate & Energy: The "Green" Tech Carbon Spike
* **Domain**: Municipal Electric Grid & Decarbonization Policy
* **The Core Question**: A city mandates 10,000 electric vehicles to reduce carbon emissions, yet city-wide emissions rise during the program year. What role do marginal power plant dispatch order, overnight home charging spikes, and seasonal temperature swings play in the emissions balance?
* **Contents**: [`PROJECT.md`](./Topic3_Climate_Energy_The_Green_Tech_Carbon_Spike/PROJECT.md), [`data/DATA_DICTIONARY.md`](./Topic3_Climate_Energy_The_Green_Tech_Carbon_Spike/data/DATA_DICTIONARY.md), charging sessions, grid hourly dispatch, weather, fleet monthly stats, vehicles, stations.

### Topic 4. Sports Analytics: The "Unbeatable" Underdog
* **Domain**: NCAA College Basketball Performance Modeling
* **The Core Question**: An algorithm predicts that a historically weak underdog team with an 85% regular season record will easily win the national championship over powerhouse teams. How do home-court bias, non-conference scheduling, and conference opponent strength explain the win rate?
* **Contents**: [`PROJECT.md`](./Topic4_Sports_Analytics_The_Unbeatable_Underdog/PROJECT.md), [`data/DATA_DICTIONARY.md`](./Topic4_Sports_Analytics_The_Unbeatable_Underdog/data/DATA_DICTIONARY.md), box scores, regular season results, tournament results, preseason ratings, teams, conferences.

### Topic 5. Education: The Tutoring Paradox
* **Domain**: K-12 Educational Interventions & Academic Outcomes
* **The Core Question**: Students who attend free after-school tutoring show higher course failure rates than non-attendees. Is the tutoring ineffective, or are referrals targeted at struggling students, combined with transportation and socioeconomic factors, masking the program's true value?
* **Contents**: [`PROJECT.md`](./Topic5_Education_The_Tutoring_Paradox/PROJECT.md), [`data/DATA_DICTIONARY.md`](./Topic5_Education_The_Tutoring_Paradox/data/DATA_DICTIONARY.md), term grades, tutoring sessions, referrals, student demographics, courses, tutors, schools.

---

## 3. Repository Structure

Each project folder follows a standardized layout:
```text
Topic<N>_<Project_Name>/
├── PROJECT.md               # Detailed problem background, motivation, and domain expert inputs
└── data/
    ├── DATA_DICTIONARY.md   # Complete schema and column documentation
    ├── *.csv / *.csv.gz     # Primary datasets for analysis and modeling
    └── *_sample.csv         # Small 20-row sample files for quick inspection
```

---

## 4. How to Use & Getting Started

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/CSC491-557/final-project.git
   cd final-project
   ```

2. **Navigate to Your Assigned Topic**:
   Check your team's assigned topic in `STUDENT_VM_ROSTER.md` or Canvas, then navigate into that folder.

3. **Working on the Lab Cluster VMs**:
   * All datasets are also pre-staged in your VM's shared folder: `/home/groups/` and `/home/Fall2026 Share folder/`.
   * Teammates on the same system share a common project workspace.
   * Log your model runs and metrics to the hosted MLflow server at `http://10.0.100.20:5000` using your assigned student credentials.

---

## 5. Course Project Milestones Schedule

* **Milestone 1 (M1) — Frame**: Problem formulation, causal DAG formulation, and hypothesis definition.
* **Milestone 2 (M2) — Explore & Focus**: Exploratory data analysis, data cleaning, sanity checks, and initial patterns.
* **Milestone 3 (M3) — Select & Train**: Feature engineering, baseline model selection, MLflow experiment tracking.
* **Milestone 4 (M4) — Evaluate & Validate**: Cross-validation, paradox resolution, bias-variance tradeoff, test set evaluation.
* **Milestone 5 (M5) — Deliver**: Final model packaging, reproducible pipeline, and team presentation.

