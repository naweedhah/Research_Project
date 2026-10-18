export const assistantKnowledge = [
  {
    keys: ['sam', 'severe acute'],
    answer:
      'SAM (Severe Acute Malnutrition) is the most critical form of undernutrition in children, typically identified by very low weight-for-height, visible severe wasting, or nutritional oedema. Children with SAM need urgent therapeutic feeding and clinical follow-up.',
  },
  {
    keys: ['mam', 'moderate acute'],
    answer:
      'MAM (Moderate Acute Malnutrition) indicates moderate wasting. Early detection through growth monitoring and timely Triposha / supplementary feeding can prevent progression to SAM.',
  },
  {
    keys: ['badulla', 'high risk'],
    answer:
      'Badulla is classified as High Risk with about 520 predicted cases and a DMPI score of 82. Key drivers include poverty rate (~31–32%), food inflation (~24–25%), low birth weight, and relatively lower Triposha coverage (~61%).',
  },
  {
    keys: ['factor', 'increase malnutrition', 'drivers', 'cause'],
    answer:
      'In this prototype, the main factors increasing malnutrition risk are household poverty, food inflation, low birth weight, incomplete Triposha coverage, and rainfall / climate variation. These map to socio-economic, maternal-child health, programme, and climate pathways.',
  },
  {
    keys: ['triposha', 'required', 'packs', 'requirement'],
    answer:
      'National Triposha requirement this quarter is approximately 45,200 packs. Available warehouse stock is 38,500 packs, leaving an additional procurement need of about 6,700 packs. High-risk districts receive priority in the distribution plan.',
  },
  {
    keys: ['forecast', 'xgboost', 'predict'],
    answer:
      'The forecasting module uses simulated XGBoost / Random Forest / LSTM runs. Historical caseload covers 2019–2023; projections extend to 2035 with a 95% confidence band. National 2025 predicted caseload is about 8,426 children (+3.1%).',
  },
  {
    keys: ['dmpi', 'pressure'],
    answer:
      'DMPI (District Malnutrition Pressure Index) is a composite research score used in this prototype to summarise predicted pressure. Scores above ~75 typically align with High Risk districts such as Badulla (82).',
  },
  {
    keys: ['clinic', 'staff', 'officer', 'service'],
    answer:
      'Nutrition clinic capacity in the prototype includes 125 clinics, 320 nutrition officers, 860 healthcare workers, and 45 active programmes. Core services are growth monitoring, counseling, supplement distribution, child screening, and maternal nutrition support.',
  },
  {
    keys: ['shap', 'explain', 'xai', 'feature'],
    answer:
      'Explainable AI (SHAP-style attributions) shows which features pushed a district prediction up or down. For Badulla, poverty and food inflation dominate, followed by low birth weight, Triposha coverage, and rainfall variation.',
  },
  {
    keys: ['hello', 'hi', 'help'],
    answer:
      "Hello! I'm the FedNutri-XAI Health Assistant. Ask me about malnutrition indicators, district risk levels, Triposha planning, or how the AI model reached a prediction.",
  },
];

export const suggestedQuestions = [
  'What is SAM?',
  'Why is Badulla high risk?',
  'What factors increase malnutrition?',
  'How much Triposha is required?',
  'Explain this forecast',
];

export function getAssistantReply(question) {
  const q = question.toLowerCase();
  for (const item of assistantKnowledge) {
    if (item.keys.some((k) => q.includes(k))) return item.answer;
  }
  return 'Based on the simulated research knowledge base: I can help with SAM/MAM definitions, district risk (e.g. Badulla), Triposha requirements, forecast interpretation, clinic staffing, and SHAP feature drivers. Try one of the suggested questions for a detailed answer.';
}
