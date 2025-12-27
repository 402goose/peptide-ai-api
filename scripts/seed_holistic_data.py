"""
Seed script for holistic symptom-product-lab data

This contains all the mappings extracted from the holistic approaches guide (IMG_0876-0893).
Run this script to populate the database with symptoms, products, and lab tests.

Usage:
    python scripts/seed_holistic_data.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from models.documents import (
    HolisticProduct, Symptom, LabTest, SymptomProductMapping,
    ProductType, SymptomCategory
)
import re


# =============================================================================
# PRODUCTS DATA
# =============================================================================

PRODUCTS = [
    # PEPTIDES
    {"name": "BPC-157", "type": "peptide", "is_peptide": True, "description": "Body Protection Compound - healing and anti-inflammatory peptide"},
    {"name": "SS-31", "type": "peptide", "is_peptide": True, "description": "Elamipretide - mitochondrial support peptide"},
    {"name": "Semax", "type": "peptide", "is_peptide": True, "description": "Nootropic peptide for cognitive enhancement"},
    {"name": "Selank", "type": "peptide", "is_peptide": True, "description": "Anxiolytic peptide for stress and anxiety"},
    {"name": "Thymosin Alpha-1", "type": "peptide", "is_peptide": True, "description": "Immune modulating peptide"},
    {"name": "Dihexa", "type": "peptide", "is_peptide": True, "description": "Cognitive enhancement peptide"},
    {"name": "NAD+ IM", "type": "peptide", "is_peptide": True, "description": "Intramuscular NAD+ for cellular energy"},
    {"name": "GHK-Cu", "type": "peptide", "is_peptide": True, "description": "Copper peptide for skin and wound healing"},
    {"name": "TB-500", "type": "peptide", "is_peptide": True, "description": "Thymosin Beta-4 fragment for healing"},
    {"name": "LL-37", "type": "peptide", "is_peptide": True, "description": "Antimicrobial peptide for immune support"},
    {"name": "KPV", "type": "peptide", "is_peptide": True, "description": "Anti-inflammatory peptide"},
    {"name": "Larazotide", "type": "peptide", "is_peptide": True, "description": "Gut barrier support peptide"},
    {"name": "Epithalon", "type": "peptide", "is_peptide": True, "description": "Telomerase activating peptide for longevity"},
    {"name": "DSIP", "type": "peptide", "is_peptide": True, "description": "Delta sleep inducing peptide"},
    {"name": "CJC-1295", "type": "peptide", "is_peptide": True, "description": "Growth hormone releasing hormone analog"},
    {"name": "Ipamorelin", "type": "peptide", "is_peptide": True, "description": "Growth hormone secretagogue"},
    {"name": "Tesamorelin", "type": "peptide", "is_peptide": True, "description": "GHRH analog for fat loss"},
    {"name": "PT-141", "type": "peptide", "is_peptide": True, "description": "Melanocortin peptide for sexual function"},
    {"name": "Kisspeptin", "type": "peptide", "is_peptide": True, "description": "Reproductive hormone regulating peptide"},
    {"name": "MOTS-c", "type": "peptide", "is_peptide": True, "description": "Mitochondrial peptide for metabolic health"},
    {"name": "Humanin", "type": "peptide", "is_peptide": True, "description": "Neuroprotective mitochondrial peptide"},
    {"name": "Semaglutide", "type": "peptide", "is_peptide": True, "description": "GLP-1 agonist for metabolic health"},
    {"name": "Tirzepatide", "type": "peptide", "is_peptide": True, "description": "Dual GIP/GLP-1 agonist"},
    {"name": "AOD-9604", "type": "peptide", "is_peptide": True, "description": "Fat loss peptide fragment"},
    {"name": "5-Amino 1MQ", "type": "peptide", "is_peptide": True, "description": "NNMT inhibitor for metabolism"},
    {"name": "P21", "type": "peptide", "is_peptide": True, "description": "CNTF mimetic for neurogenesis"},
    {"name": "NA-Selank", "type": "peptide", "is_peptide": True, "description": "N-Acetyl Selank for enhanced bioavailability"},

    # ADAPTOGENS
    {"name": "Ashwagandha", "type": "adaptogen", "is_peptide": False, "description": "Adaptogen for stress, cortisol, and energy"},
    {"name": "Rhodiola", "type": "adaptogen", "is_peptide": False, "description": "Adaptogen for energy and mental performance"},
    {"name": "Cordyceps", "type": "adaptogen", "is_peptide": False, "description": "Mushroom for energy and endurance"},
    {"name": "Lion's Mane", "type": "adaptogen", "is_peptide": False, "description": "Mushroom for cognitive function and nerve health"},
    {"name": "Reishi", "type": "adaptogen", "is_peptide": False, "description": "Mushroom for immune support and sleep"},
    {"name": "Holy Basil", "type": "adaptogen", "is_peptide": False, "description": "Adaptogen for stress and inflammation"},
    {"name": "Maca", "type": "adaptogen", "is_peptide": False, "description": "Root for energy and hormonal balance"},
    {"name": "Schisandra", "type": "adaptogen", "is_peptide": False, "description": "Adaptogen for liver and stress support"},
    {"name": "Licorice Root", "type": "adaptogen", "is_peptide": False, "description": "Adrenal support herb"},
    {"name": "Adrenal Cortex", "type": "supplement", "is_peptide": False, "description": "Glandular support for adrenals"},

    # AMINO ACIDS
    {"name": "L-Theanine", "type": "amino_acid", "is_peptide": False, "description": "Calming amino acid from tea"},
    {"name": "L-Tyrosine", "type": "amino_acid", "is_peptide": False, "description": "Dopamine precursor"},
    {"name": "L-Glutamine", "type": "amino_acid", "is_peptide": False, "description": "Gut healing and immune support"},
    {"name": "L-Tryptophan", "type": "amino_acid", "is_peptide": False, "description": "Serotonin precursor"},
    {"name": "Glycine", "type": "amino_acid", "is_peptide": False, "description": "Calming amino acid for sleep"},
    {"name": "Taurine", "type": "amino_acid", "is_peptide": False, "description": "Amino acid for heart and brain"},
    {"name": "NAC", "type": "amino_acid", "is_peptide": False, "description": "N-Acetyl Cysteine - glutathione precursor"},
    {"name": "Acetyl L-Carnitine", "type": "amino_acid", "is_peptide": False, "description": "Mitochondrial support amino acid"},
    {"name": "GABA", "type": "amino_acid", "is_peptide": False, "description": "Calming neurotransmitter"},
    {"name": "Phenylalanine", "type": "amino_acid", "is_peptide": False, "description": "Dopamine and norepinephrine precursor"},
    {"name": "Agmatine", "type": "amino_acid", "is_peptide": False, "description": "Neuromodulator for mood and pain"},
    {"name": "5-HTP", "type": "amino_acid", "is_peptide": False, "description": "Direct serotonin precursor"},

    # VITAMINS
    {"name": "Vitamin D3", "type": "vitamin", "is_peptide": False, "description": "Essential hormone vitamin"},
    {"name": "Vitamin B12", "type": "vitamin", "is_peptide": False, "description": "Energy and nerve vitamin"},
    {"name": "Vitamin B Complex", "type": "vitamin", "is_peptide": False, "description": "Full spectrum B vitamins"},
    {"name": "Methylated B Complex", "type": "vitamin", "is_peptide": False, "description": "Active form B vitamins"},
    {"name": "Vitamin C", "type": "vitamin", "is_peptide": False, "description": "Antioxidant and immune support"},
    {"name": "Vitamin E", "type": "vitamin", "is_peptide": False, "description": "Fat-soluble antioxidant"},
    {"name": "Vitamin A", "type": "vitamin", "is_peptide": False, "description": "Vision and immune vitamin"},
    {"name": "Vitamin K2", "type": "vitamin", "is_peptide": False, "description": "Calcium metabolism vitamin"},
    {"name": "Riboflavin", "type": "vitamin", "is_peptide": False, "description": "Vitamin B2 for energy and migraines"},
    {"name": "Benfotiamine", "type": "vitamin", "is_peptide": False, "description": "Fat-soluble vitamin B1"},

    # MINERALS
    {"name": "Magnesium Glycinate", "type": "mineral", "is_peptide": False, "description": "Highly absorbable calming magnesium"},
    {"name": "Magnesium Threonate", "type": "mineral", "is_peptide": False, "description": "Brain-penetrating magnesium"},
    {"name": "Zinc", "type": "mineral", "is_peptide": False, "description": "Immune and hormone mineral"},
    {"name": "Selenium", "type": "mineral", "is_peptide": False, "description": "Thyroid and antioxidant mineral"},
    {"name": "Iron Bisglycinate", "type": "mineral", "is_peptide": False, "description": "Gentle absorbable iron"},
    {"name": "Potassium Citrate", "type": "mineral", "is_peptide": False, "description": "Electrolyte mineral"},
    {"name": "Iodine", "type": "mineral", "is_peptide": False, "description": "Thyroid essential mineral"},
    {"name": "Chromium", "type": "mineral", "is_peptide": False, "description": "Blood sugar support mineral"},
    {"name": "Boron", "type": "mineral", "is_peptide": False, "description": "Bone and hormone mineral"},
    {"name": "Electrolytes", "type": "mineral", "is_peptide": False, "description": "Balanced mineral blend"},

    # SUPPLEMENTS
    {"name": "CoQ10", "type": "supplement", "is_peptide": False, "description": "Mitochondrial coenzyme"},
    {"name": "Alpha Lipoic Acid", "type": "supplement", "is_peptide": False, "description": "Universal antioxidant"},
    {"name": "Omega-3s", "type": "supplement", "is_peptide": False, "description": "Fish oil for brain and inflammation"},
    {"name": "Curcumin", "type": "supplement", "is_peptide": False, "description": "Turmeric extract anti-inflammatory"},
    {"name": "Quercetin", "type": "supplement", "is_peptide": False, "description": "Flavonoid for inflammation and allergies"},
    {"name": "Resveratrol", "type": "supplement", "is_peptide": False, "description": "Longevity polyphenol"},
    {"name": "PQQ", "type": "supplement", "is_peptide": False, "description": "Mitochondrial biogenesis support"},
    {"name": "Glutathione", "type": "supplement", "is_peptide": False, "description": "Master antioxidant"},
    {"name": "Alpha GPC", "type": "supplement", "is_peptide": False, "description": "Choline source for brain"},
    {"name": "Phosphatidylcholine", "type": "supplement", "is_peptide": False, "description": "Cell membrane support"},
    {"name": "Phosphatidylserine", "type": "supplement", "is_peptide": False, "description": "Brain cell membrane support"},
    {"name": "Inositol", "type": "supplement", "is_peptide": False, "description": "Mood and hormone support"},
    {"name": "SAMe", "type": "supplement", "is_peptide": False, "description": "Methylation and mood support"},
    {"name": "DIM", "type": "supplement", "is_peptide": False, "description": "Estrogen metabolism support"},
    {"name": "I3C", "type": "supplement", "is_peptide": False, "description": "Indole-3-Carbinol for estrogen balance"},
    {"name": "Berberine", "type": "supplement", "is_peptide": False, "description": "Blood sugar and gut support"},
    {"name": "Milk Thistle", "type": "supplement", "is_peptide": False, "description": "Liver support herb"},
    {"name": "TUDCA", "type": "supplement", "is_peptide": False, "description": "Bile acid for liver support"},
    {"name": "Digestive Enzymes", "type": "supplement", "is_peptide": False, "description": "Enzyme blend for digestion"},
    {"name": "Betaine HCL", "type": "supplement", "is_peptide": False, "description": "Stomach acid support"},
    {"name": "Beet Root", "type": "supplement", "is_peptide": False, "description": "Nitric oxide support"},
    {"name": "Huperzine A", "type": "supplement", "is_peptide": False, "description": "Acetylcholine support"},
    {"name": "Uridine Monophosphate", "type": "supplement", "is_peptide": False, "description": "Brain health nucleotide"},
    {"name": "Caffeine", "type": "supplement", "is_peptide": False, "description": "Stimulant for focus"},
    {"name": "Cinnamon Extract", "type": "supplement", "is_peptide": False, "description": "Blood sugar support"},
    {"name": "Ginger Extract", "type": "supplement", "is_peptide": False, "description": "Digestive and anti-nausea"},
    {"name": "Melatonin", "type": "supplement", "is_peptide": False, "description": "Sleep hormone"},
    {"name": "DHEA", "type": "hormone", "is_peptide": False, "description": "Precursor hormone"},
    {"name": "Pregnenolone", "type": "hormone", "is_peptide": False, "description": "Master hormone precursor"},

    # PROBIOTICS
    {"name": "Probiotics", "type": "probiotic", "is_peptide": False, "description": "Beneficial gut bacteria"},
    {"name": "Spore Probiotics", "type": "probiotic", "is_peptide": False, "description": "Shelf-stable spore-forming probiotics"},
    {"name": "Saccharomyces Boulardii", "type": "probiotic", "is_peptide": False, "description": "Beneficial yeast probiotic"},

    # HERBS
    {"name": "Vitex", "type": "herb", "is_peptide": False, "description": "Chasteberry for hormone balance"},
    {"name": "Black Cohosh", "type": "herb", "is_peptide": False, "description": "Menopause support herb"},
    {"name": "Red Clover", "type": "herb", "is_peptide": False, "description": "Phytoestrogen herb"},
    {"name": "Dong Quai", "type": "herb", "is_peptide": False, "description": "Female hormone support"},
    {"name": "Evening Primrose Oil", "type": "herb", "is_peptide": False, "description": "GLA source for hormones"},
    {"name": "Dandelion", "type": "herb", "is_peptide": False, "description": "Liver and diuretic herb"},
    {"name": "Bitters", "type": "herb", "is_peptide": False, "description": "Digestive bitters blend"},
    {"name": "Oregano Oil", "type": "herb", "is_peptide": False, "description": "Antimicrobial herb"},
    {"name": "Caprylic Acid", "type": "herb", "is_peptide": False, "description": "Antifungal from coconut"},
    {"name": "D-Mannose", "type": "supplement", "is_peptide": False, "description": "Urinary tract support"},
    {"name": "Cranberry Extract", "type": "herb", "is_peptide": False, "description": "Urinary tract support"},
    {"name": "Saw Palmetto", "type": "herb", "is_peptide": False, "description": "Prostate and hormone support"},
    {"name": "Stinging Nettle", "type": "herb", "is_peptide": False, "description": "Histamine and prostate support"},
    {"name": "DAO Enzyme", "type": "enzyme", "is_peptide": False, "description": "Diamine oxidase for histamine"},
    {"name": "Lymphatic Herbs", "type": "herb", "is_peptide": False, "description": "Blend for lymphatic drainage"},
]


# =============================================================================
# LAB TESTS DATA
# =============================================================================

LAB_TESTS = [
    # Hormone Panels
    {"name": "Complete Thyroid Panel", "description": "TSH, Free T3, Free T4, RT3, TPO, TG antibodies"},
    {"name": "Testosterone Panel", "description": "Total T, Free T, SHBG, Estradiol"},
    {"name": "Female Hormone Panel", "description": "Estradiol, Progesterone, FSH, LH"},
    {"name": "DUTCH Test", "description": "Complete hormone metabolite test"},
    {"name": "Cortisol Rhythm", "description": "4-point salivary cortisol"},
    {"name": "Morning Cortisol", "description": "AM cortisol level"},
    {"name": "Cortisol Awakening Response", "description": "CAR test for HPA axis"},

    # Metabolic
    {"name": "Fasting Insulin", "description": "Insulin sensitivity marker"},
    {"name": "HbA1c", "description": "3-month average blood sugar"},
    {"name": "Fasting Glucose", "description": "Blood sugar level"},
    {"name": "Lipid Panel", "description": "Cholesterol, LDL, HDL, Triglycerides"},
    {"name": "Leptin", "description": "Satiety hormone"},
    {"name": "Homocysteine", "description": "Methylation and cardiovascular marker"},
    {"name": "Uric Acid", "description": "Metabolic and joint health marker"},

    # Inflammation
    {"name": "CRP", "description": "C-Reactive Protein inflammation marker"},
    {"name": "ESR", "description": "Erythrocyte Sedimentation Rate"},
    {"name": "Inflammation Markers", "description": "CRP, ESR, Ferritin panel"},

    # Liver & Kidney
    {"name": "Liver Panel", "description": "ALT, AST, GGT, Bilirubin"},
    {"name": "ALT/AST", "description": "Liver enzyme markers"},
    {"name": "GFR", "description": "Kidney filtration rate"},
    {"name": "Kidney Panel", "description": "BUN, Creatinine, GFR"},
    {"name": "Liver Ultrasound", "description": "Imaging for fatty liver"},
    {"name": "Gallbladder Ultrasound", "description": "Imaging for gallbladder health"},
    {"name": "Bile Acids Panel", "description": "Bile acid metabolism test"},

    # Blood
    {"name": "CBC", "description": "Complete Blood Count"},
    {"name": "Ferritin", "description": "Iron storage marker"},
    {"name": "Iron Panel", "description": "Iron, TIBC, Ferritin, % Saturation"},
    {"name": "B12", "description": "Vitamin B12 level"},
    {"name": "Folate", "description": "Vitamin B9 level"},
    {"name": "B Vitamin Panel", "description": "B12, Folate, B6 levels"},
    {"name": "Immune Cell Differential", "description": "WBC breakdown"},

    # Gut
    {"name": "GI-MAP", "description": "Comprehensive stool analysis"},
    {"name": "GI-MAP Fungal Panel", "description": "Stool test for fungal overgrowth"},
    {"name": "SIBO Breath Test", "description": "Small intestinal bacterial overgrowth test"},
    {"name": "Food Sensitivity Panel", "description": "IgG food reactions"},
    {"name": "Zonulin", "description": "Leaky gut marker"},

    # Urinary
    {"name": "Urinalysis", "description": "Basic urine analysis"},
    {"name": "Urine Culture", "description": "Infection identification"},
    {"name": "Aldosterone", "description": "Fluid balance hormone"},

    # Cognitive
    {"name": "Cognitive Panel", "description": "Homocysteine, B12, inflammatory markers"},
    {"name": "Neurotransmitter Panel", "description": "Urinary neurotransmitter test"},
    {"name": "Organic Acids Test", "description": "OAT for neurotransmitters and metabolism"},
    {"name": "Dopamine Pathways", "description": "Catecholamine metabolites"},

    # Other
    {"name": "Prolactin", "description": "Pituitary hormone"},
    {"name": "SHBG", "description": "Sex Hormone Binding Globulin"},
    {"name": "CMP", "description": "Comprehensive Metabolic Panel"},
    {"name": "Methylation Markers", "description": "Homocysteine, B12, Folate"},
    {"name": "Estrogen/Progesterone Rhythm", "description": "Cycle mapping test"},
]


# =============================================================================
# SYMPTOM-PRODUCT-LAB MAPPINGS
# =============================================================================

SYMPTOM_MAPPINGS = [
    # === IMG_0876: Energy & Fatigue ===
    {
        "name": "Fatigue",
        "category": "energy_fatigue",
        "products": ["Ashwagandha", "Rhodiola", "BPC-157", "SS-31"],
        "labs": ["Complete Thyroid Panel", "Cortisol Rhythm", "Iron Panel"],
        "keywords": ["tired", "exhaustion", "low energy", "no energy"]
    },
    {
        "name": "Burnout",
        "category": "energy_fatigue",
        "products": ["Semax", "Selank", "NAC", "Phosphatidylserine"],
        "labs": ["Cortisol Rhythm", "DUTCH Test"],
        "keywords": ["exhausted", "overwhelmed", "burnt out"]
    },
    {
        "name": "Brain Fog",
        "category": "cognitive",
        "products": ["Lion's Mane", "Semax", "Alpha GPC", "Omega-3s"],
        "labs": ["Complete Thyroid Panel", "B12", "Inflammation Markers"],
        "keywords": ["foggy", "unclear thinking", "mental haze", "cloudy mind"]
    },
    {
        "name": "Poor Focus",
        "category": "cognitive",
        "products": ["L-Tyrosine", "Alpha GPC", "Caffeine", "Semax"],
        "labs": ["Dopamine Pathways", "Complete Thyroid Panel"],
        "keywords": ["distracted", "cant concentrate", "attention problems"]
    },
    {
        "name": "Low Libido",
        "category": "urinary_reproductive",
        "products": ["PT-141", "Maca", "DHEA", "Zinc"],
        "labs": ["Testosterone Panel", "DUTCH Test"],
        "keywords": ["no sex drive", "low desire", "decreased libido"]
    },

    # === IMG_0877: Recovery & Stress ===
    {
        "name": "Slow Recovery",
        "category": "recovery",
        "products": ["BPC-157", "TB-500", "Glutamine", "CoQ10"],
        "labs": ["Inflammation Markers", "CRP"],
        "keywords": ["not healing", "prolonged recovery", "slow healing"]
    },
    {
        "name": "Chronic Stress",
        "category": "mood_mental",
        "products": ["Ashwagandha", "Selank", "L-Theanine", "Magnesium Glycinate"],
        "labs": ["Cortisol Rhythm", "DUTCH Test"],
        "keywords": ["stressed", "anxious", "overwhelmed"]
    },
    {
        "name": "Sleep Issues",
        "category": "sleep",
        "products": ["DSIP", "Glycine", "Magnesium Glycinate", "Melatonin"],
        "labs": ["Cortisol Rhythm", "Cortisol Awakening Response"],
        "keywords": ["insomnia", "cant sleep", "poor sleep", "waking up"]
    },
    {
        "name": "Depression",
        "category": "mood_mental",
        "products": ["SAMe", "Omega-3s", "5-HTP", "Semax"],
        "labs": ["DUTCH Test", "Complete Thyroid Panel", "B12"],
        "keywords": ["sad", "depressed", "low mood", "hopeless"]
    },
    {
        "name": "Stress Eating",
        "category": "appetite_cravings",
        "products": ["5-HTP", "Inositol", "L-Glutamine", "Ashwagandha"],
        "labs": ["Cortisol Rhythm", "Fasting Insulin"],
        "keywords": ["emotional eating", "binge eating", "comfort eating"]
    },
    {
        "name": "Adrenal Depletion",
        "category": "energy_fatigue",
        "products": ["Adrenal Cortex", "Ashwagandha", "Vitamin C", "Licorice Root"],
        "labs": ["Cortisol Rhythm", "DUTCH Test", "Morning Cortisol"],
        "keywords": ["adrenal fatigue", "exhausted adrenals"]
    },
    {
        "name": "Neural Burnout",
        "category": "cognitive",
        "products": ["Lion's Mane", "NAC", "Phosphatidylserine", "Omega-3s"],
        "labs": ["Neurotransmitter Panel", "Organic Acids Test"],
        "keywords": ["mental exhaustion", "cognitive fatigue"]
    },
    {
        "name": "Oxidative Stress",
        "category": "inflammation_pain",
        "products": ["NAC", "Glutathione", "Alpha Lipoic Acid", "CoQ10"],
        "labs": ["Inflammation Markers", "Organic Acids Test"],
        "keywords": ["free radicals", "cellular damage"]
    },
    {
        "name": "Gut Inflammation",
        "category": "gut_digestive",
        "products": ["BPC-157", "L-Glutamine", "Curcumin", "Probiotics"],
        "labs": ["GI-MAP", "Zonulin", "Food Sensitivity Panel"],
        "keywords": ["inflamed gut", "GI inflammation"]
    },

    # === IMG_0878: Gut & Immune ===
    {
        "name": "Bloating",
        "category": "gut_digestive",
        "products": ["Digestive Enzymes", "Probiotics", "Betaine HCL", "Ginger Extract"],
        "labs": ["GI-MAP", "SIBO Breath Test"],
        "keywords": ["bloated", "distended", "gas", "distension"]
    },
    {
        "name": "Candida",
        "category": "gut_digestive",
        "products": ["Caprylic Acid", "Oregano Oil", "Saccharomyces Boulardii", "Berberine"],
        "labs": ["GI-MAP Fungal Panel", "Organic Acids Test"],
        "keywords": ["yeast overgrowth", "fungal", "thrush"]
    },
    {
        "name": "SIBO",
        "category": "gut_digestive",
        "products": ["Oregano Oil", "Berberine", "Digestive Enzymes", "Probiotics"],
        "labs": ["SIBO Breath Test", "GI-MAP"],
        "keywords": ["small intestinal bacterial overgrowth"]
    },
    {
        "name": "Leaky Gut",
        "category": "gut_digestive",
        "products": ["L-Glutamine", "BPC-157", "Larazotide", "Zinc"],
        "labs": ["Zonulin", "Food Sensitivity Panel", "GI-MAP"],
        "keywords": ["intestinal permeability", "permeable gut"]
    },
    {
        "name": "Food Sensitivities",
        "category": "gut_digestive",
        "products": ["L-Glutamine", "Digestive Enzymes", "Probiotics", "Quercetin"],
        "labs": ["Food Sensitivity Panel", "GI-MAP"],
        "keywords": ["food reactions", "food intolerance"]
    },
    {
        "name": "Autoimmunity",
        "category": "immune",
        "products": ["NAC", "Vitamin D3", "Omega-3s", "Curcumin"],
        "labs": ["Inflammation Markers", "Complete Thyroid Panel"],
        "keywords": ["autoimmune", "immune dysfunction"]
    },
    {
        "name": "Immune Fatigue",
        "category": "immune",
        "products": ["Thymosin Alpha-1", "Vitamin C", "Zinc", "Reishi"],
        "labs": ["Immune Cell Differential", "CBC"],
        "keywords": ["weak immune", "always sick", "low immunity"]
    },
    {
        "name": "Viral Reactivation",
        "category": "immune",
        "products": ["Thymosin Alpha-1", "LL-37", "NAC", "Vitamin C"],
        "labs": ["Immune Cell Differential", "CBC"],
        "keywords": ["EBV", "herpes", "viral flare"]
    },

    # === IMG_0879: Infection & Inflammation ===
    {
        "name": "Chronic Infection",
        "category": "immune",
        "products": ["LL-37", "Thymosin Alpha-1", "NAC", "Oregano Oil"],
        "labs": ["CBC", "Immune Cell Differential", "CRP"],
        "keywords": ["persistent infection", "recurring infection"]
    },
    {
        "name": "Eczema",
        "category": "skin_hair",
        "products": ["Omega-3s", "Vitamin D3", "Probiotics", "GHK-Cu"],
        "labs": ["Food Sensitivity Panel", "Inflammation Markers"],
        "keywords": ["dermatitis", "itchy skin", "skin inflammation"]
    },
    {
        "name": "Flu/Viral Illness",
        "category": "immune",
        "products": ["Thymosin Alpha-1", "Vitamin C", "Zinc", "NAC"],
        "labs": ["CBC", "Immune Cell Differential"],
        "keywords": ["cold", "flu", "virus", "sick"]
    },
    {
        "name": "Wound Healing",
        "category": "recovery",
        "products": ["BPC-157", "TB-500", "GHK-Cu", "Zinc"],
        "labs": ["Inflammation Markers", "B Vitamin Panel"],
        "keywords": ["slow wound healing", "cuts not healing"]
    },
    {
        "name": "Lung Support",
        "category": "immune",
        "products": ["NAC", "Quercetin", "Vitamin C", "BPC-157"],
        "labs": ["Inflammation Markers", "CBC"],
        "keywords": ["respiratory", "breathing", "lungs"]
    },
    {
        "name": "Inflammation",
        "category": "inflammation_pain",
        "products": ["Curcumin", "Omega-3s", "BPC-157", "Quercetin"],
        "labs": ["CRP", "ESR", "Inflammation Markers"],
        "keywords": ["inflamed", "swelling", "inflammatory"]
    },
    {
        "name": "Mitochondrial Decline",
        "category": "energy_fatigue",
        "products": ["SS-31", "CoQ10", "PQQ", "NAD+ IM"],
        "labs": ["Organic Acids Test"],
        "keywords": ["mito dysfunction", "cellular energy decline"]
    },

    # === IMG_0880: Metabolic & Hormonal ===
    {
        "name": "Thyroid Sluggishness",
        "category": "thyroid",
        "products": ["Selenium", "Iodine", "Zinc", "Ashwagandha"],
        "labs": ["Complete Thyroid Panel"],
        "keywords": ["slow thyroid", "hypothyroid symptoms"]
    },
    {
        "name": "High A1C",
        "category": "metabolic",
        "products": ["Berberine", "Chromium", "Cinnamon Extract", "Inositol"],
        "labs": ["HbA1c", "Fasting Insulin", "Fasting Glucose"],
        "keywords": ["prediabetes", "high blood sugar", "glucose issues"]
    },
    {
        "name": "High LDL",
        "category": "cardiovascular",
        "products": ["Omega-3s", "Berberine", "NAC", "CoQ10"],
        "labs": ["Lipid Panel", "Inflammation Markers"],
        "keywords": ["high cholesterol", "elevated LDL"]
    },
    {
        "name": "High ALT",
        "category": "liver_detox",
        "products": ["NAC", "Milk Thistle", "TUDCA", "Alpha Lipoic Acid"],
        "labs": ["Liver Panel", "ALT/AST", "Liver Ultrasound"],
        "keywords": ["elevated liver enzymes", "liver stress"]
    },
    {
        "name": "Low GFR",
        "category": "kidney_fluid",
        "products": ["NAC", "CoQ10", "Omega-3s"],
        "labs": ["GFR", "Kidney Panel", "CMP"],
        "keywords": ["kidney function", "low kidney filtration"]
    },
    {
        "name": "Low Testosterone",
        "category": "hormonal_male",
        "products": ["DHEA", "Zinc", "Boron", "Ashwagandha"],
        "labs": ["Testosterone Panel", "SHBG"],
        "keywords": ["low T", "testosterone deficiency", "hypogonadism"]
    },
    {
        "name": "PMS",
        "category": "hormonal_female",
        "products": ["Vitex", "Magnesium Glycinate", "Evening Primrose Oil", "DIM"],
        "labs": ["Female Hormone Panel", "DUTCH Test"],
        "keywords": ["premenstrual", "period symptoms", "menstrual issues"]
    },

    # === IMG_0881: More Hormonal ===
    {
        "name": "Menopause Support",
        "category": "hormonal_female",
        "products": ["Black Cohosh", "Maca", "Red Clover", "DIM"],
        "labs": ["Female Hormone Panel", "DUTCH Test"],
        "keywords": ["perimenopause", "hot flashes", "menopausal symptoms"]
    },
    {
        "name": "High Ferritin",
        "category": "liver_detox",
        "products": ["Curcumin", "Green Tea Extract", "NAC"],
        "labs": ["Ferritin", "Iron Panel", "Liver Panel"],
        "keywords": ["iron overload", "elevated ferritin"]
    },
    {
        "name": "High Cortisol",
        "category": "hormonal_general",
        "products": ["Ashwagandha", "Phosphatidylserine", "Holy Basil", "Rhodiola"],
        "labs": ["Cortisol Rhythm", "DUTCH Test"],
        "keywords": ["elevated cortisol", "stress hormones high"]
    },
    {
        "name": "Low Cortisol",
        "category": "hormonal_general",
        "products": ["Licorice Root", "Adrenal Cortex", "Vitamin C", "Pregnenolone"],
        "labs": ["Cortisol Rhythm", "Morning Cortisol", "DUTCH Test"],
        "keywords": ["adrenal insufficiency", "low stress hormones"]
    },
    {
        "name": "Water Retention",
        "category": "kidney_fluid",
        "products": ["Dandelion", "Potassium Citrate", "Magnesium Glycinate", "Taurine"],
        "labs": ["Aldosterone", "Kidney Panel", "Electrolytes"],
        "keywords": ["fluid retention", "swelling", "edema", "puffy"]
    },
    {
        "name": "Weight Resistance",
        "category": "metabolic",
        "products": ["Semaglutide", "5-Amino 1MQ", "Berberine", "MOTS-c"],
        "labs": ["Fasting Insulin", "Complete Thyroid Panel", "Leptin"],
        "keywords": ["cant lose weight", "weight plateau", "stubborn weight"]
    },
    {
        "name": "Metabolic Slowdown",
        "category": "metabolic",
        "products": ["MOTS-c", "SS-31", "CoQ10", "Thyroid Support"],
        "labs": ["Complete Thyroid Panel", "Fasting Insulin", "Lipid Panel"],
        "keywords": ["slow metabolism", "metabolic dysfunction"]
    },
    {
        "name": "High Prolactin",
        "category": "hormonal_general",
        "products": ["Vitex", "Vitamin B6", "Zinc", "DIM"],
        "labs": ["Prolactin", "Female Hormone Panel"],
        "keywords": ["elevated prolactin", "hyperprolactinemia"]
    },

    # === IMG_0882: Cardiovascular & Cognitive ===
    {
        "name": "High SHBG",
        "category": "hormonal_general",
        "products": ["Boron", "Magnesium Glycinate", "Zinc", "Stinging Nettle"],
        "labs": ["SHBG", "Testosterone Panel"],
        "keywords": ["sex hormone binding globulin elevated"]
    },
    {
        "name": "High Homocysteine",
        "category": "cardiovascular",
        "products": ["Methylated B Complex", "B12", "Folate", "NAC"],
        "labs": ["Homocysteine", "B Vitamin Panel", "Methylation Markers"],
        "keywords": ["elevated homocysteine", "methylation issues"]
    },
    {
        "name": "High Uric Acid",
        "category": "metabolic",
        "products": ["Quercetin", "Vitamin C", "Tart Cherry", "NAC"],
        "labs": ["Uric Acid", "Kidney Panel"],
        "keywords": ["gout", "elevated uric acid"]
    },
    {
        "name": "Memory Decline",
        "category": "cognitive",
        "products": ["Lion's Mane", "Semax", "Alpha GPC", "Phosphatidylserine"],
        "labs": ["Cognitive Panel", "B12", "Homocysteine"],
        "keywords": ["memory loss", "forgetfulness", "cognitive decline"]
    },
    {
        "name": "Low Dopamine",
        "category": "mood_mental",
        "products": ["L-Tyrosine", "Phenylalanine", "Mucuna", "Rhodiola"],
        "labs": ["Neurotransmitter Panel", "Dopamine Pathways"],
        "keywords": ["no motivation", "anhedonia", "pleasure deficit"]
    },
    {
        "name": "Motivation Crash",
        "category": "mood_mental",
        "products": ["L-Tyrosine", "Rhodiola", "Semax", "Caffeine"],
        "labs": ["Dopamine Pathways", "Complete Thyroid Panel"],
        "keywords": ["no drive", "unmotivated", "apathy"]
    },
    {
        "name": "Neuroinflammation",
        "category": "cognitive",
        "products": ["Curcumin", "Omega-3s", "Lion's Mane", "NAC"],
        "labs": ["Inflammation Markers", "Cognitive Panel"],
        "keywords": ["brain inflammation", "neural inflammation"]
    },
    {
        "name": "Anxiety",
        "category": "mood_mental",
        "products": ["Selank", "L-Theanine", "Magnesium Glycinate", "GABA"],
        "labs": ["Cortisol Rhythm", "Neurotransmitter Panel"],
        "keywords": ["anxious", "worried", "nervous", "panic"]
    },

    # === IMG_0883: Cognitive ===
    {
        "name": "Mental Fatigue",
        "category": "cognitive",
        "products": ["Rhodiola", "Lion's Mane", "Alpha GPC", "CoQ10"],
        "labs": ["Complete Thyroid Panel", "B Vitamin Panel"],
        "keywords": ["brain tired", "mental exhaustion", "cognitive fatigue"]
    },
    {
        "name": "Cognitive Decline",
        "category": "cognitive",
        "products": ["Semax", "Dihexa", "Lion's Mane", "Omega-3s"],
        "labs": ["Cognitive Panel", "Inflammation Markers", "B12"],
        "keywords": ["declining cognition", "mental decline"]
    },
    {
        "name": "Overthinking",
        "category": "mood_mental",
        "products": ["L-Theanine", "GABA", "Magnesium Threonate", "Selank"],
        "labs": ["Cortisol Rhythm", "Neurotransmitter Panel"],
        "keywords": ["rumination", "racing thoughts", "cant stop thinking"]
    },
    {
        "name": "Racing Thoughts",
        "category": "mood_mental",
        "products": ["L-Theanine", "GABA", "Magnesium Glycinate", "Selank"],
        "labs": ["Cortisol Rhythm", "Complete Thyroid Panel"],
        "keywords": ["mind racing", "thoughts wont stop"]
    },
    {
        "name": "Forgetfulness",
        "category": "cognitive",
        "products": ["Alpha GPC", "Lion's Mane", "Phosphatidylserine", "Bacopa"],
        "labs": ["B12", "Cognitive Panel"],
        "keywords": ["cant remember", "memory problems", "forgetting"]
    },
    {
        "name": "Short-term Memory Trouble",
        "category": "cognitive",
        "products": ["Alpha GPC", "Semax", "Lion's Mane", "Omega-3s"],
        "labs": ["Cognitive Panel", "B12", "Inflammation Markers"],
        "keywords": ["working memory", "immediate memory issues"]
    },

    # === IMG_0884: Emotional & Temperature ===
    {
        "name": "Emotional Numbness",
        "category": "mood_mental",
        "products": ["SAMe", "Omega-3s", "5-HTP", "Rhodiola"],
        "labs": ["Neurotransmitter Panel", "DUTCH Test"],
        "keywords": ["cant feel emotions", "emotional blunting", "numb"]
    },
    {
        "name": "Irritability",
        "category": "mood_mental",
        "products": ["Magnesium Glycinate", "L-Theanine", "Omega-3s", "Ashwagandha"],
        "labs": ["Cortisol Rhythm", "Complete Thyroid Panel", "Iron Panel"],
        "keywords": ["angry", "easily irritated", "short temper"]
    },
    {
        "name": "Sensitivity to Stress",
        "category": "mood_mental",
        "products": ["Ashwagandha", "Selank", "Phosphatidylserine", "L-Theanine"],
        "labs": ["Cortisol Rhythm", "DUTCH Test"],
        "keywords": ["stress intolerance", "overwhelmed easily"]
    },
    {
        "name": "Wired but Tired",
        "category": "sleep",
        "products": ["Phosphatidylserine", "Magnesium Glycinate", "L-Theanine", "Ashwagandha"],
        "labs": ["Cortisol Rhythm", "Cortisol Awakening Response"],
        "keywords": ["tired but cant sleep", "exhausted but wired"]
    },
    {
        "name": "Cold Intolerance",
        "category": "temperature",
        "products": ["Selenium", "Iodine", "Iron Bisglycinate", "CoQ10"],
        "labs": ["Complete Thyroid Panel", "Iron Panel"],
        "keywords": ["always cold", "cold hands feet", "temperature sensitivity"]
    },
    {
        "name": "Hair Thinning",
        "category": "skin_hair",
        "products": ["Biotin", "Iron Bisglycinate", "Zinc", "Collagen"],
        "labs": ["Complete Thyroid Panel", "Iron Panel", "Ferritin"],
        "keywords": ["hair loss", "balding", "thinning hair"]
    },

    # === IMG_0885: Thyroid & Skin ===
    {
        "name": "Hypothyroid Symptoms",
        "category": "thyroid",
        "products": ["Selenium", "Iodine", "Zinc", "Ashwagandha"],
        "labs": ["Complete Thyroid Panel"],
        "keywords": ["underactive thyroid", "low thyroid"]
    },
    {
        "name": "Hashimoto's",
        "category": "thyroid",
        "products": ["Selenium", "NAC", "Vitamin D3", "Omega-3s"],
        "labs": ["Complete Thyroid Panel", "Inflammation Markers"],
        "keywords": ["hashimotos thyroiditis", "autoimmune thyroid"]
    },
    {
        "name": "Brittle Nails",
        "category": "skin_hair",
        "products": ["Biotin", "Collagen", "Silica", "Zinc"],
        "labs": ["Complete Thyroid Panel", "Iron Panel"],
        "keywords": ["weak nails", "breaking nails"]
    },
    {
        "name": "Constipation",
        "category": "gut_digestive",
        "products": ["Magnesium Glycinate", "Probiotics", "Fiber", "Digestive Enzymes"],
        "labs": ["Complete Thyroid Panel", "GI-MAP"],
        "keywords": ["irregular bowels", "cant go", "bowel issues"]
    },
    {
        "name": "Acne Flare Patterns",
        "category": "skin_hair",
        "products": ["DIM", "Zinc", "Probiotics", "Omega-3s"],
        "labs": ["DUTCH Test", "Female Hormone Panel"],
        "keywords": ["hormonal acne", "breakouts", "pimples"]
    },
    {
        "name": "Estrogen Dominance",
        "category": "hormonal_female",
        "products": ["DIM", "I3C", "Calcium D-Glucarate", "Probiotics"],
        "labs": ["DUTCH Test", "Estrogen/Progesterone Rhythm"],
        "keywords": ["high estrogen", "estrogen excess"]
    },

    # === IMG_0886: Female Hormones & Blood Sugar ===
    {
        "name": "Low Progesterone Symptoms",
        "category": "hormonal_female",
        "products": ["Vitex", "Vitamin B6", "Magnesium Glycinate", "Zinc"],
        "labs": ["DUTCH Test", "Female Hormone Panel"],
        "keywords": ["progesterone deficiency", "luteal phase issues"]
    },
    {
        "name": "PCOS Tendencies",
        "category": "hormonal_female",
        "products": ["Inositol", "Berberine", "DIM", "NAC"],
        "labs": ["DUTCH Test", "Fasting Insulin", "Testosterone Panel"],
        "keywords": ["polycystic ovary", "irregular periods"]
    },
    {
        "name": "Insulin Resistance Symptoms",
        "category": "metabolic",
        "products": ["Berberine", "Inositol", "Chromium", "Alpha Lipoic Acid"],
        "labs": ["Fasting Insulin", "HbA1c", "Fasting Glucose"],
        "keywords": ["insulin resistance", "prediabetes"]
    },
    {
        "name": "Blood Sugar Crashes",
        "category": "metabolic",
        "products": ["Berberine", "Chromium", "Cinnamon Extract", "L-Glutamine"],
        "labs": ["Fasting Insulin", "Fasting Glucose"],
        "keywords": ["hypoglycemia", "sugar crashes", "blood sugar swings"]
    },
    {
        "name": "Chronic Bloating After Meals",
        "category": "gut_digestive",
        "products": ["Digestive Enzymes", "Betaine HCL", "Probiotics", "Ginger Extract"],
        "labs": ["GI-MAP", "SIBO Breath Test"],
        "keywords": ["post-meal bloating", "digestive bloating"]
    },
    {
        "name": "Histamine Issues",
        "category": "immune",
        "products": ["DAO Enzyme", "Quercetin", "Vitamin C", "Probiotics"],
        "labs": ["Food Sensitivity Panel", "GI-MAP"],
        "keywords": ["histamine intolerance", "histamine reaction"]
    },

    # === IMG_0887: Pain & Neurological ===
    {
        "name": "Chronic Nausea",
        "category": "gut_digestive",
        "products": ["Ginger Extract", "Digestive Enzymes", "B6", "Probiotics"],
        "labs": ["GI-MAP", "Liver Panel"],
        "keywords": ["always nauseous", "persistent nausea"]
    },
    {
        "name": "Migraines",
        "category": "inflammation_pain",
        "products": ["Magnesium Glycinate", "Riboflavin", "CoQ10", "Omega-3s"],
        "labs": ["Inflammation Markers", "Complete Thyroid Panel"],
        "keywords": ["headaches", "severe headaches", "migraine"]
    },
    {
        "name": "Dizziness",
        "category": "neurological",
        "products": ["Iron Bisglycinate", "B12", "Electrolytes", "CoQ10"],
        "labs": ["Iron Panel", "B12", "CBC"],
        "keywords": ["lightheaded", "vertigo", "unsteady"]
    },
    {
        "name": "POTS Tendencies",
        "category": "neurological",
        "products": ["Electrolytes", "Iron Bisglycinate", "CoQ10", "Vitamin B12"],
        "labs": ["Iron Panel", "CBC", "Aldosterone"],
        "keywords": ["postural tachycardia", "standing dizziness"]
    },
    {
        "name": "Joint Pain",
        "category": "inflammation_pain",
        "products": ["BPC-157", "Curcumin", "Omega-3s", "Collagen"],
        "labs": ["CRP", "ESR", "Uric Acid"],
        "keywords": ["aching joints", "joint inflammation"]
    },
    {
        "name": "Joint Stiffness",
        "category": "inflammation_pain",
        "products": ["Curcumin", "Omega-3s", "Collagen", "BPC-157"],
        "labs": ["Inflammation Markers", "CRP"],
        "keywords": ["stiff joints", "morning stiffness"]
    },

    # === IMG_0888: Neurological & Immune ===
    {
        "name": "Lower Back Tightness",
        "category": "inflammation_pain",
        "products": ["Magnesium Glycinate", "Omega-3s", "BPC-157", "Curcumin"],
        "labs": ["Inflammation Markers", "CRP"],
        "keywords": ["back pain", "tight back", "lumbar pain"]
    },
    {
        "name": "Burning Feet",
        "category": "neurological",
        "products": ["Alpha Lipoic Acid", "Benfotiamine", "Acetyl L-Carnitine", "B Vitamin Panel"],
        "labs": ["B Vitamin Panel", "Fasting Glucose", "HbA1c"],
        "keywords": ["neuropathy", "feet burning", "nerve pain feet"]
    },
    {
        "name": "Numbness or Tingling",
        "category": "neurological",
        "products": ["Methylated B Complex", "Omega-3s", "Lion's Mane", "Alpha Lipoic Acid"],
        "labs": ["Homocysteine", "B12", "B Vitamin Panel"],
        "keywords": ["paresthesia", "pins and needles", "nerve sensations"]
    },
    {
        "name": "Restless Legs",
        "category": "neurological",
        "products": ["Magnesium Glycinate", "Iron Bisglycinate", "CoQ10", "Taurine"],
        "labs": ["Ferritin", "Iron Panel"],
        "keywords": ["RLS", "restless leg syndrome", "leg discomfort"]
    },
    {
        "name": "Low Oxygen Feeling",
        "category": "cardiovascular",
        "products": ["NAC", "CoQ10", "Beet Root", "Iron Bisglycinate"],
        "labs": ["CBC", "Ferritin", "Iron Panel"],
        "keywords": ["shortness of breath", "air hunger", "cant breathe"]
    },
    {
        "name": "Frequent Illness",
        "category": "immune",
        "products": ["Thymosin Alpha-1", "Zinc", "Vitamin C", "Vitamin D3"],
        "labs": ["Immune Cell Differential", "CBC"],
        "keywords": ["always sick", "catching everything", "weak immune"]
    },

    # === IMG_0890: Urinary & Liver ===
    {
        "name": "Yeast Infections",
        "category": "urinary_reproductive",
        "products": ["Caprylic Acid", "Oregano Oil", "Berberine", "Probiotics"],
        "labs": ["GI-MAP Fungal Panel", "Urinalysis"],
        "keywords": ["vaginal yeast", "candida infection"]
    },
    {
        "name": "Urinary Frequency",
        "category": "urinary_reproductive",
        "products": ["D-Mannose", "Cranberry Extract", "Probiotics"],
        "labs": ["Urinalysis", "Urine Culture"],
        "keywords": ["frequent urination", "bladder urgency"]
    },
    {
        "name": "Fatty Liver Patterns",
        "category": "liver_detox",
        "products": ["TUDCA", "Milk Thistle", "NAC", "Berberine"],
        "labs": ["Liver Ultrasound", "ALT/AST", "Liver Panel"],
        "keywords": ["NAFLD", "fatty liver disease"]
    },
    {
        "name": "Bile Sluggishness",
        "category": "liver_detox",
        "products": ["Dandelion", "Bitters", "Taurine", "Phosphatidylcholine"],
        "labs": ["Bile Acids Panel", "Liver Panel"],
        "keywords": ["bile flow", "sluggish bile"]
    },
    {
        "name": "Gallbladder Irritation",
        "category": "liver_detox",
        "products": ["Phosphatidylcholine", "Taurine", "Bitters"],
        "labs": ["Gallbladder Ultrasound", "Bile Acids Panel"],
        "keywords": ["gallbladder pain", "gallbladder issues"]
    },
    {
        "name": "Water Weight Gain",
        "category": "kidney_fluid",
        "products": ["Dandelion", "Potassium Citrate", "Taurine", "Magnesium Glycinate"],
        "labs": ["Aldosterone", "Electrolytes", "Kidney Panel"],
        "keywords": ["fluid gain", "water retention", "bloated"]
    },
    {
        "name": "Puffiness or Swelling",
        "category": "kidney_fluid",
        "products": ["Curcumin", "Omega-3s", "Lymphatic Herbs", "Dandelion"],
        "labs": ["CRP", "ESR", "Kidney Panel"],
        "keywords": ["swollen", "puffy face", "edema"]
    },

    # === IMG_0891: Energy Timing & Cravings ===
    {
        "name": "Hard Time Waking Up",
        "category": "energy_fatigue",
        "products": ["Ashwagandha", "Licorice Root", "Adrenal Cortex", "Rhodiola"],
        "labs": ["Morning Cortisol", "Cortisol Awakening Response"],
        "keywords": ["cant wake up", "morning fatigue", "groggy"]
    },
    {
        "name": "Midday Crash",
        "category": "energy_fatigue",
        "products": ["Rhodiola", "Cordyceps", "Electrolytes", "CoQ10"],
        "labs": ["Cortisol Rhythm", "Fasting Glucose"],
        "keywords": ["afternoon slump", "energy crash", "2pm fatigue"]
    },
    {
        "name": "Evening Wired State",
        "category": "sleep",
        "products": ["Glycine", "Magnesium Threonate", "Phosphatidylserine", "L-Theanine"],
        "labs": ["Cortisol Awakening Response", "Cortisol Rhythm"],
        "keywords": ["wired at night", "cant wind down"]
    },
    {
        "name": "Night Sweats",
        "category": "temperature",
        "products": ["Maca", "DIM", "Magnesium Glycinate", "Sage"],
        "labs": ["DUTCH Test", "Estrogen/Progesterone Rhythm"],
        "keywords": ["sweating at night", "hot flashes night"]
    },
    {
        "name": "Temperature Swings",
        "category": "temperature",
        "products": ["Inositol", "Vitex", "Maca", "Ashwagandha"],
        "labs": ["Estrogen/Progesterone Rhythm", "Complete Thyroid Panel"],
        "keywords": ["hot cold", "temperature regulation"]
    },
    {
        "name": "Salt Cravings",
        "category": "appetite_cravings",
        "products": ["Adrenal Cortex", "Electrolytes", "Vitamin C", "Licorice Root"],
        "labs": ["Morning Cortisol", "Aldosterone"],
        "keywords": ["craving salt", "want salty foods"]
    },
    {
        "name": "Sugar Cravings",
        "category": "appetite_cravings",
        "products": ["Berberine", "Cinnamon Extract", "L-Glutamine", "Chromium"],
        "labs": ["Fasting Insulin", "Fasting Glucose"],
        "keywords": ["craving sugar", "sweet tooth", "want sweets"]
    },

    # === IMG_0892: Appetite & Pain ===
    {
        "name": "High Appetite",
        "category": "appetite_cravings",
        "products": ["5-HTP", "Chromium", "Berberine", "Inositol"],
        "labs": ["Leptin", "Fasting Insulin"],
        "keywords": ["always hungry", "increased appetite", "cant stop eating"]
    },
    {
        "name": "Loss of Appetite",
        "category": "appetite_cravings",
        "products": ["Zinc", "Vitamin B Complex", "Ginger Extract", "Digestive Enzymes"],
        "labs": ["CMP", "GI-MAP"],
        "keywords": ["no appetite", "not hungry", "food aversion"]
    },
    {
        "name": "Frequent Headaches",
        "category": "inflammation_pain",
        "products": ["Magnesium Glycinate", "Riboflavin", "CoQ10", "Omega-3s"],
        "labs": ["Inflammation Markers", "CRP"],
        "keywords": ["regular headaches", "daily headaches"]
    },
    {
        "name": "Chronic Pain",
        "category": "inflammation_pain",
        "products": ["Curcumin", "Omega-3s", "BPC-157", "NAC"],
        "labs": ["CRP", "ESR", "Inflammation Markers"],
        "keywords": ["persistent pain", "ongoing pain"]
    },
    {
        "name": "Fluctuating Energy",
        "category": "energy_fatigue",
        "products": ["Rhodiola", "Cordyceps", "NAD+ IM", "CoQ10"],
        "labs": ["Cortisol Pattern", "Complete Thyroid Panel"],
        "keywords": ["energy ups downs", "inconsistent energy"]
    },
    {
        "name": "Brain Overstimulation",
        "category": "cognitive",
        "products": ["Magnesium Threonate", "Glycine", "Taurine", "L-Theanine"],
        "labs": ["Neurotransmitter Metabolites", "Cortisol Rhythm"],
        "keywords": ["overstimulated", "sensory overload", "overwhelmed brain"]
    },
    {
        "name": "Emotional Overwhelm",
        "category": "mood_mental",
        "products": ["Ashwagandha", "L-Theanine", "Glycine", "Selank"],
        "labs": ["Cortisol Curve", "DUTCH Test"],
        "keywords": ["emotionally overwhelmed", "cant cope"]
    },

    # === IMG_0893: Social & Cognitive ===
    {
        "name": "Social Exhaustion",
        "category": "mood_mental",
        "products": ["Dihexa", "Omega-3s", "SAMe", "Selank"],
        "labs": ["Organic Acids Test", "Neurotransmitter Panel"],
        "keywords": ["drained by socializing", "social fatigue"]
    },
    {
        "name": "Poor Verbal Recall",
        "category": "cognitive",
        "products": ["Alpha GPC", "Uridine Monophosphate", "Semax", "Lion's Mane"],
        "labs": ["Cognitive Panel", "B12"],
        "keywords": ["word finding", "cant remember words", "tip of tongue"]
    },
    {
        "name": "Difficulty Concentrating",
        "category": "cognitive",
        "products": ["L-Tyrosine", "Caffeine", "Huperzine A", "Alpha GPC"],
        "labs": ["Dopamine Pathways", "Complete Thyroid Panel"],
        "keywords": ["cant focus", "concentration problems"]
    },
    {
        "name": "Poor Task Initiation",
        "category": "cognitive",
        "products": ["Dihexa", "Phenylalanine", "Agmatine", "L-Tyrosine"],
        "labs": ["Testosterone Panel", "Dopamine Pathways"],
        "keywords": ["cant start tasks", "procrastination", "executive function"]
    },
    {
        "name": "Chronic Guilt Cycles",
        "category": "mood_mental",
        "products": ["SAMe", "Omega-3s", "Methylated B Complex", "5-HTP"],
        "labs": ["Neurotransmitter Panel", "Methylation Markers"],
        "keywords": ["guilt", "shame", "self-blame"]
    },
]


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================

async def seed_products(db):
    """Seed all products"""
    print("Seeding products...")
    count = 0
    for p in PRODUCTS:
        existing = await db.products.find_one({"name": p["name"]})
        if not existing:
            product = HolisticProduct(
                name=p["name"],
                product_type=ProductType(p["type"]),
                is_peptide=p.get("is_peptide", False),
                description=p.get("description")
            )
            await db.products.insert_one(product.model_dump())
            count += 1
    print(f"  Created {count} new products")


async def seed_labs(db):
    """Seed all lab tests"""
    print("Seeding lab tests...")
    count = 0
    for lab in LAB_TESTS:
        existing = await db.lab_tests.find_one({"name": lab["name"]})
        if not existing:
            lab_test = LabTest(
                name=lab["name"],
                description=lab.get("description")
            )
            await db.lab_tests.insert_one(lab_test.model_dump())
            count += 1
    print(f"  Created {count} new lab tests")


async def seed_symptoms(db):
    """Seed all symptoms with product and lab mappings"""
    print("Seeding symptoms...")
    count = 0
    for s in SYMPTOM_MAPPINGS:
        slug = re.sub(r'[^a-z0-9]+', '-', s["name"].lower()).strip('-')

        existing = await db.symptoms.find_one({"slug": slug})
        if existing:
            continue

        # Get product IDs
        product_ids = []
        for product_name in s.get("products", []):
            product = await db.products.find_one({"name": product_name})
            if product:
                product_ids.append(product["product_id"])

        # Get lab IDs
        lab_ids = []
        for lab_name in s.get("labs", []):
            lab = await db.lab_tests.find_one({"name": lab_name})
            if lab:
                lab_ids.append(lab["test_id"])

        symptom = Symptom(
            name=s["name"],
            slug=slug,
            category=SymptomCategory(s["category"]),
            recommended_products=product_ids,
            recommended_labs=lab_ids,
            keywords=s.get("keywords", [])
        )

        await db.symptoms.insert_one(symptom.model_dump())
        count += 1

    print(f"  Created {count} new symptoms")


async def main():
    """Main seeding function"""
    # Connect to database
    mongo_url = os.getenv("MONGODB_URL", os.getenv("MONGO_PUBLIC_URL", "mongodb://localhost:27017"))
    db_name = os.getenv("MONGODB_DATABASE", "peptide_ai")

    print(f"Connecting to MongoDB at {mongo_url}...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print(f"Using database: {db_name}")
    print()

    # Seed data
    await seed_products(db)
    await seed_labs(db)
    await seed_symptoms(db)

    print()
    print("Seeding complete!")

    # Print stats
    product_count = await db.products.count_documents({})
    lab_count = await db.lab_tests.count_documents({})
    symptom_count = await db.symptoms.count_documents({})

    print(f"  Total products: {product_count}")
    print(f"  Total lab tests: {lab_count}")
    print(f"  Total symptoms: {symptom_count}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
