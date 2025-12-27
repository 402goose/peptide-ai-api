#!/bin/bash
# Seed holistic data via production API with query params

API_URL="https://peptide-ai-api-production.up.railway.app/api/v1/affiliate/admin"

urlencode() {
  python3 -c "import urllib.parse; print(urllib.parse.quote('$1', safe=''))"
}

seed_product() {
  local name="$1"
  local type="$2"
  local is_peptide="$3"
  local desc="$4"

  local enc_name=$(urlencode "$name")
  local enc_desc=$(urlencode "$desc")

  curl -s -X POST "$API_URL/seed-product?name=$enc_name&product_type=$type&is_peptide=$is_peptide&description=$enc_desc" > /dev/null
}

seed_lab() {
  local name="$1"
  local desc="$2"

  local enc_name=$(urlencode "$name")
  local enc_desc=$(urlencode "$desc")

  curl -s -X POST "$API_URL/seed-lab?name=$enc_name&description=$enc_desc" > /dev/null
}

seed_symptom() {
  local name="$1"
  local category="$2"
  shift 2
  local keywords="$@"

  local enc_name=$(urlencode "$name")
  local enc_kw=$(urlencode "$keywords")

  curl -s -X POST "$API_URL/seed-symptom?name=$enc_name&category=$category&keywords=$enc_kw" > /dev/null
}

echo "=== Seeding Products ==="

# PEPTIDES
echo "Seeding peptides..."
seed_product "BPC-157" "peptide" "true" "Body Protection Compound - healing and anti-inflammatory"
seed_product "SS-31" "peptide" "true" "Elamipretide - mitochondrial support"
seed_product "Semax" "peptide" "true" "Nootropic peptide for cognitive enhancement"
seed_product "Selank" "peptide" "true" "Anxiolytic peptide for stress and anxiety"
seed_product "Thymosin Alpha-1" "peptide" "true" "Immune modulating peptide"
seed_product "Dihexa" "peptide" "true" "Cognitive enhancement peptide"
seed_product "NAD+ IM" "peptide" "true" "Intramuscular NAD+ for cellular energy"
seed_product "GHK-Cu" "peptide" "true" "Copper peptide for skin and wound healing"
seed_product "TB-500" "peptide" "true" "Thymosin Beta-4 fragment for healing"
seed_product "LL-37" "peptide" "true" "Antimicrobial peptide for immune support"
seed_product "KPV" "peptide" "true" "Anti-inflammatory peptide"
seed_product "Larazotide" "peptide" "true" "Gut barrier support peptide"
seed_product "Epithalon" "peptide" "true" "Telomerase activating peptide"
seed_product "DSIP" "peptide" "true" "Delta sleep inducing peptide"
seed_product "PT-141" "peptide" "true" "Melanocortin peptide for sexual function"
seed_product "MOTS-c" "peptide" "true" "Mitochondrial peptide for metabolic health"
seed_product "Semaglutide" "peptide" "true" "GLP-1 agonist for metabolic health"
seed_product "5-Amino 1MQ" "peptide" "true" "NNMT inhibitor for metabolism"
seed_product "P21" "peptide" "true" "CNTF mimetic for neurogenesis"
echo "  Done: Peptides"

# ADAPTOGENS
echo "Seeding adaptogens..."
seed_product "Ashwagandha" "adaptogen" "false" "Adaptogen for stress and energy"
seed_product "Rhodiola" "adaptogen" "false" "Adaptogen for energy and mental performance"
seed_product "Cordyceps" "adaptogen" "false" "Mushroom for energy and endurance"
seed_product "Lion's Mane" "adaptogen" "false" "Mushroom for cognitive function"
seed_product "Reishi" "adaptogen" "false" "Mushroom for immune support and sleep"
seed_product "Holy Basil" "adaptogen" "false" "Adaptogen for stress and inflammation"
seed_product "Maca" "adaptogen" "false" "Root for energy and hormonal balance"
seed_product "Licorice Root" "adaptogen" "false" "Adrenal support herb"
seed_product "Adrenal Cortex" "supplement" "false" "Glandular support for adrenals"
echo "  Done: Adaptogens"

# AMINO ACIDS
echo "Seeding amino acids..."
seed_product "L-Theanine" "amino_acid" "false" "Calming amino acid from tea"
seed_product "L-Tyrosine" "amino_acid" "false" "Dopamine precursor"
seed_product "L-Glutamine" "amino_acid" "false" "Gut healing and immune support"
seed_product "Glycine" "amino_acid" "false" "Calming amino acid for sleep"
seed_product "Taurine" "amino_acid" "false" "Amino acid for heart and brain"
seed_product "NAC" "amino_acid" "false" "N-Acetyl Cysteine - glutathione precursor"
seed_product "Acetyl L-Carnitine" "amino_acid" "false" "Mitochondrial support"
seed_product "GABA" "amino_acid" "false" "Calming neurotransmitter"
seed_product "Phenylalanine" "amino_acid" "false" "Dopamine precursor"
seed_product "Agmatine" "amino_acid" "false" "Neuromodulator for mood and pain"
seed_product "5-HTP" "amino_acid" "false" "Direct serotonin precursor"
echo "  Done: Amino acids"

