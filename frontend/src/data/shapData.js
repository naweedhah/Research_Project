export const shapByDistrict = {
  Badulla: {
    prediction: 520,
    dmpi: 82,
    confidence: 92.4,
    trend: 'Increasing',
    risk: 'High',
    triposhaCoverage: 61,
    features: [
      { name: 'Poverty Rate', value: 31, color: '#6C5CE7', interpretation: 'Household poverty is the strongest single driver, reducing dietary diversity and access to protein-rich foods.' },
      { name: 'Food Inflation', value: 24, color: '#0B1F4D', interpretation: 'Rising food prices reduce purchasing power, pushing families toward calorie-dense but nutrient-poor diets.' },
      { name: 'Low Birth Weight', value: 17, color: '#F39C12', interpretation: 'Low birth weight is a strong predictor of stunting and wasting during the first 1,000 days.' },
      { name: 'Triposha Coverage', value: 14, color: '#27AE60', interpretation: 'Lower supplement coverage removes a protective factor, increasing predicted case counts.' },
      { name: 'Rainfall Variation', value: 13, color: '#3498DB', interpretation: 'Climate variability disrupts local food production and seasonal household income.' },
    ],
  },
  'Nuwara Eliya': {
    prediction: 495,
    dmpi: 80,
    confidence: 91.1,
    trend: 'Increasing',
    risk: 'High',
    triposhaCoverage: 64,
    features: [
      { name: 'Poverty Rate', value: 30, color: '#6C5CE7', interpretation: 'Estate-sector poverty remains a dominant structural driver of undernutrition.' },
      { name: 'Food Inflation', value: 24, color: '#0B1F4D', interpretation: 'High food prices in plantation areas reduce dietary quality for young children.' },
      { name: 'Low Birth Weight', value: 17, color: '#F39C12', interpretation: 'Elevated low birth weight rates amplify early-life malnutrition risk.' },
      { name: 'Triposha Coverage', value: 15, color: '#27AE60', interpretation: 'Coverage gaps leave vulnerable households without timely supplementation.' },
      { name: 'Rainfall Variation', value: 14, color: '#3498DB', interpretation: 'Hill-country climate shocks affect food availability and caregiving capacity.' },
    ],
  },
  Batticaloa: {
    prediction: 480,
    dmpi: 79,
    confidence: 90.5,
    trend: 'Increasing',
    risk: 'High',
    triposhaCoverage: 63,
    features: [
      { name: 'Poverty Rate', value: 29, color: '#6C5CE7', interpretation: 'Coastal household poverty constrains access to diverse nutritious foods.' },
      { name: 'Food Inflation', value: 23, color: '#0B1F4D', interpretation: 'Market price volatility reduces protein intake among under-five children.' },
      { name: 'Low Birth Weight', value: 16, color: '#F39C12', interpretation: 'Perinatal nutrition deficits cascade into higher SAM/MAM probability.' },
      { name: 'Triposha Coverage', value: 16, color: '#27AE60', interpretation: 'Incomplete supplement reach weakens protective programme impact.' },
      { name: 'Rainfall Variation', value: 16, color: '#3498DB', interpretation: 'Seasonal flooding patterns disrupt clinic attendance and supply chains.' },
    ],
  },
};

export function getShapForDistrict(name) {
  if (shapByDistrict[name]) return shapByDistrict[name];
  return {
    prediction: 320,
    dmpi: 55,
    confidence: 88.0,
    trend: 'Stable',
    risk: 'Medium',
    triposhaCoverage: 72,
    features: [
      { name: 'Poverty Rate', value: 28, color: '#6C5CE7', interpretation: 'Poverty remains an influential contributor to predicted malnutrition pressure.' },
      { name: 'Food Inflation', value: 22, color: '#0B1F4D', interpretation: 'Food price pressure reduces household dietary quality.' },
      { name: 'Low Birth Weight', value: 18, color: '#F39C12', interpretation: 'Birth-weight indicators elevate early childhood risk.' },
      { name: 'Triposha Coverage', value: 17, color: '#27AE60', interpretation: 'Programme coverage moderates but does not eliminate risk.' },
      { name: 'Rainfall Variation', value: 15, color: '#3498DB', interpretation: 'Climate variation adds seasonal uncertainty to food security.' },
    ],
  };
}
