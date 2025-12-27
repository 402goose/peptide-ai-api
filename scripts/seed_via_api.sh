#!/bin/bash
# Seed holistic data via production API

API_URL="https://peptide-ai-api-production.up.railway.app/api/v1/affiliate/admin"

echo "Seeding products..."

# PEPTIDES
curl -s -X POST "$API_URL/seed-product" -d "name=BPC-157&product_type=peptide&is_peptide=true&description=Body Protection Compound - healing and anti-inflammatory peptide" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=SS-31&product_type=peptide&is_peptide=true&description=Elamipretide - mitochondrial support peptide" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Semax&product_type=peptide&is_peptide=true&description=Nootropic peptide for cognitive enhancement" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Selank&product_type=peptide&is_peptide=true&description=Anxiolytic peptide for stress and anxiety" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Thymosin Alpha-1&product_type=peptide&is_peptide=true&description=Immune modulating peptide" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Dihexa&product_type=peptide&is_peptide=true&description=Cognitive enhancement peptide" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=NAD+ IM&product_type=peptide&is_peptide=true&description=Intramuscular NAD+ for cellular energy" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=GHK-Cu&product_type=peptide&is_peptide=true&description=Copper peptide for skin and wound healing" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=TB-500&product_type=peptide&is_peptide=true&description=Thymosin Beta-4 fragment for healing" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=LL-37&product_type=peptide&is_peptide=true&description=Antimicrobial peptide for immune support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=KPV&product_type=peptide&is_peptide=true&description=Anti-inflammatory peptide" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Larazotide&product_type=peptide&is_peptide=true&description=Gut barrier support peptide" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Epithalon&product_type=peptide&is_peptide=true&description=Telomerase activating peptide" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=DSIP&product_type=peptide&is_peptide=true&description=Delta sleep inducing peptide" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=PT-141&product_type=peptide&is_peptide=true&description=Melanocortin peptide for sexual function" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=MOTS-c&product_type=peptide&is_peptide=true&description=Mitochondrial peptide for metabolic health" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Semaglutide&product_type=peptide&is_peptide=true&description=GLP-1 agonist for metabolic health" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=5-Amino 1MQ&product_type=peptide&is_peptide=true&description=NNMT inhibitor for metabolism" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=P21&product_type=peptide&is_peptide=true&description=CNTF mimetic for neurogenesis" > /dev/null
echo "  Peptides done"

# ADAPTOGENS
curl -s -X POST "$API_URL/seed-product" -d "name=Ashwagandha&product_type=adaptogen&is_peptide=false&description=Adaptogen for stress, cortisol, and energy" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Rhodiola&product_type=adaptogen&is_peptide=false&description=Adaptogen for energy and mental performance" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Cordyceps&product_type=adaptogen&is_peptide=false&description=Mushroom for energy and endurance" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Lion's Mane&product_type=adaptogen&is_peptide=false&description=Mushroom for cognitive function" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Reishi&product_type=adaptogen&is_peptide=false&description=Mushroom for immune support and sleep" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Holy Basil&product_type=adaptogen&is_peptide=false&description=Adaptogen for stress and inflammation" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Maca&product_type=adaptogen&is_peptide=false&description=Root for energy and hormonal balance" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Licorice Root&product_type=adaptogen&is_peptide=false&description=Adrenal support herb" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Adrenal Cortex&product_type=supplement&is_peptide=false&description=Glandular support for adrenals" > /dev/null
echo "  Adaptogens done"

# AMINO ACIDS
curl -s -X POST "$API_URL/seed-product" -d "name=L-Theanine&product_type=amino_acid&is_peptide=false&description=Calming amino acid from tea" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=L-Tyrosine&product_type=amino_acid&is_peptide=false&description=Dopamine precursor" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=L-Glutamine&product_type=amino_acid&is_peptide=false&description=Gut healing and immune support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Glycine&product_type=amino_acid&is_peptide=false&description=Calming amino acid for sleep" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Taurine&product_type=amino_acid&is_peptide=false&description=Amino acid for heart and brain" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=NAC&product_type=amino_acid&is_peptide=false&description=N-Acetyl Cysteine - glutathione precursor" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Acetyl L-Carnitine&product_type=amino_acid&is_peptide=false&description=Mitochondrial support amino acid" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=GABA&product_type=amino_acid&is_peptide=false&description=Calming neurotransmitter" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Phenylalanine&product_type=amino_acid&is_peptide=false&description=Dopamine precursor" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Agmatine&product_type=amino_acid&is_peptide=false&description=Neuromodulator for mood and pain" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=5-HTP&product_type=amino_acid&is_peptide=false&description=Direct serotonin precursor" > /dev/null
echo "  Amino acids done"

