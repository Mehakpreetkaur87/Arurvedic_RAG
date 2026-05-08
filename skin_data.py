import gradio as gr
import json

print("Starting Dermatology Gradio App...")

# =========================================================
# OPTIONS
# =========================================================

AGE_OPTIONS = [
    "neonate",
    "infant",
    "child",
    "adolescent",
    "adult",
    "middle_aged",
    "elderly"
]

SEX_OPTIONS = [
    "male",
    "female",
    "other"
]

SKIN_TYPE_OPTIONS = [
    "fst1",
    "fst2",
    "fst3",
    "fst4",
    "fst5",
    "fst6",
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
    "acute",
    "chronic",
    "subacute",
    "days",
    "weeks",
    "months",
    "years",
    "lifelong",
    "sudden_onset",
    "gradual_onset",
    "recurrent",
    "persistent",
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

LESION_COUNT_OPTIONS = [
    "single",
    "few",
    "multiple",
    "numerous",
    "scattered",
    "generalized"
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
    "life_threatening",
    "quality_of_life_impact"
]

IMAGE_OPTIONS = [
    "clinical_image",
    "dermoscopy",
    "close_up",
    "macro",
    "microscopic",
    "clear",
    "blurry",
    "well_lit",
    "poor_lighting"
]

# =========================================================
# VISIBILITY FUNCTIONS
# =========================================================

def show_treatment_questions(choice):
    if choice == "yes":
        return gr.update(visible=True)
    return gr.update(visible=False)


def show_systemic_questions(choice):
    if choice == "yes":
        return gr.update(visible=True)
    return gr.update(visible=False)


def show_secondary_questions(choice):
    if choice == "yes":
        return gr.update(visible=True)
    return gr.update(visible=False)


# =========================================================
# SUBMIT FUNCTION
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

    image_metadata,
    image,

    additional_notes
):

    data = {
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
        "symptoms_systemic": systemic_symptoms if systemic_yesno == "yes" else [],

        "duration": duration,
        "triggers": triggers,

        "treatment_taken": treatment_yesno,
        "treatments": treatments if treatment_yesno == "yes" else [],
        "treatment_notes": treatment_notes if treatment_yesno == "yes" else "",

        "clinical_signs": clinical_signs,

        "history_options": history_options,
        "history_text": history_text,

        "secondary_changes_present": secondary_yesno,
        "secondary_changes": secondary_changes if secondary_yesno == "yes" else [],

        "severity": severity,

        "image_metadata": image_metadata,

        "uploaded_image_path": image,

        "additional_notes": additional_notes
    }

    # Save JSON
    with open("patient_data.json", "w") as f:
        json.dump(data, f, indent=4)

    return data


# =========================================================
# UI
# =========================================================