# MINERALS
echo "Seeding minerals..."
seed_product "Magnesium Glycinate" "mineral" "false" "Highly absorbable calming magnesium"
seed_product "Magnesium Threonate" "mineral" "false" "Brain-penetrating magnesium"
seed_product "Zinc" "mineral" "false" "Immune and hormone mineral"
seed_product "Selenium" "mineral" "false" "Thyroid and antioxidant mineral"
seed_product "Iron Bisglycinate" "mineral" "false" "Gentle absorbable iron"
seed_product "Potassium Citrate" "mineral" "false" "Electrolyte mineral"
seed_product "Iodine" "mineral" "false" "Thyroid essential mineral"
seed_product "Chromium" "mineral" "false" "Blood sugar support mineral"
seed_product "Boron" "mineral" "false" "Bone and hormone mineral"
seed_product "Electrolytes" "mineral" "false" "Balanced mineral blend"
echo "  Done: Minerals"

# VITAMINS
echo "Seeding vitamins..."
seed_product "Vitamin D3" "vitamin" "false" "Essential hormone vitamin"
seed_product "Vitamin B12" "vitamin" "false" "Energy and nerve vitamin"
seed_product "Vitamin B Complex" "vitamin" "false" "Full spectrum B vitamins"
seed_product "Methylated B Complex" "vitamin" "false" "Active form B vitamins"
seed_product "Vitamin C" "vitamin" "false" "Antioxidant and immune support"
seed_product "Riboflavin" "vitamin" "false" "Vitamin B2 for energy and migraines"
seed_product "Benfotiamine" "vitamin" "false" "Fat-soluble vitamin B1"
seed_product "Biotin" "vitamin" "false" "Hair skin nails vitamin"
echo "  Done: Vitamins"

# SUPPLEMENTS
echo "Seeding supplements..."
seed_product "CoQ10" "supplement" "false" "Mitochondrial coenzyme"
seed_product "Alpha Lipoic Acid" "supplement" "false" "Universal antioxidant"
seed_product "Omega-3s" "supplement" "false" "Fish oil for brain and inflammation"
seed_product "Curcumin" "supplement" "false" "Turmeric extract anti-inflammatory"
seed_product "Quercetin" "supplement" "false" "Flavonoid for inflammation"
seed_product "PQQ" "supplement" "false" "Mitochondrial biogenesis support"
seed_product "Glutathione" "supplement" "false" "Master antioxidant"
seed_product "Alpha GPC" "supplement" "false" "Choline source for brain"
seed_product "Phosphatidylcholine" "supplement" "false" "Cell membrane support"
seed_product "Phosphatidylserine" "supplement" "false" "Brain cell membrane support"
seed_product "Inositol" "supplement" "false" "Mood and hormone support"
seed_product "SAMe" "supplement" "false" "Methylation and mood support"
seed_product "DIM" "supplement" "false" "Estrogen metabolism support"
seed_product "Berberine" "supplement" "false" "Blood sugar and gut support"
seed_product "Milk Thistle" "supplement" "false" "Liver support herb"
seed_product "TUDCA" "supplement" "false" "Bile acid for liver support"
seed_product "Digestive Enzymes" "supplement" "false" "Enzyme blend for digestion"
seed_product "Betaine HCL" "supplement" "false" "Stomach acid support"
seed_product "Beet Root" "supplement" "false" "Nitric oxide support"
seed_product "Huperzine A" "supplement" "false" "Acetylcholine support"
seed_product "Melatonin" "supplement" "false" "Sleep hormone"
seed_product "DHEA" "hormone" "false" "Precursor hormone"
seed_product "Collagen" "supplement" "false" "Connective tissue support"
echo "  Done: Supplements"

# HERBS & PROBIOTICS
echo "Seeding herbs and probiotics..."
seed_product "Probiotics" "probiotic" "false" "Beneficial gut bacteria"
seed_product "Saccharomyces Boulardii" "probiotic" "false" "Beneficial yeast probiotic"
seed_product "Vitex" "herb" "false" "Chasteberry for hormone balance"
seed_product "Black Cohosh" "herb" "false" "Menopause support herb"
seed_product "Evening Primrose Oil" "herb" "false" "GLA source for hormones"
seed_product "Dandelion" "herb" "false" "Liver and diuretic herb"
seed_product "Bitters" "herb" "false" "Digestive bitters blend"
seed_product "Oregano Oil" "herb" "false" "Antimicrobial herb"
seed_product "Caprylic Acid" "herb" "false" "Antifungal from coconut"
seed_product "D-Mannose" "supplement" "false" "Urinary tract support"
seed_product "Cranberry Extract" "herb" "false" "Urinary tract support"
seed_product "Stinging Nettle" "herb" "false" "Histamine and prostate support"
seed_product "DAO Enzyme" "enzyme" "false" "Diamine oxidase for histamine"
echo "  Done: Herbs & Probiotics"