# VITAMINS
curl -s -X POST "$API_URL/seed-product" -d "name=Vitamin D3&product_type=vitamin&is_peptide=false&description=Essential hormone vitamin" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Vitamin B12&product_type=vitamin&is_peptide=false&description=Energy and nerve vitamin" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Vitamin B Complex&product_type=vitamin&is_peptide=false&description=Full spectrum B vitamins" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Methylated B Complex&product_type=vitamin&is_peptide=false&description=Active form B vitamins" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Vitamin C&product_type=vitamin&is_peptide=false&description=Antioxidant and immune support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Riboflavin&product_type=vitamin&is_peptide=false&description=Vitamin B2 for energy and migraines" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Benfotiamine&product_type=vitamin&is_peptide=false&description=Fat-soluble vitamin B1" > /dev/null
echo "  Vitamins done"

# MINERALS
curl -s -X POST "$API_URL/seed-product" -d "name=Magnesium Glycinate&product_type=mineral&is_peptide=false&description=Highly absorbable calming magnesium" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Magnesium Threonate&product_type=mineral&is_peptide=false&description=Brain-penetrating magnesium" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Zinc&product_type=mineral&is_peptide=false&description=Immune and hormone mineral" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Selenium&product_type=mineral&is_peptide=false&description=Thyroid and antioxidant mineral" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Iron Bisglycinate&product_type=mineral&is_peptide=false&description=Gentle absorbable iron" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Potassium Citrate&product_type=mineral&is_peptide=false&description=Electrolyte mineral" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Iodine&product_type=mineral&is_peptide=false&description=Thyroid essential mineral" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Chromium&product_type=mineral&is_peptide=false&description=Blood sugar support mineral" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Boron&product_type=mineral&is_peptide=false&description=Bone and hormone mineral" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Electrolytes&product_type=mineral&is_peptide=false&description=Balanced mineral blend" > /dev/null
echo "  Minerals done"

# SUPPLEMENTS
curl -s -X POST "$API_URL/seed-product" -d "name=CoQ10&product_type=supplement&is_peptide=false&description=Mitochondrial coenzyme" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Alpha Lipoic Acid&product_type=supplement&is_peptide=false&description=Universal antioxidant" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Omega-3s&product_type=supplement&is_peptide=false&description=Fish oil for brain and inflammation" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Curcumin&product_type=supplement&is_peptide=false&description=Turmeric extract anti-inflammatory" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Quercetin&product_type=supplement&is_peptide=false&description=Flavonoid for inflammation and allergies" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=PQQ&product_type=supplement&is_peptide=false&description=Mitochondrial biogenesis support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Glutathione&product_type=supplement&is_peptide=false&description=Master antioxidant" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Alpha GPC&product_type=supplement&is_peptide=false&description=Choline source for brain" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Phosphatidylcholine&product_type=supplement&is_peptide=false&description=Cell membrane support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Phosphatidylserine&product_type=supplement&is_peptide=false&description=Brain cell membrane support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Inositol&product_type=supplement&is_peptide=false&description=Mood and hormone support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=SAMe&product_type=supplement&is_peptide=false&description=Methylation and mood support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=DIM&product_type=supplement&is_peptide=false&description=Estrogen metabolism support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=I3C&product_type=supplement&is_peptide=false&description=Indole-3-Carbinol for estrogen" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Berberine&product_type=supplement&is_peptide=false&description=Blood sugar and gut support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Milk Thistle&product_type=supplement&is_peptide=false&description=Liver support herb" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=TUDCA&product_type=supplement&is_peptide=false&description=Bile acid for liver support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Digestive Enzymes&product_type=supplement&is_peptide=false&description=Enzyme blend for digestion" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Betaine HCL&product_type=supplement&is_peptide=false&description=Stomach acid support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Beet Root&product_type=supplement&is_peptide=false&description=Nitric oxide support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Huperzine A&product_type=supplement&is_peptide=false&description=Acetylcholine support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Uridine Monophosphate&product_type=supplement&is_peptide=false&description=Brain health nucleotide" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Caffeine&product_type=supplement&is_peptide=false&description=Stimulant for focus" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Cinnamon Extract&product_type=supplement&is_peptide=false&description=Blood sugar support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Ginger Extract&product_type=supplement&is_peptide=false&description=Digestive and anti-nausea" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Melatonin&product_type=supplement&is_peptide=false&description=Sleep hormone" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=DHEA&product_type=hormone&is_peptide=false&description=Precursor hormone" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Pregnenolone&product_type=hormone&is_peptide=false&description=Master hormone precursor" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Collagen&product_type=supplement&is_peptide=false&description=Connective tissue support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Biotin&product_type=vitamin&is_peptide=false&description=Hair, skin, nails vitamin" > /dev/null
echo "  Supplements done"

