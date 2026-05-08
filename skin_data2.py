import gradio as gr
import json
import os
from datetime import datetime

print("Starting Dermatology Intake Form...")

# =========================================================
# OPTIONS
# =========================================================

SEX_OPTIONS = [
    "male",
    "female",
    "other"
]

SKIN_TYPE_OPTIONS = [
    "fair",
    "medium",
    "olive",
    "dark",
    "deeply_pigmented"
]

ETHNICITY_OPTIONS = [
    "caucasian",
    "african_american",
    "asian",
    "hispanic",
    "south_asian",
    "middle_eastern",
    "indigenous",
    "mixed",
    "other"
]

TEXTURE_OPTIONS = [
    "raised",
    "papule",
    "plaque",
    "nodule",
    "wart",
    "flat",
    "macule",
    "patch",
    "rough",
    "scaly",
    "flaky",
    "vesicle",
    "blister",
    "pustule",
    "ulcer",
    "erosion",
    "crusted",
    "smooth",
    "shiny",
    "cyst",
    "abscess",
    "scar",
    "atrophy"
]

COLOR_OPTIONS = [
    "red",
    "erythematous",
    "pink",
    "purple",
    "brown",
    "hyperpigmented",
    "hypopigmented",
    "white",
    "depigmented",
    "yellow",
    "black",
    "blue",
    "grey",
    "skin_colored"
]

SHAPE_OPTIONS = [
    "round",
    "oval",
    "circular",
    "irregular",
    "annular",
    "linear",
    "serpiginous",
    "well_defined",
    "ill_defined",
    "small",
    "medium",
    "large"
]

DISTRIBUTION_OPTIONS = [
    "unilateral",
    "bilateral",
    "symmetric",
    "asymmetric",
    "grouped",
    "clustered",
    "dermatomal",
    "linear",
    "localized",
    "widespread",
    "generalized"
]

BODY_LOCATION_OPTIONS = [
    "face",
    "cheek",
    "forehead",
    "nose",
    "eyelid",
    "lip",
    "scalp",
    "hairline",
    "ear",
    "neck",
    "chest",
    "abdomen",
    "back",
    "arm",
    "hand",
    "finger",
    "leg",
    "thigh",
    "knee",
    "ankle",
    "foot",
    "toe",
    "groin",
    "genitalia",
    "buttocks",
    "axilla"
]

LESION_COUNT_OPTIONS = [
    "single",
    "few",
    "multiple",
    "numerous"
]

DERM_SYMPTOM_OPTIONS = [
    "itching",
    "burning",
    "stinging",
    "pain",
    "tenderness",
    "soreness",
    "increasing_size",
    "spreading",
    "darkening",
    "bleeding",
    "cosmetic_concern",
    "tingling"
]

SYSTEMIC_OPTIONS = [
    "fever",
    "chills",
    "fatigue",
    "malaise",
    "weight_loss",
    "joint_pain",
    "mouth_sores",
    "shortness_of_breath",
    "lymphadenopathy"
]

DURATION_OPTIONS = [
    "hours",
    "days",
    "weeks",
    "months",
    "years",
    "recurrent",
    "sudden_onset",
    "gradual_onset",
    "intermittent"
]

TRIGGER_OPTIONS = [
    "sun_exposure",
    "heat",
    "cold",
    "sweating",
    "humidity",
    "allergens",
    "chemicals",
    "cosmetics",
    "drug_reaction",
    "infection",
    "virus",
    "fungus",
    "stress",
    "pregnancy",
    "diet",
    "friction"
]

TREATMENT_OPTIONS = [
    "topical_steroids",
    "corticosteroids",
    "emollients",
    "moisturizers",
    "oral_steroids",
    "antibiotics",
    "antifungals",
    "antihistamines",
    "immunosuppressants",
    "biologics",
    "retinoids",
    "phototherapy",
    "laser_therapy",
    "surgery",
    "cryotherapy",
    "home_remedies",
    "wound_care"
]

CLINICAL_SIGN_OPTIONS = [
    "nikolsky_sign",
    "auspitz_sign",
    "koebner_phenomenon",
    "darier_sign",
    "wickham_striae",
    "target_lesions",
    "pathergy",
    "biopsy_proven"
]

