# C3 experiment results: wasting (stand-in C1 model, real linked data)

Seeds: 5. Shift runs: 160 (120 stress tests, 40 real area shifts). Strategy cycles: 800.
Harm = balanced-accuracy drop > 0.05, calibration error above limit, or sensitivity < 0.65. Runtime 164s.

## Strategy comparison (all shifts)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |      160 |               0     |                                     0     |                    0     |                    0     |                      1     |                 0     |       0     |                        0.579 |             0     |                    0.089 |                            0.686 |                0     |
| periodic_retrain   |      160 |               0.969 |                                     0.96  |                    0.983 |                    0.017 |                      0     |                 0.665 |       2.922 |                        0.592 |             0.013 |                    0.09  |                            0.732 |                0.001 |
| always_recalibrate |      160 |               0.831 |                                     0.752 |                    0.966 |                    0.017 |                      0.017 |                 0.789 |       0.847 |                        0.578 |            -0.001 |                    0.088 |                            0.692 |                0.008 |
| always_retrain     |      160 |               0.831 |                                     0.752 |                    0.966 |                    0.017 |                      0.017 |                 0.684 |       2.509 |                        0.592 |             0.013 |                    0.09  |                            0.732 |               -0.002 |
| adaptive           |      160 |               0.15  |                                     0.04  |                    0.339 |                    0.305 |                      0.356 |                 0.833 |       0.259 |                        0.582 |             0.003 |                    0.088 |                            0.689 |                0.001 |

## Strategy comparison (stress tests only)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |      120 |               0     |                                     0     |                    0     |                    0     |                      1     |                 0     |       0     |                        0.577 |             0     |                    0.1   |                            0.7   |                0     |
| periodic_retrain   |      120 |               0.958 |                                     0.946 |                    0.978 |                    0.022 |                      0     |                 0.696 |       2.896 |                        0.584 |             0.006 |                    0.1   |                            0.744 |                0.011 |
| always_recalibrate |      120 |               0.775 |                                     0.662 |                    0.957 |                    0.022 |                      0.022 |                 0.774 |       0.796 |                        0.581 |             0.004 |                    0.099 |                            0.708 |                0.008 |
| always_retrain     |      120 |               0.775 |                                     0.662 |                    0.957 |                    0.022 |                      0.022 |                 0.731 |       2.346 |                        0.584 |             0.006 |                    0.1   |                            0.744 |                0.007 |
| adaptive           |      120 |               0.183 |                                     0.041 |                    0.413 |                    0.217 |                      0.37  |                 0.818 |       0.292 |                        0.581 |             0.004 |                    0.099 |                            0.703 |                0.001 |

## Strategy comparison (real unseen-PHM shifts only)

| strategy           |   cycles |   intervention_rate |   unnecessary_interventions_when_harmless |   corrected_when_harmful |   escalated_when_harmful |   no_response_when_harmful |   candidates_rejected |   mean_cost |   test_bal_acc_after_harmful |   gain_on_harmful |   test_ece_after_harmful |   test_sensitivity_after_harmful |   change_on_harmless |
|:-------------------|---------:|--------------------:|------------------------------------------:|-------------------------:|-------------------------:|---------------------------:|----------------------:|------------:|-----------------------------:|------------------:|-------------------------:|---------------------------------:|---------------------:|
| static             |       40 |                0    |                                     0     |                    0     |                    0     |                      1     |                 0     |       0     |                        0.586 |             0     |                    0.051 |                            0.636 |                0     |
| periodic_retrain   |       40 |                1    |                                     1     |                    1     |                    0     |                      0     |                 0.575 |       3     |                        0.623 |             0.037 |                    0.053 |                            0.69  |               -0.025 |
| always_recalibrate |       40 |                1    |                                     1     |                    1     |                    0     |                      0     |                 0.825 |       1     |                        0.567 |            -0.019 |                    0.052 |                            0.636 |                0.007 |
| always_retrain     |       40 |                1    |                                     1     |                    1     |                    0     |                      0     |                 0.575 |       3     |                        0.623 |             0.037 |                    0.053 |                            0.69  |               -0.025 |
| adaptive           |       40 |                0.05 |                                     0.037 |                    0.077 |                    0.615 |                      0.308 |                 1     |       0.162 |                        0.586 |             0     |                    0.051 |                            0.636 |                0     |

## Shift types

