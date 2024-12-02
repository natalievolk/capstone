import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
import transformers
from sklearn.model_selection import train_test_split
import torch
# import os
# os.environ["CUDA_VISIBLE_DEVICES"] = "1"

# Load the model and tokenizer
print("Loading model ...")

model_id = "meta-llama/Meta-Llama-3.1-8B-Instruct"

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
)

# TODO: try this
# pipeline = transformers.pipeline("text-generation", model="stanford-crfm/BioMedLM", model_kwargs={"torch_dtype": torch.bfloat16}, device_map="auto",)

# Few-shot examples

ex3 = """
Bone Scan(Whole Body)Nuc Med TECHNETIUM MDP BONE SCAN WHOLE BODY:

History:Prostate cancer

Comparison:CT chest, abdomen and pelvis 9/21/10. No previous bone
scans

Findings:Static whole body images show foci of increased activity
in the left glenoid, T11, L2, the left medial iliac bone, the left
proximal femur and the right acetabulum. These findings are in
keeping with bony metastases.

Summary:Bony metastases as described above.

[DEIDENTIFIED - DOCTOR'S INFO]
"""


fracture_examples = f"""
Does this radiology report text indicate fracture? Provide an answer using the example output format below. Make sure to adhere to the strict format one of the two options: "Fracture: Yes", "Fracture: No".

If a report is amgibuous about whether there is a fracture, default to "No" for that category.

- Example Input: "PROVIDED HISTORY: "NONE, Prostate ca. follow-up after SBRT to oligomets ???Please do RECIST 1.1 and PCWG3 for PR.20 study (TIMEPOINT-4FINDINGS: Skeletal phase whole body planar and tomographic imaging of the thorax/abdomen/pelvis/proximal femurs demonstrate stable scislightly less conspicuous tracer activity within the mid thoracic spine. Otherwise, there is no scintigraphic abnormality suspicious ocorresponding to insufficiency fractures on recent MRI. There is degenerative-appearing uptake within the left lower cervical spine, s[DEIDENTIFIED - DOCTOR'S INFO]ence for disease progression as per PCWG-3."
- Example Output: "Fracture: Yes"

Does this radiology report text indicate fracture?
- Example Input: "Provided History: "T2b (MR nodule centrally 1.7cm) G6 19.6 DT1.6y velocity 7.2 /yr. Pt on Abiraterone+/-Ipateserib. Please compare ALLFindings: Angiographic and tissue phase imaging of the torso is unremarkable. Skeletal phase whole body planar images and SPECT of thedegenerative-appearing uptake within the right a.c. joint, right L4/L5 facet joint, knees and forefeet. Stable mild diffuse tracer act[DEIDENTIFIED - DOCTOR'S INFO]ence for bony metastatic disease.remote trauma."
- Example Output: "Fracture: No"

Does this radiology report text indicate fracture?
- Example Input: "{ex3}"
- Example Output: "Fracture: No"
"""


metastases_examples = f"""
Does this radiology report text indicate metastases? Provide an answer using the example output format below. Make sure to adhere to the strict format one of the two options: "Metastases: Yes", "Metastases: No".

If a report is amgibuous about whether there is a metastases, default to "No".

- Example Input: "PROVIDED HISTORY: "NONE, Prostate ca. follow-up after SBRT to oligomets ???Please do RECIST 1.1 and PCWG3 for PR.20 study (TIMEPOINT-4FINDINGS: Skeletal phase whole body planar and tomographic imaging of the thorax/abdomen/pelvis/proximal femurs demonstrate stable scislightly less conspicuous tracer activity within the mid thoracic spine. Otherwise, there is no scintigraphic abnormality suspicious ocorresponding to insufficiency fractures on recent MRI. There is degenerative-appearing uptake within the left lower cervical spine, s[DEIDENTIFIED - DOCTOR'S INFO]ence for disease progression as per PCWG-3."
- Example Output: "Metastases: Yes"

Does this radiology report text indicate metastases?
- Example Input: "Provided History: "T2b (MR nodule centrally 1.7cm) G6 19.6 DT1.6y velocity 7.2 /yr. Pt on Abiraterone+/-Ipateserib. Please compare ALLFindings: Angiographic and tissue phase imaging of the torso is unremarkable. Skeletal phase whole body planar images and SPECT of thedegenerative-appearing uptake within the right a.c. joint, right L4/L5 facet joint, knees and forefeet. Stable mild diffuse tracer act[DEIDENTIFIED - DOCTOR'S INFO]ence for bony metastatic disease.remote trauma."
- Example Output: "Metastases: No,"

Does this radiology report text indicate metastases?
- Example Input: "{ex3}"
- Example Output: "Metastases: Yes"
"""

