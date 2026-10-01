# Data

Data is **not** committed to this repository. Nutrition Month / PHM records contain
child-level health information and must stay on local machines or approved storage.

Suggested local layout (all git-ignored):

```
data/
├── raw/         # digitized records as received, never edited
├── processed/   # cleaned datasets used for modelling
└── splits/      # frozen reference / adapt / verify splits shared between C1 and C3
```