with gr.Blocks(title="Dermatology Intake Form") as demo:

    gr.Markdown("# Dermatology Clinical Intake Form")

    # -----------------------------------------------------
    # DEMOGRAPHICS
    # -----------------------------------------------------

    gr.Markdown("## Demographics")

    age = gr.Dropdown(
        AGE_OPTIONS,
        label="What is your age?"
    )

    sex = gr.Radio(
        SEX_OPTIONS,
        label="What is your sex?"
    )

    skin_type = gr.Dropdown(
        SKIN_TYPE_OPTIONS,
        label="Skin Type"
    )

    ethnicity = gr.CheckboxGroup(
        ETHNICITY_OPTIONS,
        label="Ethnicity"
    )

    # -----------------------------------------------------
    # LESION DETAILS
    # -----------------------------------------------------

    gr.Markdown("## Lesion Details")

    texture = gr.CheckboxGroup(
        TEXTURE_OPTIONS,
        label="Texture / Surface"
    )

    color = gr.CheckboxGroup(
        COLOR_OPTIONS,
        label="Color"
    )

    shape = gr.CheckboxGroup(
        SHAPE_OPTIONS,
        label="Shape / Border"
    )

    distribution = gr.CheckboxGroup(
        DISTRIBUTION_OPTIONS,
        label="Distribution"
    )

    body_location = gr.CheckboxGroup(
        BODY_LOCATION_OPTIONS,
        label="Body Location"
    )

    lesion_count = gr.Radio(
        LESION_COUNT_OPTIONS,
        label="Lesion Count"
    )

    # -----------------------------------------------------
    # SYMPTOMS
    # -----------------------------------------------------

    gr.Markdown("## Symptoms")

    derm_symptoms = gr.CheckboxGroup(
        DERM_SYMPTOM_OPTIONS,
        label="Dermatological Symptoms"
    )

    # Systemic Symptoms YES/NO
    systemic_yesno = gr.Radio(
        ["yes", "no"],
        label="Do you have any whole-body symptoms alongside the rash?"
    )

    with gr.Column(visible=False) as systemic_box:

        systemic_symptoms = gr.CheckboxGroup(
            SYSTEMIC_OPTIONS,
            label="Select Systemic Symptoms"
        )

    systemic_yesno.change(
        show_systemic_questions,
        inputs=systemic_yesno,
        outputs=systemic_box
    )

    # -----------------------------------------------------
    # DURATION
    # -----------------------------------------------------

    gr.Markdown("## Duration")

    duration = gr.CheckboxGroup(
        DURATION_OPTIONS,
        label="Duration and Onset"
    )

    # -----------------------------------------------------
    # TRIGGERS
    # -----------------------------------------------------

    gr.Markdown("## Triggers")

    triggers = gr.CheckboxGroup(
        TRIGGER_OPTIONS,
        label="Triggers"
    )

    # -----------------------------------------------------
    # TREATMENT
    # -----------------------------------------------------

    gr.Markdown("## Treatment History")

    treatment_yesno = gr.Radio(
        ["yes", "no"],
        label="Have you taken any treatment?"
    )

    with gr.Column(visible=False) as treatment_box:

        treatments = gr.CheckboxGroup(
            TREATMENT_OPTIONS,
            label="Treatments Taken"
        )

        treatment_notes = gr.Textbox(
            lines=4,
            label="Enter Treatment Details"
        )

    treatment_yesno.change(
        show_treatment_questions,
        inputs=treatment_yesno,
        outputs=treatment_box
    )

    # -----------------------------------------------------
    # CLINICAL SIGNS
    # -----------------------------------------------------

    gr.Markdown("## Clinical Signs")

    clinical_signs = gr.CheckboxGroup(
        CLINICAL_SIGN_OPTIONS,
        label="Clinical Signs"
    )

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    gr.Markdown("## Medical History")

    history_options = gr.CheckboxGroup(
        HISTORY_OPTIONS,
        label="Select Medical History"
    )

    history_text = gr.Textbox(
        lines=5,
        label="Describe Medical History"
    )

    # -----------------------------------------------------
    # SECONDARY CHANGES
    # -----------------------------------------------------

    gr.Markdown("## Secondary Changes")

    secondary_yesno = gr.Radio(
        ["yes", "no"],
        label="Any secondary changes you've noticed in the skin?"
    )

    with gr.Column(visible=False) as secondary_box:

        secondary_changes = gr.CheckboxGroup(
            SECONDARY_OPTIONS,
            label="Select Secondary Changes"
        )

    secondary_yesno.change(
        show_secondary_questions,
        inputs=secondary_yesno,
        outputs=secondary_box
    )

    # -----------------------------------------------------
    # SEVERITY
    # -----------------------------------------------------

    gr.Markdown("## Severity")

    severity = gr.Radio(
        SEVERITY_OPTIONS,
        label="Severity"
    )

    # -----------------------------------------------------
    # IMAGE
    # -----------------------------------------------------

    gr.Markdown("## Upload Image")

    image_metadata = gr.CheckboxGroup(
        IMAGE_OPTIONS,
        label="Image Metadata"
    )

    image = gr.Image(
        type="filepath",
        label="Upload Lesion Image"
    )

    # -----------------------------------------------------
    # OTHER NOTES
    # -----------------------------------------------------

    additional_notes = gr.Textbox(
        lines=5,
        label="Anything Else We Should Know?"
    )

    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------

    output = gr.JSON(label="Collected Patient Data")

    submit_btn = gr.Button("Submit")

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

            image_metadata,
            image,

            additional_notes
        ],
        outputs=output
    )

print("Launching Gradio App...")

demo.launch(
    debug=True,
    share=False
)