HISTORY_OPTIONS = [
    "family_history",
    "genetic_predisposition",
    "atopy",
    "allergies",
    "asthma",
    "recurrence",
    "previous_episodes",
    "immunocompromised",
    "diabetes",
    "autoimmune",
    "smoking",
    "travel_history"
]

SECONDARY_OPTIONS = [
    "lichenification",
    "thickening",
    "atrophy",
    "excoriation",
    "scratch_marks",
    "crusting",
    "fissuring",
    "maceration",
    "post_inflammatory_hyperpigmentation",
    "post_inflammatory_hypopigmentation",
    "scarring",
    "keloid"
]

SEVERITY_OPTIONS = [
    "mild",
    "moderate",
    "severe",
    "very_severe",
    "quality_of_life_impact"
]

# =========================================================
# SHOW / HIDE FUNCTIONS
# =========================================================

def toggle_systemic(choice):
    return gr.update(visible=(choice == "Yes"))


def toggle_treatment(choice):
    return gr.update(visible=(choice == "Yes"))


def toggle_secondary(choice):
    return gr.update(visible=(choice == "Yes"))


# =========================================================
# SAVE FUNCTION
# =========================================================

def submit_form(
    age,
    sex,
    skin_type,
    ethnicity,
    texture,
    color,
    shape,
    distribution,
    body_location,
    lesion_count,
    derm_symptoms,

    systemic_yesno,
    systemic_symptoms,

    duration,
    triggers,

    treatment_yesno,
    treatments,
    treatment_notes,

    clinical_signs,

    history_options,
    history_text,

    secondary_yesno,
    secondary_changes,

    severity,
    uploaded_image,
    additional_notes
):

    data = {
        "timestamp": str(datetime.now()),

        "demographics_age": age,
        "demographics_sex": sex,
        "demographics_skin_type": skin_type,
        "demographics_ethnicity": ethnicity,

        "morphology_texture": texture,
        "morphology_color": color,
        "morphology_shape": shape,
        "morphology_distribution": distribution,

        "body_location": body_location,
        "lesion_count": lesion_count,

        "symptoms_dermatological": derm_symptoms,

        "symptoms_systemic_present": systemic_yesno,
        "symptoms_systemic": systemic_symptoms if systemic_yesno == "Yes" else [],

        "duration": duration,
        "triggers": triggers,

        "treatment_taken": treatment_yesno,
        "treatments": treatments if treatment_yesno == "Yes" else [],
        "treatment_notes": treatment_notes if treatment_yesno == "Yes" else "",

        "clinical_signs": clinical_signs,

        "history_options": history_options,
        "history_text": history_text,

        "secondary_changes_present": secondary_yesno,
        "secondary_changes": secondary_changes if secondary_yesno == "Yes" else [],

        "severity": severity,

        "other_notes": additional_notes,


        "uploaded_image": uploaded_image
    }

    # Create folder if not exists
    os.makedirs("responses", exist_ok=True)

    # Save unique JSON file
    filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"

    filepath = os.path.join("responses", filename)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

    return data


# =========================================================
# UI
# =========================================================

