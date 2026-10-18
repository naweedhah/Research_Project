export const dashboardMetrics = {
  totalDistricts: 25,
  highRiskDistricts: 6,
  predictedCases: 8426,
  predictedCasesChange: 3.1,
  triposhaRequirement: 45200,
  earlyWarningAlerts: 5,
  dataRefreshed: '12 minutes ago',
  modelVersion: 'XGBoost v3.1',
};

export const clinicStaffServices = {
  totalClinics: 125,
  nutritionOfficers: 320,
  healthcareWorkers: 860,
  activePrograms: 45,
  services: [
    { name: 'Growth Monitoring', coverage: 92 },
    { name: 'Nutrition Counseling', coverage: 84 },
    { name: 'Supplement Distribution', coverage: 78 },
    { name: 'Child Screening', coverage: 80 },
    { name: 'Maternal Nutrition Support', coverage: 71 },
  ],
};

export const triposhaDemand = [
  { name: 'High Risk', value: 18200, color: '#E74C3C' },
  { name: 'Medium Risk', value: 16800, color: '#F39C12' },
  { name: 'Low Risk', value: 10200, color: '#27AE60' },
];

export const topDistricts = [
  { rank: 1, district: 'Badulla', cases: 520, risk: 'High' },
  { rank: 2, district: 'Nuwara Eliya', cases: 495, risk: 'High' },
  { rank: 3, district: 'Batticaloa', cases: 480, risk: 'High' },
  { rank: 4, district: 'Monaragala', cases: 430, risk: 'Medium' },
  { rank: 5, district: 'Ampara', cases: 410, risk: 'Medium' },
];

export const programmePerformance = [
  { name: 'Triposha coverage', value: 74, target: 75 },
  { name: 'Growth monitoring attendance', value: 80, target: 85 },
  { name: 'Screening completion', value: 81, target: 85 },
  { name: 'Maternal support reach', value: 71, target: 80 },
];

export const forecastSummary = [
  { year: 2019, historical: 6200, predicted: null, upper: null, lower: null },
  { year: 2020, historical: 6550, predicted: null, upper: null, lower: null },
  { year: 2021, historical: 7100, predicted: null, upper: null, lower: null },
  { year: 2022, historical: 7600, predicted: null, upper: null, lower: null },
  { year: 2023, historical: 8050, predicted: 8050, upper: 8050, lower: 8050 },
  { year: 2024, historical: null, predicted: 8180, upper: 8600, lower: 7800 },
  { year: 2025, historical: null, predicted: 8426, upper: 9000, lower: 7950 },
  { year: 2026, historical: null, predicted: 8680, upper: 9450, lower: 8100 },
  { year: 2027, historical: null, predicted: 8920, upper: 9900, lower: 8250 },
];

export const notificationsSeed = [
  {
    id: 1,
    title: 'Critical Alert',
    preview: 'Badulla risk increased',
    message:
      'Badulla district risk classification has escalated to Critical. Predicted cases rose by +18% against the early-warning threshold. Immediate Triposha redistribution and clinic outreach are recommended for Uva Province.',
    type: 'critical',
    time: '8 min ago',
    read: false,
  },
  {
    id: 2,
    title: 'Triposha allocation completed',
    preview: 'Q2 distribution plan finalized',
    message:
      'The national Triposha allocation for Q2 has been finalized. 38,500 packs were assigned across 25 districts with priority given to High Risk zones. Warehouse dispatch schedules are ready for export.',
    type: 'success',
    time: '42 min ago',
    read: false,
  },
  {
    id: 3,
    title: 'New forecast generated',
    preview: 'XGBoost national run to 2035',
    message:
      'A new national forecast using XGBoost has been generated for 2024–2035. Predicted national caseload for 2025 is 8,426 children (+3.1%). Confidence band and district breakdown are available in Forecast Studio.',
    type: 'info',
    time: '2 hours ago',
    read: false,
  },
  {
    id: 4,
    title: 'Screening milestone',
    preview: 'Child screening reached 80%',
    message:
      'National child screening coverage has reached 80% this quarter. Maternal nutrition support remains at 71% and is below the 80% programme target.',
    type: 'info',
    time: 'Yesterday',
    read: true,
  },
];

export const userProfileSeed = {
  name: 'Dr. Nimal Perera',
  role: 'MOH Officer',
  email: 'n.perera@health.gov.lk',
  organization: 'Ministry of Health - Nutrition Division',
  avatar: null,
};