# HERBS & PROBIOTICS
curl -s -X POST "$API_URL/seed-product" -d "name=Probiotics&product_type=probiotic&is_peptide=false&description=Beneficial gut bacteria" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Saccharomyces Boulardii&product_type=probiotic&is_peptide=false&description=Beneficial yeast probiotic" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Vitex&product_type=herb&is_peptide=false&description=Chasteberry for hormone balance" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Black Cohosh&product_type=herb&is_peptide=false&description=Menopause support herb" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Red Clover&product_type=herb&is_peptide=false&description=Phytoestrogen herb" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Evening Primrose Oil&product_type=herb&is_peptide=false&description=GLA source for hormones" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Dandelion&product_type=herb&is_peptide=false&description=Liver and diuretic herb" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Bitters&product_type=herb&is_peptide=false&description=Digestive bitters blend" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Oregano Oil&product_type=herb&is_peptide=false&description=Antimicrobial herb" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Caprylic Acid&product_type=herb&is_peptide=false&description=Antifungal from coconut" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=D-Mannose&product_type=supplement&is_peptide=false&description=Urinary tract support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Cranberry Extract&product_type=herb&is_peptide=false&description=Urinary tract support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Stinging Nettle&product_type=herb&is_peptide=false&description=Histamine and prostate support" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=DAO Enzyme&product_type=enzyme&is_peptide=false&description=Diamine oxidase for histamine" > /dev/null
curl -s -X POST "$API_URL/seed-product" -d "name=Lymphatic Herbs&product_type=herb&is_peptide=false&description=Blend for lymphatic drainage" > /dev/null
echo "  Herbs & probiotics done"

echo ""
echo "Seeding lab tests..."

curl -s -X POST "$API_URL/seed-lab" -d "name=Complete Thyroid Panel&description=TSH, Free T3, Free T4, RT3, TPO, TG antibodies" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Testosterone Panel&description=Total T, Free T, SHBG, Estradiol" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Female Hormone Panel&description=Estradiol, Progesterone, FSH, LH" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=DUTCH Test&description=Complete hormone metabolite test" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Cortisol Rhythm&description=4-point salivary cortisol" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Morning Cortisol&description=AM cortisol level" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Cortisol Awakening Response&description=CAR test for HPA axis" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Fasting Insulin&description=Insulin sensitivity marker" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=HbA1c&description=3-month average blood sugar" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Fasting Glucose&description=Blood sugar level" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Lipid Panel&description=Cholesterol, LDL, HDL, Triglycerides" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Leptin&description=Satiety hormone" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Homocysteine&description=Methylation and cardiovascular marker" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Uric Acid&description=Metabolic and joint health marker" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=CRP&description=C-Reactive Protein inflammation marker" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=ESR&description=Erythrocyte Sedimentation Rate" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Inflammation Markers&description=CRP, ESR, Ferritin panel" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Liver Panel&description=ALT, AST, GGT, Bilirubin" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=ALT/AST&description=Liver enzyme markers" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=GFR&description=Kidney filtration rate" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Kidney Panel&description=BUN, Creatinine, GFR" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Liver Ultrasound&description=Imaging for fatty liver" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Gallbladder Ultrasound&description=Imaging for gallbladder health" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Bile Acids Panel&description=Bile acid metabolism test" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=CBC&description=Complete Blood Count" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Ferritin&description=Iron storage marker" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Iron Panel&description=Iron, TIBC, Ferritin" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=B12&description=Vitamin B12 level" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=B Vitamin Panel&description=B12, Folate, B6 levels" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Immune Cell Differential&description=WBC breakdown" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=GI-MAP&description=Comprehensive stool analysis" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=GI-MAP Fungal Panel&description=Stool test for fungal overgrowth" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=SIBO Breath Test&description=Small intestinal bacterial overgrowth test" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Food Sensitivity Panel&description=IgG food reactions" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Zonulin&description=Leaky gut marker" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Urinalysis&description=Basic urine analysis" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Urine Culture&description=Infection identification" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Aldosterone&description=Fluid balance hormone" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Cognitive Panel&description=Homocysteine, B12, inflammatory markers" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Neurotransmitter Panel&description=Urinary neurotransmitter test" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Organic Acids Test&description=OAT for neurotransmitters" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Dopamine Pathways&description=Catecholamine metabolites" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Prolactin&description=Pituitary hormone" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=SHBG&description=Sex Hormone Binding Globulin" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=CMP&description=Comprehensive Metabolic Panel" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Methylation Markers&description=Homocysteine, B12, Folate" > /dev/null
curl -s -X POST "$API_URL/seed-lab" -d "name=Estrogen/Progesterone Rhythm&description=Cycle mapping test" > /dev/null
echo "  Lab tests done"

echo ""
echo "Seeding complete! Check the API at:"
echo "  https://peptide-ai-api-production.up.railway.app/api/v1/affiliate/products"
echo "  https://peptide-ai-api-production.up.railway.app/api/v1/affiliate/categories"
