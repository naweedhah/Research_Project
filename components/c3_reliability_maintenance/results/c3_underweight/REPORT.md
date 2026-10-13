# C3 experiment results: underweight (stand-in C1 model, real linked data)

Seeds: 5. Shift runs: 150 (110 stress tests, 40 real area shifts). Strategy cycles: 750.
Harm = balanced-accuracy drop > 0.05, calibration error above limit, or sensitivity < 0.65. 

## Strategy comparison (all shifts)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |      150 |               0     |                                     0     |                    0     |                    0     |                      1     |                 0     |       0     |                        0.695 |             0     |                    0.095 |                            0.675 |                0     |
| periodic_retrain   |      150 |               1     |                                     1     |                    1     |                    0     |                      0     |                 0.627 |       3     |                        0.699 |             0.005 |                    0.094 |                            0.68  |                0.012 |
| always_recalibrate |      150 |               0.92  |                                     0.888 |                    0.967 |                    0     |                      0.033 |                 0.667 |       0.92  |                        0.698 |             0.004 |                    0.089 |                            0.685 |                0.01  |
| always_retrain     |      150 |               0.92  |                                     0.888 |                    0.967 |                    0     |                      0.033 |                 0.645 |       2.76  |                        0.699 |             0.005 |                    0.094 |                            0.68  |                0.01  |
| adaptive           |      150 |               0.433 |                                     0.393 |                    0.492 |                    0.377 |                      0.131 |                 0.615 |       1.017 |                        0.698 |             0.003 |                    0.091 |                            0.684 |                0     |

## Strategy comparison (stress tests only)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |      110 |               0     |                                     0     |                    0     |                    0     |                      1     |                 0     |       0     |                        0.71  |             0     |                    0.102 |                            0.736 |                0     |
| periodic_retrain   |      110 |               1     |                                     1     |                    1     |                    0     |                      0     |                 0.573 |       3     |                        0.716 |             0.005 |                    0.101 |                            0.739 |                0.016 |
| always_recalibrate |      110 |               0.891 |                                     0.846 |                    0.956 |                    0     |                      0.044 |                 0.602 |       0.891 |                        0.716 |             0.006 |                    0.094 |                            0.733 |                0.015 |
| always_retrain     |      110 |               0.891 |                                     0.846 |                    0.956 |                    0     |                      0.044 |                 0.592 |       2.673 |                        0.716 |             0.005 |                    0.101 |                            0.739 |                0.012 |
| adaptive           |      110 |               0.445 |                                     0.308 |                    0.644 |                    0.244 |                      0.111 |                 0.592 |       1.173 |                        0.715 |             0.004 |                    0.096 |                            0.737 |                0.002 |

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
| poorer_growth_population | WAZ tilt 0.5                       |      5 |             0   |       0.01  |     0.409 |             1   |
| poorer_growth_population | WAZ tilt 1.0                       |      5 |             0.8 |       0.036 |     1.109 |             1   |
| poorer_growth_population | WAZ tilt 1.5                       |      5 |             1   |       0.106 |     2.621 |             1   |
| prevalence               | prevalence 25%                     |      5 |             1   |      -0.003 |     0.215 |             1   |
| prevalence               | prevalence 40%                     |      5 |             1   |       0.007 |     0.277 |             1   |
| prevalence               | prevalence 5%                      |      5 |             0.2 |      -0.009 |     0.189 |             1   |
| scale_bias               | scale reads 0.25 kg low            |      5 |             0   |       0.011 |     0.125 |             1   |
| scale_bias               | scale reads 0.5 kg low             |      5 |             0   |       0.021 |     0.233 |             1   |
| scale_bias               | scale reads 1.0 kg low             |      5 |             0.8 |       0.06  |     0.678 |             1   |
| younger_population       | age tilt 0.5                       |      5 |             0.2 |       0.028 |     0.303 |             1   |
| younger_population       | age tilt 1.0                       |      5 |             0.2 |       0.027 |     0.952 |             1   |
| younger_population       | age tilt 1.5                       |      5 |             0.8 |       0.072 |     1.996 |             1   |

## Does drift predict harm? (idea 1)

| predictors                                            |   r2_balanced_accuracy_drop |
|:------------------------------------------------------|----------------------------:|
| max_psi                                               |                       0.159 |
| max_ks                                                |                       0.112 |
| max_missing_delta                                     |                       0.001 |
| prediction_psi                                        |                       0.041 |
| max_psi + max_ks + max_missing_delta + prediction_psi |                       0.168 |

| monitor           |   auroc_for_harm |   corr_with_drop |
|:------------------|-----------------:|-----------------:|
| max_psi           |            0.707 |            0.399 |
| max_ks            |            0.678 |            0.335 |
| max_missing_delta |            0.506 |           -0.026 |
| prediction_psi    |            0.655 |            0.203 |

Suggested monitor thresholds (maximise detection minus false alarms):

```
{
  "max_psi": {
    "threshold": 0.598,
    "detects_harm": 0.52,
    "false_alarm": 0.2
  },
  "max_ks": {
    "threshold": 0.274,
    "detects_harm": 0.39,
    "false_alarm": 0.08
  },
  "prediction_psi": {
    "threshold": 0.042,
    "detects_harm": 0.57,
    "false_alarm": 0.27
  },
  "current_rules_false_alarm_rate": 0.92
}
```