| family                   | shift                              |   runs |   harmful_share |   mean_drop |   max_psi |   flagged_share |
|:-------------------------|:-----------------------------------|-------:|----------------:|------------:|----------:|----------------:|
| field_dropped            | WHZ not computed                   |      5 |             0.2 |       0.024 |     0.096 |             1   |
| field_dropped            | birth weight not collected         |      5 |             0.4 |      -0.014 |     0.096 |             1   |
| impossible_values        | 20% weights recorded 5x too high   |      5 |             0.2 |       0.009 |     0.303 |             1   |
| impossible_values        | 5% weights recorded 5x too high    |      5 |             0.2 |       0.001 |     0.105 |             0.2 |
| measurement_error        | height SD 1.0 cm, weight SD 0.3 kg |      5 |             0.2 |      -0     |     0.099 |             0.2 |
| measurement_error        | height SD 2.0 cm, weight SD 0.6 kg |      5 |             0.2 |       0.001 |     0.087 |             0.4 |
| measurement_error        | height SD 4.0 cm, weight SD 1.2 kg |      5 |             0.4 |       0.031 |     0.221 |             1   |
| missing_weight           | 10% weights missing                |      5 |             0.2 |       0.018 |     0.098 |             0.4 |
| missing_weight           | 25% weights missing                |      5 |             0.4 |       0.037 |     0.107 |             1   |
| missing_weight           | 50% weights missing                |      5 |             0.6 |       0.051 |     0.145 |             1   |
| missing_weight           | 75% weights missing                |      5 |             0.6 |       0.076 |     0.382 |             1   |
| new_phm_area             | unseen area PHM01                  |      5 |             0.6 |       0.047 |     0.918 |             1   |
| new_phm_area             | unseen area PHM02                  |      5 |             0.2 |      -0.005 |     0.93  |             1   |
| new_phm_area             | unseen area PHM03                  |      5 |             0.8 |       0.08  |     2.049 |             1   |
| new_phm_area             | unseen area PHM04                  |      5 |             0.6 |       0.059 |     1.498 |             1   |
| new_phm_area             | unseen area PHM05                  |      5 |             0   |      -0.023 |     0.98  |             1   |
| new_phm_area             | unseen area PHM06                  |      5 |             0   |      -0.078 |     0.672 |             1   |
| new_phm_area             | unseen area PHM07                  |      5 |             0.2 |      -0.036 |     0.482 |             1   |
| new_phm_area             | unseen area PHM10                  |      5 |             0.2 |      -0.009 |     0.604 |             1   |
| none                     | no shift                           |      5 |             0.2 |       0     |     0.096 |             0   |
| poorer_growth_population | WAZ tilt 0.5                       |      5 |             0   |       0.01  |     0.341 |             1   |
| poorer_growth_population | WAZ tilt 1.0                       |      5 |             0.6 |       0.017 |     1.215 |             1   |
| poorer_growth_population | WAZ tilt 1.5                       |      5 |             1   |       0.05  |     2.486 |             1   |
| prevalence               | prevalence 25%                     |      5 |             1   |      -0.003 |     0.196 |             1   |
| prevalence               | prevalence 40%                     |      5 |             1   |       0.004 |     0.308 |             1   |
| prevalence               | prevalence 5%                      |      5 |             0.4 |       0.016 |     0.204 |             0.8 |
| scale_bias               | scale reads 0.25 kg low            |      5 |             0   |       0.012 |     0.122 |             0.6 |
| scale_bias               | scale reads 0.5 kg low             |      5 |             0   |       0.025 |     0.216 |             1   |
| scale_bias               | scale reads 1.0 kg low             |      5 |             0.4 |       0.043 |     0.655 |             1   |
| younger_population       | age tilt 0.5                       |      5 |             0.2 |       0.001 |     0.364 |             1   |
| younger_population       | age tilt 1.0                       |      5 |             0.2 |       0.047 |     1.115 |             1   |
| younger_population       | age tilt 1.5                       |      5 |             0.6 |       0.063 |     2.178 |             1   |

## Does drift predict harm? (idea 1)

| predictors                                            |   r2_balanced_accuracy_drop |
|:------------------------------------------------------|----------------------------:|
| max_psi                                               |                       0.091 |
| max_ks                                                |                       0.065 |
| max_missing_delta                                     |                       0.013 |
| prediction_psi                                        |                       0.025 |
| max_psi + max_ks + max_missing_delta + prediction_psi |                       0.127 |

| monitor           |   auroc_for_harm |   corr_with_drop |
|:------------------|-----------------:|-----------------:|
| max_psi           |            0.631 |            0.302 |
| max_ks            |            0.599 |            0.254 |
| max_missing_delta |            0.603 |            0.112 |
| prediction_psi    |            0.632 |            0.157 |

Suggested monitor thresholds (maximise detection minus false alarms):

```
{
  "max_psi": {
    "threshold": 0.116,
    "detects_harm": 0.97,
    "false_alarm": 0.7
  },
  "max_ks": {
    "threshold": 0.102,
    "detects_harm": 0.95,
    "false_alarm": 0.72
  },
  "prediction_psi": {
    "threshold": 0.041,
    "detects_harm": 0.43,
    "false_alarm": 0.21
  },
  "current_rules_false_alarm_rate": 0.82
}
```