echo ""
echo "=== Seeding Lab Tests ==="
seed_lab "Complete Thyroid Panel" "TSH, Free T3, Free T4, RT3, TPO, TG antibodies"
seed_lab "Testosterone Panel" "Total T, Free T, SHBG, Estradiol"
seed_lab "Female Hormone Panel" "Estradiol, Progesterone, FSH, LH"
seed_lab "DUTCH Test" "Complete hormone metabolite test"
seed_lab "Cortisol Rhythm" "4-point salivary cortisol"
seed_lab "Morning Cortisol" "AM cortisol level"
seed_lab "Fasting Insulin" "Insulin sensitivity marker"
seed_lab "HbA1c" "3-month average blood sugar"
seed_lab "Lipid Panel" "Cholesterol, LDL, HDL, Triglycerides"
seed_lab "CRP" "C-Reactive Protein inflammation marker"
seed_lab "Inflammation Markers" "CRP, ESR, Ferritin panel"
seed_lab "Liver Panel" "ALT, AST, GGT, Bilirubin"
seed_lab "GFR" "Kidney filtration rate"
seed_lab "CBC" "Complete Blood Count"
seed_lab "Ferritin" "Iron storage marker"
seed_lab "Iron Panel" "Iron, TIBC, Ferritin"
seed_lab "B12" "Vitamin B12 level"
seed_lab "GI-MAP" "Comprehensive stool analysis"
seed_lab "SIBO Breath Test" "Small intestinal bacterial overgrowth test"
seed_lab "Food Sensitivity Panel" "IgG food reactions"
seed_lab "Neurotransmitter Panel" "Urinary neurotransmitter test"
echo "  Done: Lab tests"

echo ""
echo "=== Seeding Symptoms ==="
# Energy & Fatigue
seed_symptom "Fatigue" "energy_fatigue" "tired exhaustion low energy"
seed_symptom "Burnout" "energy_fatigue" "exhausted overwhelmed burnt out"
seed_symptom "Brain Fog" "cognitive" "foggy unclear thinking mental haze"
seed_symptom "Poor Focus" "cognitive" "distracted concentration attention"
seed_symptom "Low Libido" "urinary_reproductive" "sex drive desire"
seed_symptom "Chronic Stress" "mood_mental" "stressed anxious overwhelmed"
seed_symptom "Sleep Issues" "sleep" "insomnia poor sleep waking"
seed_symptom "Depression" "mood_mental" "sad depressed low mood"
seed_symptom "Anxiety" "mood_mental" "anxious worried nervous panic"
seed_symptom "Bloating" "gut_digestive" "bloated gas distension"
seed_symptom "Leaky Gut" "gut_digestive" "intestinal permeability"
seed_symptom "SIBO" "gut_digestive" "small intestinal bacterial overgrowth"
seed_symptom "Inflammation" "inflammation_pain" "inflamed swelling"
seed_symptom "Joint Pain" "inflammation_pain" "aching joints"
seed_symptom "Migraines" "inflammation_pain" "headaches severe"
seed_symptom "Thyroid Sluggishness" "thyroid" "slow thyroid hypothyroid"
seed_symptom "High Cortisol" "hormonal_general" "elevated cortisol stress"
seed_symptom "Low Testosterone" "hormonal_male" "low T deficiency"
seed_symptom "PMS" "hormonal_female" "premenstrual period"
seed_symptom "Menopause Support" "hormonal_female" "perimenopause hot flashes"
seed_symptom "Estrogen Dominance" "hormonal_female" "high estrogen"
seed_symptom "PCOS Tendencies" "hormonal_female" "polycystic ovary"
seed_symptom "Insulin Resistance" "metabolic" "prediabetes blood sugar"
seed_symptom "Weight Resistance" "metabolic" "cant lose weight plateau"
seed_symptom "Hair Thinning" "skin_hair" "hair loss balding"
seed_symptom "Memory Decline" "cognitive" "memory loss forgetfulness"
seed_symptom "Low Dopamine" "mood_mental" "no motivation anhedonia"
seed_symptom "Frequent Illness" "immune" "always sick weak immune"
seed_symptom "Autoimmunity" "immune" "autoimmune immune dysfunction"
seed_symptom "Fatty Liver" "liver_detox" "NAFLD liver disease"
echo "  Done: Symptoms"

echo ""
echo "=== SEEDING COMPLETE ==="
echo ""
echo "Verify at:"
echo "  https://peptide-ai-api-production.up.railway.app/api/v1/affiliate/products"
echo "  https://peptide-ai-api-production.up.railway.app/api/v1/affiliate/symptoms"
echo "  https://peptide-ai-api-production.up.railway.app/api/v1/affiliate/categories"
