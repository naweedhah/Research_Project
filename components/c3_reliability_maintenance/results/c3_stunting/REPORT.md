# C3 experiment results: stunting (stand-in C1 model, real linked data)

Seeds: 5. Shift runs: 160 (120 stress tests, 40 real area shifts). Strategy cycles: 800.
Harm = balanced-accuracy drop > 0.05, calibration error above limit, or sensitivity < 0.65. Runtime 198s.

## Strategy comparison (all shifts)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |      160 |               0     |                                     0     |                    0     |                    0     |                      1     |                 0     |       0     |                        0.656 |             0     |                    0.103 |                            0.655 |                0     |
| periodic_retrain   |      160 |               0.975 |                                     0.971 |                    0.982 |                    0.018 |                      0     |                 0.622 |       2.938 |                        0.668 |             0.012 |                    0.105 |                            0.705 |                0.009 |
| always_recalibrate |      160 |               0.862 |                                     0.835 |                    0.912 |                    0.018 |                      0.07  |                 0.63  |       0.875 |                        0.663 |             0.007 |                    0.111 |                            0.684 |                0.007 |
| always_retrain     |      160 |               0.862 |                                     0.835 |                    0.912 |                    0.018 |                      0.07  |                 0.659 |       2.6   |                        0.666 |             0.01  |                    0.104 |                            0.694 |                0.008 |
| adaptive           |      160 |               0.338 |                                     0.184 |                    0.614 |                    0.228 |                      0.158 |                 0.704 |       0.8   |                        0.657 |             0.002 |                    0.104 |                            0.669 |                0.003 |

## Strategy comparison (stress tests only)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |      120 |               0     |                                     0     |                    0     |                    0     |                      1     |                 0     |       0     |                        0.677 |             0     |                    0.112 |                            0.717 |                0     |
| periodic_retrain   |      120 |               0.967 |                                     0.96  |                    0.978 |                    0.022 |                      0     |                 0.603 |       2.917 |                        0.68  |             0.003 |                    0.115 |                            0.751 |                0.004 |
| always_recalibrate |      120 |               0.817 |                                     0.773 |                    0.889 |                    0.022 |                      0.089 |                 0.622 |       0.833 |                        0.68  |             0.003 |                    0.121 |                            0.731 |                0.002 |
| always_retrain     |      120 |               0.817 |                                     0.773 |                    0.889 |                    0.022 |                      0.089 |                 0.653 |       2.467 |                        0.678 |             0.001 |                    0.114 |                            0.738 |                0.004 |
| adaptive           |      120 |               0.383 |                                     0.147 |                    0.778 |                    0.156 |                      0.067 |                 0.717 |       0.954 |                        0.679 |             0.002 |                    0.113 |                            0.735 |                0.001 |

## Strategy comparison (real unseen-PHM shifts only)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |       40 |                 0   |                                     0     |                        0 |                      0   |                        1   |                 0     |       0     |                        0.577 |             0     |                    0.069 |                            0.422 |                0     |
| periodic_retrain   |       40 |                 1   |                                     1     |                        1 |                      0   |                        0   |                 0.675 |       3     |                        0.622 |             0.045 |                    0.068 |                            0.529 |                0.02  |
| always_recalibrate |       40 |                 1   |                                     1     |                        1 |                      0   |                        0   |                 0.65  |       1     |                        0.6   |             0.023 |                    0.073 |                            0.505 |                0.019 |
| always_retrain     |       40 |                 1   |                                     1     |                        1 |                      0   |                        0   |                 0.675 |       3     |                        0.622 |             0.045 |                    0.068 |                            0.529 |                0.02  |
| adaptive           |       40 |                 0.2 |                                     0.286 |                        0 |                      0.5 |                        0.5 |                 0.625 |       0.338 |                        0.577 |             0     |                    0.069 |                            0.422 |                0.006 |

## Shift types

