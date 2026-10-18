export const alertsSeed = [
  {
    id: 1,
    district: 'Badulla',
    alertType: 'Threshold Breach',
    risk: 'Critical',
    increase: 18,
    date: '2025-03-12',
    status: 'Unread',
    details:
      'Predicted caseload exceeded the critical threshold by +18%. Immediate clinic surge capacity and Triposha top-up recommended.',
  },
  {
    id: 2,
    district: 'Monaragala',
    alertType: 'Emerging Risk',
    risk: 'High',
    increase: 12,
    date: '2025-03-11',
    status: 'Unread',
    details:
      'Emerging upward trend detected across three consecutive forecast windows. DMPI pressure rising toward High band.',
  },
  {
    id: 3,
    district: 'Ampara',
    alertType: 'Increasing Trend',
    risk: 'High',
    increase: 9,
    date: '2025-03-10',
    status: 'Unread',
    details:
      'Caseload trend increasing for 4 months. Food inflation and coverage gaps are co-driving the signal.',
  },
  {
    id: 4,
    district: 'Nuwara Eliya',
    alertType: 'Climate Risk',
    risk: 'Medium',
    increase: 7,
    date: '2025-03-09',
    status: 'Unread',
    details:
      'Rainfall variation anomaly linked to seasonal food insecurity risk. Monitor plantation-estate child cohorts.',
  },
  {
    id: 5,
    district: 'Batticaloa',
    alertType: 'Coverage Gap',
    risk: 'Medium',
    increase: 6,
    date: '2025-03-08',
    status: 'Read',
    details:
      'Triposha coverage dropped below programme target. Redistribution from low-pressure Western districts suggested.',
  },
  {
    id: 6,
    district: 'Mullaitivu',
    alertType: 'Threshold Breach',
    risk: 'Critical',
    increase: 15,
    date: '2025-03-07',
    status: 'Unread',
    details:
      'Critical threshold breach with constrained clinic staffing. Coordinate Northern Province outreach teams.',
  },
  {
    id: 7,
    district: 'Ratnapura',
    alertType: 'Stable Watch',
    risk: 'Low',
    increase: 2,
    date: '2025-03-06',
    status: 'Read',
    details:
      'Stable watch notice. No immediate action required; continue routine growth monitoring.',
  },
  {
    id: 8,
    district: 'Anuradhapura',
    alertType: 'Increasing Trend',
    risk: 'Medium',
    increase: 5,
    date: '2025-03-05',
    status: 'Read',
    details:
      'Mild upward trend linked to seasonal agricultural income variability.',
  },
];
