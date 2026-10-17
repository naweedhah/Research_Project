# C3 experiment results: underweight (stand-in C1 model, real linked data)

Seeds: 5. Shift runs: 160 (120 stress tests, 40 real area shifts). Strategy cycles: 800.
Harm = balanced-accuracy drop > 0.05, calibration error above limit, or sensitivity < 0.65. Runtime 118s.

## Strategy comparison (all shifts)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |      160 |               0     |                                     0     |                    0     |                    0     |                      1     |                 0     |       0     |                        0.696 |             0     |                    0.095 |                            0.67  |                0     |
| periodic_retrain   |      160 |               0.969 |                                     0.958 |                    0.985 |                    0.015 |                      0     |                 0.71  |       2.922 |                        0.7   |             0.004 |                    0.094 |                            0.673 |                0.007 |
| always_recalibrate |      160 |               0.881 |                                     0.832 |                    0.954 |                    0.015 |                      0.031 |                 0.688 |       0.897 |                        0.705 |             0.009 |                    0.09  |                            0.69  |                0.007 |
| always_retrain     |      160 |               0.881 |                                     0.832 |                    0.954 |                    0.015 |                      0.031 |                 0.723 |       2.659 |                        0.7   |             0.004 |                    0.094 |                            0.673 |                0.006 |
| adaptive           |      160 |               0.412 |                                     0.368 |                    0.477 |                    0.369 |                      0.154 |                 0.682 |       0.981 |                        0.699 |             0.002 |                    0.095 |                            0.675 |                0.001 |

## Strategy comparison (stress tests only)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |      120 |               0     |                                     0     |                    0     |                    0     |                      1     |                 0     |       0     |                        0.712 |             0     |                    0.102 |                            0.723 |                0     |
| periodic_retrain   |      120 |               0.958 |                                     0.944 |                    0.98  |                    0.02  |                      0     |                 0.687 |       2.896 |                        0.716 |             0.004 |                    0.101 |                            0.724 |                0.008 |
| always_recalibrate |      120 |               0.842 |                                     0.775 |                    0.939 |                    0.02  |                      0.041 |                 0.634 |       0.862 |                        0.724 |             0.012 |                    0.095 |                            0.735 |                0.01  |
| always_retrain     |      120 |               0.842 |                                     0.775 |                    0.939 |                    0.02  |                      0.041 |                 0.703 |       2.546 |                        0.716 |             0.004 |                    0.101 |                            0.724 |                0.006 |
| adaptive           |      120 |               0.417 |                                     0.282 |                    0.612 |                    0.245 |                      0.143 |                 0.68  |       1.112 |                        0.715 |             0.003 |                    0.1   |                            0.721 |                0.002 |

## Strategy comparison (real unseen-PHM shifts only)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |       40 |                 0   |                                     0     |                    0     |                     0    |                      1     |                 0     |       0     |                        0.65  |             0     |                    0.074 |                            0.505 |                0     |
| periodic_retrain   |       40 |                 1   |                                     1     |                    1     |                     0    |                      0     |                 0.775 |       3     |                        0.653 |             0.004 |                    0.076 |                            0.515 |                0.004 |
| always_recalibrate |       40 |                 1   |                                     1     |                    1     |                     0    |                      0     |                 0.825 |       1     |                        0.649 |            -0.001 |                    0.076 |                            0.549 |               -0.002 |
| always_retrain     |       40 |                 1   |                                     1     |                    1     |                     0    |                      0     |                 0.775 |       3     |                        0.653 |             0.004 |                    0.076 |                            0.515 |                0.004 |
| adaptive           |       40 |                 0.4 |                                     0.625 |                    0.062 |                     0.75 |                      0.188 |                 0.688 |       0.588 |                        0.65  |             0     |                    0.077 |                            0.536 |               -0.005 |

## Shift types