with gr.Blocks(title="Dermatology Intake Form") as demo:

    gr.Markdown("# Dermatology Clinical Intake Form")

    gr.Markdown(
        """
        Please answer the following questions carefully.  
        These questions help collect skin-related clinical information.
        """
    )

    # =====================================================
    # DEMOGRAPHICS
    # =====================================================

    gr.Markdown("## 1. What is your age?")
    gr.Markdown(
        "Enter your age in years. Age should be between 0 and 100."
    )

    age = gr.Slider(
        minimum=0,
        maximum=100,
        step=1,
        label="Age"
    )

    # -----------------------------------------------------

    gr.Markdown("## 2. What is your sex?")
    gr.Markdown(
        "Select the biological sex that best describes you."
    )

    sex = gr.Radio(
        SEX_OPTIONS,
        label="Sex"
    )

    # -----------------------------------------------------

    gr.Markdown("## 3. How does your skin react to 30 minutes of midday sun?")
    gr.Markdown(
        "Choose the option that best describes your natural skin tone and sun sensitivity."
    )

    skin_type = gr.Radio(
        SKIN_TYPE_OPTIONS,
        label="Skin Type"
    )

    # -----------------------------------------------------

    gr.Markdown("## 4. What is your ethnic background? (Optional)")
    gr.Markdown(
        "This information may help understand certain skin conditions better."
    )

    ethnicity = gr.CheckboxGroup(
        ETHNICITY_OPTIONS,
        label="Ethnicity"
    )

    # =====================================================
    # LESION DETAILS
    # =====================================================

    gr.Markdown("## 5. How would you describe the surface and texture?")
    gr.Markdown(
        "Select all options that describe the skin lesion surface."
    )

    texture = gr.CheckboxGroup(
        TEXTURE_OPTIONS,
        label="Surface and Texture"
    )

    # -----------------------------------------------------

    gr.Markdown("## 6. What colour(s) does the affected skin appear?")
    gr.Markdown(
        "Select the colors that best describe the affected area."
    )

    color = gr.CheckboxGroup(
        COLOR_OPTIONS,
        label="Skin Color"
    )

    # -----------------------------------------------------

    gr.Markdown("## 7. What shape, edges, and size are the lesions?")
    gr.Markdown(
        "Describe the lesion shape, borders, and approximate size."
    )

    shape = gr.CheckboxGroup(
        SHAPE_OPTIONS,
        label="Shape and Borders"
    )

    # -----------------------------------------------------

    gr.Markdown("## 8. How are the spots distributed across your body?")
    gr.Markdown(
        "Choose how the lesions are spread or arranged."
    )

    distribution = gr.CheckboxGroup(
        DISTRIBUTION_OPTIONS,
        label="Distribution Pattern"
    )

    # -----------------------------------------------------

    gr.Markdown("## 9. Where on your body are the lesions?")
    gr.Markdown(
        "Select all body areas where the lesions are present."
    )

    body_location = gr.CheckboxGroup(
        BODY_LOCATION_OPTIONS,
        label="Body Location"
    )

    # -----------------------------------------------------

    gr.Markdown("## 10. How many spots or lesions do you have in total?")
    gr.Markdown(
        "Estimate the total number of lesions visible on the body."
    )

    lesion_count = gr.Radio(
        LESION_COUNT_OPTIONS,
        label="Lesion Count"
    )

    # =====================================================
    # SYMPTOMS
    # =====================================================

    gr.Markdown("## 11. What sensations do you feel in the affected area?")
    gr.Markdown(
        "Select all symptoms you experience in the affected skin."
    )

    derm_symptoms = gr.CheckboxGroup(
        DERM_SYMPTOM_OPTIONS,
        label="Skin Symptoms"
    )

    # -----------------------------------------------------

    gr.Markdown("## 12. Do you have any whole-body symptoms alongside the rash?")
    gr.Markdown(
        "Examples include fever, tiredness, joint pain, or weight loss."
    )

    systemic_yesno = gr.Radio(
        ["Yes", "No"],
        label="Systemic Symptoms Present?"
    )

    with gr.Column(visible=False) as systemic_box:

        systemic_symptoms = gr.CheckboxGroup(
            SYSTEMIC_OPTIONS,
            label="Select Systemic Symptoms"
        )

    systemic_yesno.change(
        toggle_systemic,
        inputs=systemic_yesno,
        outputs=systemic_box
    )

    # =====================================================
    # DURATION
    # =====================================================

    gr.Markdown("## 13. How long have you had this, and how did it start?")
    gr.Markdown(
        "Select duration and how the condition started."
    )

    duration = gr.CheckboxGroup(
        DURATION_OPTIONS,
        label="Duration"
    )

    # =====================================================
    # TRIGGERS
    # =====================================================

    gr.Markdown("## 14. Have you noticed anything that triggers or worsens it?")
    gr.Markdown(
        "Select factors that make the condition worse."
    )

    triggers = gr.CheckboxGroup(
        TRIGGER_OPTIONS,
        label="Triggers"
    )

    # =====================================================
    # TREATMENTS
    # =====================================================

    gr.Markdown("## 15. What treatments have you tried, and did they help?")
    gr.Markdown(
        "Select Yes if you have used any treatment previously."
    )

    treatment_yesno = gr.Radio(
        ["Yes", "No"],
        label="Any Previous Treatment?"
    )

    with gr.Column(visible=False) as treatment_box:

        treatments = gr.CheckboxGroup(
            TREATMENT_OPTIONS,
            label="Treatments Used"
        )

        treatment_notes = gr.Textbox(
            lines=4,
            label="Describe Treatment Response"
        )

    treatment_yesno.change(
        toggle_treatment,
        inputs=treatment_yesno,
        outputs=treatment_box
    )

    # =====================================================
    # CLINICAL SIGNS
    # =====================================================

    gr.Markdown("## 16. Have you noticed any of these distinctive behaviours?")
    gr.Markdown(
        "These are specific skin findings sometimes noticed by doctors or patients."
    )

    clinical_signs = gr.CheckboxGroup(
        CLINICAL_SIGN_OPTIONS,
        label="Clinical Signs"
    )

    # =====================================================
    # HISTORY
    # =====================================================

    gr.Markdown("## 17. Personal or family medical history")
    gr.Markdown(
        "Include allergies, asthma, autoimmune disease, diabetes, or similar conditions."
    )

    history_options = gr.CheckboxGroup(
        HISTORY_OPTIONS,
        label="Medical History"
    )

    history_text = gr.Textbox(
        lines=5,
        label="Describe Medical History"
    )

    # =====================================================
    # SECONDARY CHANGES
    # =====================================================

    gr.Markdown("## 18. Any secondary changes you've noticed in the skin?")
    gr.Markdown(
        "Examples include scarring, crusting, thickening, or pigmentation changes."
    )

    secondary_yesno = gr.Radio(
        ["Yes", "No"],
        label="Secondary Skin Changes Present?"
    )

    with gr.Column(visible=False) as secondary_box:

        secondary_changes = gr.CheckboxGroup(
            SECONDARY_OPTIONS,
            label="Secondary Changes"
        )

    secondary_yesno.change(
        toggle_secondary,
        inputs=secondary_yesno,
        outputs=secondary_box
    )

    # =====================================================
    # SEVERITY
    # =====================================================

    gr.Markdown("## 19. How much does this condition affect your daily life?")
    gr.Markdown(
        "Choose the severity level that best matches your condition."
    )

    severity = gr.Radio(
        SEVERITY_OPTIONS,
        label="Severity"
    )

    # =====================================================
    # OTHER
    # =====================================================

    gr.Markdown("## 20. Anything else we should know?")
    gr.Markdown(
        "Add any additional details that may help understand your condition better."
    )

    additional_notes = gr.Textbox(
        lines=5,
        label="Additional Notes"
    )

    # =====================================================
    # IMAGE UPLOAD
    # =====================================================

    gr.Markdown("## 21. Upload a clinical photograph of the lesion")

    gr.Markdown(
        """
        Please upload a clear image of the affected skin area.
        
        Tips:
        - Use good lighting
        - Keep the lesion clearly visible
        - Avoid blurry images
        """
    )

    uploaded_image = gr.Image(
        type="filepath",
        label="Upload Skin Lesion Image"
    )

    # =====================================================
    # OUTPUT
    # =====================================================

    output = gr.JSON(label="Collected Patient Response")

    submit_btn = gr.Button("Submit Form")

    submit_btn.click(
        submit_form,
        inputs=[
            age,
            sex,
            skin_type,
            ethnicity,
            texture,
            color,
            shape,
            distribution,
            body_location,
            lesion_count,
            derm_symptoms,

            systemic_yesno,
            systemic_symptoms,

            duration,
            triggers,

            treatment_yesno,
            treatments,
            treatment_notes,

            clinical_signs,

            history_options,
            history_text,

            secondary_yesno,
            secondary_changes,

            severity,
            uploaded_image,

            additional_notes,
           
           
        ],
        outputs=output
    )

print("Launching Gradio App...")

demo.launch(
    server_name="0.0.0.0",
    server_port=8003,
    debug=True
)