# Define prediction function
def predict_label_lama(report):
    frac_prompt = fracture_examples + f'- Final Input: "{report}"\n- Final Output: '
    met_prompt = metastases_examples + f'- Final Input: "{report}"\n- Final Output: '
    res = []
    for prompt in [frac_prompt, met_prompt]:
        messages = [
            {"role": "system", "content": "You are an intelligent assistant who's tasked with identifying whether a radiology report describes a paitient with fractures and/or metastases."},
            {"role": "user", "content": prompt},
        ]

        outputs = pipeline(
            messages,
            max_new_tokens=2048,
        )

        response = outputs[0]["generated_text"][-1]

        processed_response = response["content"].split("Final Output: ")[-1]
        print("Processed response:", processed_response)
        # TODO: regex process the response to ensure it aligns with the requested format
        # assert "Metastases" in processed_response or "Fracture" in processed_response


        if "Metastases" in processed_response:
            if "Yes" in processed_response:
                res.append(1)
            elif "No" in processed_response:
                res.append(0)
            else:
                res.append(-1)
        elif "Fracture" in processed_response:
            if "Yes" in processed_response:
                res.append(1)
            elif "No" in processed_response:
                res.append(0)
            else:
                res.append(-1)
        else:
            res.append(-1)

    return res

# Load labeled data
print("Loading labeled data...")
grouped_reports = pd.read_csv('labeled_data.csv')  # Replace with the correct path
texts = grouped_reports['reports'].tolist()
labels = grouped_reports[['image_ct___1', 'image_ct___2']].astype(int).values.tolist()

# Split into train/test sets (optional, if not already split)
train_texts, test_texts, train_labels, test_labels = train_test_split(
    texts, labels, test_size=0.2, random_state=42
)

# use the first train data text and the second train data text for the instructions
example1 = train_texts[0]
example1_label = train_labels[0]

example2 = train_texts[1]
example2_label = train_labels[1]




# Generate predictions for the test set
print("Generating predictions...")
predictions = []
true_labels = []

print("Total examples:", len(test_texts))
i = 0
for report, label in zip(test_texts, test_labels):
    if i < 10:
        i += 1
        continue
    print("Prediction: " + str(i))
    prediction = predict_label_lama(report)
    predictions.append(prediction)
    true_labels.append(label)
    print("\nPredictions: " + str(predictions))
    print("\nTrue labels: " + str(true_labels))
    i = i + 1

# Convert lists to arrays
predictions = np.array(predictions)
true_labels = np.array(true_labels)

# Filter out invalid predictions (-1)
valid_indices = predictions != -1
valid_predictions = predictions[valid_indices]
valid_true_labels = true_labels[valid_indices]

# Evaluate metrics
print("Evaluating performance...")
accuracy = accuracy_score(valid_true_labels, valid_predictions)
f1 = f1_score(valid_true_labels, valid_predictions, average="binary")  # Adjust as needed

# Per-label accuracy
unique_labels = np.unique(valid_true_labels)
per_label_accuracy = {
    label: accuracy_score(
        valid_true_labels[valid_true_labels == label],
        valid_predictions[valid_true_labels == label],
    )
    for label in unique_labels
}

# Print results
print(f"Overall Accuracy: {accuracy:.4f}")
print(f"F1 Score: {f1:.4f}")
for label, acc in per_label_accuracy.items():
    label_name = "Metastases" if label == 1 else "Fracture"
    print(f"Accuracy for {label_name}: {acc:.4f}")