| family                   | shift                              |   runs |   harmful_share |   mean_drop |   max_psi |   flagged_share |
|:-------------------------|:-----------------------------------|-------:|----------------:|------------:|----------:|----------------:|
| field_dropped            | WHZ not computed                   |      5 |             0   |       0.002 |     0.096 |             1   |
| field_dropped            | birth weight not collected         |      5 |             0.2 |      -0.011 |     0.092 |             1   |
| impossible_values        | 20% weights recorded 5x too high   |      5 |             0.2 |       0.033 |     0.291 |             1   |
| impossible_values        | 5% weights recorded 5x too high    |      5 |             0   |       0.019 |     0.112 |             0.6 |
| measurement_error        | height SD 1.0 cm, weight SD 0.3 kg |      5 |             0   |       0.017 |     0.093 |             0.2 |
| measurement_error        | height SD 2.0 cm, weight SD 0.6 kg |      5 |             0.2 |       0.026 |     0.113 |             0.4 |
| measurement_error        | height SD 4.0 cm, weight SD 1.2 kg |      5 |             0.8 |       0.073 |     0.257 |             1   |
| missing_weight           | 10% weights missing                |      5 |             0.2 |       0.014 |     0.099 |             0.6 |
| missing_weight           | 25% weights missing                |      5 |             0.2 |       0.033 |     0.106 |             1   |
| missing_weight           | 50% weights missing                |      5 |             0.6 |       0.073 |     0.144 |             1   |
| missing_weight           | 75% weights missing                |      5 |             0.8 |       0.105 |     0.43  |             1   |
| new_phm_area             | unseen area PHM01                  |      5 |             0   |      -0.076 |     0.667 |             1   |
| new_phm_area             | unseen area PHM02                  |      5 |             0.4 |       0.023 |     0.645 |             1   |
| new_phm_area             | unseen area PHM03                  |      5 |             1   |       0.253 |     2.078 |             1   |
| new_phm_area             | unseen area PHM04                  |      5 |             0   |      -0.026 |     1.517 |             1   |
| new_phm_area             | unseen area PHM05                  |      5 |             0.8 |       0.084 |     1.175 |             1   |
| new_phm_area             | unseen area PHM06                  |      5 |             0   |      -0.053 |     0.696 |             1   |
| new_phm_area             | unseen area PHM07                  |      5 |             1   |       0.143 |     0.493 |             1   |
| new_phm_area             | unseen area PHM10                  |      5 |             0   |       0.028 |     0.371 |             1   |
| none                     | no shift                           |      5 |             0   |       0     |     0.096 |             0.4 |
| poorer_growth_population | WAZ tilt 0.5                       |      5 |             0   |      -0.001 |     0.32  |             1   |
| poorer_growth_population | WAZ tilt 1.0                       |      5 |             1   |       0.035 |     1.333 |             1   |
| poorer_growth_population | WAZ tilt 1.5                       |      5 |             1   |       0.099 |     2.407 |             1   |
| prevalence               | prevalence 25%                     |      5 |             1   |       0.002 |     0.238 |             1   |
| prevalence               | prevalence 40%                     |      5 |             1   |      -0.001 |     0.294 |             1   |
| prevalence               | prevalence 5%                      |      5 |             0.2 |       0.011 |     0.186 |             1   |
| scale_bias               | scale reads 0.25 kg low            |      5 |             0   |       0.011 |     0.125 |             1   |
| scale_bias               | scale reads 0.5 kg low             |      5 |             0   |       0.021 |     0.233 |             1   |
| scale_bias               | scale reads 1.0 kg low             |      5 |             0.8 |       0.06  |     0.678 |             1   |
| younger_population       | age tilt 0.5                       |      5 |             0.2 |       0.028 |     0.356 |             1   |
| younger_population       | age tilt 1.0                       |      5 |             0.6 |       0.047 |     1.013 |             1   |
| younger_population       | age tilt 1.5                       |      5 |             0.8 |       0.078 |     2.02  |             1   |

## Does drift predict harm? (idea 1)

| predictors                                            |   r2_balanced_accuracy_drop |
|:------------------------------------------------------|----------------------------:|
| max_psi                                               |                       0.167 |
| max_ks                                                |                       0.122 |
| max_missing_delta                                     |                       0.001 |
| prediction_psi                                        |                       0.036 |
| max_psi + max_ks + max_missing_delta + prediction_psi |                       0.179 |

| monitor           |   auroc_for_harm |   corr_with_drop |
|:------------------|-----------------:|-----------------:|
| max_psi           |            0.75  |            0.409 |
| max_ks            |            0.722 |            0.349 |
| max_missing_delta |            0.522 |           -0.03  |
| prediction_psi    |            0.669 |            0.189 |

Suggested monitor thresholds (maximise detection minus false alarms):

```
{
  "max_psi": {
    "threshold": 0.429,
    "detects_harm": 0.58,
    "false_alarm": 0.2
  },
  "max_ks": {
    "threshold": 0.274,
    "detects_harm": 0.42,
    "false_alarm": 0.06
  },
  "prediction_psi": {
    "threshold": 0.049,
    "detects_harm": 0.52,
    "false_alarm": 0.22
  },
  "current_rules_false_alarm_rate": 0.9
}
```