| family                   | shift                              |   runs |   harmful_share |   mean_drop |   max_psi |   flagged_share |
|:-------------------------|:-----------------------------------|-------:|----------------:|------------:|----------:|----------------:|
| field_dropped            | WHZ not computed                   |      5 |             0.2 |      -0.004 |     0.117 |             1   |
| field_dropped            | birth weight not collected         |      5 |             0.2 |       0.002 |     0.117 |             1   |
| impossible_values        | 20% weights recorded 5x too high   |      5 |             0.2 |       0.016 |     0.299 |             1   |
| impossible_values        | 5% weights recorded 5x too high    |      5 |             0.2 |       0     |     0.126 |             0.4 |
| measurement_error        | height SD 1.0 cm, weight SD 0.3 kg |      5 |             0.2 |      -0.001 |     0.117 |             0.4 |
| measurement_error        | height SD 2.0 cm, weight SD 0.6 kg |      5 |             0.2 |       0.015 |     0.12  |             0.4 |
| measurement_error        | height SD 4.0 cm, weight SD 1.2 kg |      5 |             0.6 |       0.052 |     0.232 |             1   |
| missing_weight           | 10% weights missing                |      5 |             0.2 |      -0.001 |     0.122 |             0.6 |
| missing_weight           | 25% weights missing                |      5 |             0.2 |      -0.002 |     0.14  |             1   |
| missing_weight           | 50% weights missing                |      5 |             0.2 |      -0.001 |     0.156 |             1   |
| missing_weight           | 75% weights missing                |      5 |             0.2 |      -0     |     0.245 |             1   |
| new_phm_area             | unseen area PHM01                  |      5 |             0.2 |      -0.019 |     0.707 |             1   |
| new_phm_area             | unseen area PHM02                  |      5 |             0   |      -0.012 |     0.856 |             1   |
| new_phm_area             | unseen area PHM03                  |      5 |             1   |       0.196 |     2.157 |             1   |
| new_phm_area             | unseen area PHM04                  |      5 |             0.2 |      -0.003 |     1.591 |             1   |
| new_phm_area             | unseen area PHM05                  |      5 |             0   |      -0.042 |     0.853 |             1   |
| new_phm_area             | unseen area PHM06                  |      5 |             0   |      -0.02  |     0.787 |             1   |
| new_phm_area             | unseen area PHM07                  |      5 |             0.8 |       0.15  |     0.635 |             1   |
| new_phm_area             | unseen area PHM10                  |      5 |             0.2 |      -0.002 |     0.453 |             1   |
| none                     | no shift                           |      5 |             0.2 |       0     |     0.117 |             0.2 |
| poorer_growth_population | WAZ tilt 0.5                       |      5 |             0   |       0.011 |     0.311 |             1   |
| poorer_growth_population | WAZ tilt 1.0                       |      5 |             0.8 |       0.036 |     1.15  |             1   |
| poorer_growth_population | WAZ tilt 1.5                       |      5 |             1   |       0.081 |     2.592 |             1   |
| prevalence               | prevalence 25%                     |      5 |             1   |       0.001 |     0.205 |             1   |
| prevalence               | prevalence 40%                     |      5 |             1   |      -0.007 |     0.324 |             1   |
| prevalence               | prevalence 5%                      |      5 |             0   |      -0.001 |     0.184 |             0.8 |
| scale_bias               | scale reads 0.25 kg low            |      5 |             0   |      -0.004 |     0.132 |             0.6 |
| scale_bias               | scale reads 0.5 kg low             |      5 |             0   |       0.002 |     0.199 |             1   |
| scale_bias               | scale reads 1.0 kg low             |      5 |             0   |       0.015 |     0.571 |             1   |
| younger_population       | age tilt 0.5                       |      5 |             0.4 |       0.037 |     0.312 |             1   |
| younger_population       | age tilt 1.0                       |      5 |             1   |       0.061 |     1.102 |             1   |
| younger_population       | age tilt 1.5                       |      5 |             1   |       0.096 |     2.283 |             1   |

## Does drift predict harm? (idea 1)

| predictors                                            |   r2_balanced_accuracy_drop |
|:------------------------------------------------------|----------------------------:|
| max_psi                                               |                       0.232 |
| max_ks                                                |                       0.17  |
| max_missing_delta                                     |                       0.02  |
| prediction_psi                                        |                       0.034 |
| max_psi + max_ks + max_missing_delta + prediction_psi |                       0.245 |

| monitor           |   auroc_for_harm |   corr_with_drop |
|:------------------|-----------------:|-----------------:|
| max_psi           |            0.735 |            0.481 |
| max_ks            |            0.709 |            0.413 |
| max_missing_delta |            0.504 |           -0.142 |
| prediction_psi    |            0.677 |            0.184 |

Suggested monitor thresholds (maximise detection minus false alarms):

```
{
  "max_psi": {
    "threshold": 0.177,
    "detects_harm": 1.0,
    "false_alarm": 0.63
  },
  "max_ks": {
    "threshold": 0.319,
    "detects_harm": 0.45,
    "false_alarm": 0.06
  },
  "prediction_psi": {
    "threshold": 0.051,
    "detects_harm": 0.41,
    "false_alarm": 0.06
  },
  "current_rules_false_alarm_rate": 0.89
}
```
