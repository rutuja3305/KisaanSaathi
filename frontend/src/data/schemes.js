// schemes.js - mock scheme content. Replace with getSchemes() from your backend later.
// Always check official websites for the latest rules.
export const schemes = [
  {
    id: 'pm-kisan', shot: 's_pmkisan', name: 'PM-KISAN', category: 'Income support', states: 'all',
    short: 'Yearly income support for eligible farmer families.',
    about: 'Provides income support of ₹6,000 per year to eligible farmer families, paid in three instalments directly to the bank account.',
    eligibility: ['Farmer families with cultivable land', 'Some categories are excluded under the scheme rules', 'Bank account linked for direct transfer'],
    apply: ['Visit the PM-KISAN portal or your Common Service Centre', 'Register with Aadhaar, bank details and land record', 'Complete e-KYC to keep receiving instalments'],
    link: 'https://pmkisan.gov.in', source: 'PM-KISAN Operational Guidelines'
  },
  {
    id: 'pmfby', shot: 's_pmfby', name: 'PMFBY', category: 'Crop insurance', states: 'all',
    short: 'Insurance cover if your crop is lost to natural causes.',
    about: 'Pradhan Mantri Fasal Bima Yojana gives insurance cover against crop loss from natural calamities, pests and diseases. Farmers pay a small share of the premium.',
    eligibility: ['Farmers growing notified crops in notified areas', 'Both landowners and eligible tenant farmers', 'Enrol before the cut-off date for the season'],
    apply: ['Apply through your bank, Common Service Centre or the PMFBY portal', 'Keep land record and sowing details ready', 'Report crop loss quickly through the official channel'],
    link: 'https://pmfby.gov.in', source: 'PMFBY Operational Guidelines'
  },
  {
    id: 'mahadbt', shot: 's_mahadbt', name: 'MahaDBT', category: 'Subsidies', states: ['Maharashtra'],
    short: "Maharashtra's single portal to apply for farm subsidies.",
    about: 'The MahaDBT portal lets Maharashtra farmers apply for many agriculture department schemes and receive benefits directly in the bank account.',
    eligibility: ['Farmers in Maharashtra', 'Aadhaar-linked bank account', 'Scheme-specific conditions apply'],
    apply: ['Register on the MahaDBT farmer portal', 'Fill in your profile and land details', 'Choose the scheme and submit the application'],
    link: 'https://mahadbt.maharashtra.gov.in', source: 'MahaDBT Farmer Portal'
  },
  {
    id: 'kcc', shot: 's_kcc', name: 'Kisan Credit Card', category: 'Loans & credit', states: 'all',
    short: 'Easy short-term credit for seeds, fertiliser and farm needs.',
    about: 'Kisan Credit Card offers timely credit for cultivation and related needs, often with interest support when repaid on time.',
    eligibility: ['Farmers, tenant farmers and sharecroppers', 'Farmers in dairy, fisheries and allied work may also apply', 'Apply at your bank'],
    apply: ['Visit your bank branch or cooperative bank', 'Carry ID, address and land or cultivation proof', 'Ask about interest support and repayment terms'],
    link: 'https://www.myscheme.gov.in', source: 'Kisan Credit Card Guidelines'
  },
  {
    id: 'state-schemes', shot: 's_state', name: 'State Agriculture Schemes', category: 'State support', states: 'all',
    short: 'Support that depends on your state and district.',
    about: 'Every state runs its own agriculture schemes for irrigation, machinery, seeds and relief. Tell us where you farm and we will show what applies.',
    eligibility: ['Depends on the state and scheme', 'Location (state and district) helps us narrow this down'],
    apply: ['Check your state agriculture department', 'Visit the nearest Krishi office or Common Service Centre', 'Or ask KisanSathi about your district'],
    link: 'https://www.myscheme.gov.in', source: 'State Agriculture Department'
  }
]
export const categories = ['Income support', 'Crop insurance', 'Subsidies', 'Loans & credit', 'State support']
