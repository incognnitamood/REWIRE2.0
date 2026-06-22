System Role & Objective You are an expert full-stack AI coding assistant. We are building a computational drug repurposing web application. Our architecture consists of a backend API (handling the data and mathematical models) and a modern frontend (React/Vite) for data visualization.

Your objective is to implement four core features that explain and validate our drug predictions. These features must be built cleanly into our existing tech stack.

Please read the requirements for all four features below, then propose an implementation plan before writing the code.

Feature 1: Edge Weight Attenuation View (Network Perturbation)
Objective: Visualize exactly how a specific drug alters the underlying biological network by weakening connections (edges) around its target proteins.

Backend Requirements:

Data Sources: You need access to the base biological network (nodes = proteins, edges = interactions with weights) and a mapping of Drug -> Target Proteins -> Binding Affinity (nM).
Mathematical Logic:
When a drug is selected, identify its target proteins.
Calculate the binding inhibition for each target based on affinity. Example formula: binding_inhibition = 1.0 / (1.0 + affinity_nM). (If affinity is unknown, default to 0.5).
Find all edges connected to these target proteins.
Calculate the attenuated weight: New Weight = Original Weight * (1 - binding_inhibition).
Calculate the % Change between the New Weight and Original Weight.
Endpoint: Create an API endpoint that receives a drug name and returns a list of the Top 20 edges with the most significant negative % change.
Frontend Requirements (React):

Build a clean data table component.
Columns should include: Protein A, Protein B, Original Weight, New Weight, and % Change.
Style the % Change column text in red (e.g., -54.94%) to clearly indicate the attenuation/weakening of the biological connection.
Feature 2: Chemical Composition & Structural Similarity View
Objective: Display a drug's structural profile and compare its chemical makeup against disease profiles and other known drugs.

Backend Requirements:

Data Sources: A dataset containing drug chemical properties: SMILES strings (or image URLs), Drug Class, Scaffold Family, and a list of Functional Groups.
Similarity Logic (Jaccard): Create a function that calculates the structural similarity between the selected drug and all other drugs in the database using the Jaccard similarity of their Functional Groups. Return the Top 5 most similar drugs.
Disease Profile Scoring: Calculate a score representing how well the selected drug's functional groups match the "typical" chemical profile of drugs known to treat specific diseases.
Endpoint: Create an API endpoint returning the drug's properties, its Top 5 structurally similar drugs (with scores), and its Disease Profile scores.
Frontend Requirements (React):

2D Molecular Structure: Create a card to display the 2D molecule image (you can use an external service like PubChem or RDKit to render SMILES to an image).
Metadata Badges: Display the Drug Class and Scaffold Family as text, and map the Functional Groups into stylized, color-coded pill badges/tags.
Disease Similarity Chart: Build a section using a charting library (like Recharts) or custom HTML/CSS horizontal progress bars to show the drug's "Composition Similarity to Disease Pathway Profiles" across different diseases.
Similar Drugs List: A clean list/table displaying the Top 5 structurally similar drugs, their drug class, and their Jaccard similarity score.
Feature 3: On-the-Fly Drug Inference
Objective: Allow users to search for a drug that is not in our pre-computed database and evaluate it live.

Backend Requirements:

Dynamic Lookup: Create an endpoint that takes a drug name. If it's not in the database, fetch its necessary input features (e.g., target genes) from an external API (like DrugBank or ChEMBL) or a local fallback table.
Live Execution: Pass these dynamically fetched features into our core prediction pipeline and run the mathematical scoring live.
Volatile State: Return the computed relevance score, but do NOT save this permanently to the database unless specifically prompted later.
Frontend Requirements (React):

Add a global search bar.
When searching, show a prominent loading spinner/skeleton UI with text: "Computing relevance for [drug]... this may take a moment."
Render the computed scores once returned.
If the backend cannot find target data, show a graceful error: "Insufficient target/chemical data available for [drug name] — computational relevance cannot be evaluated."
Feature 4: Clinical Verification Panel (Comparative Analysis)
Objective: Prove that our computational model makes biological sense by showing how often it independently rediscovers real, clinically approved treatments.

Backend Requirements:

Ground Truth Data: Ensure we have a dataset mapping Disease -> Real-World Drugs -> Evidence Level (e.g., "Approved", "Phase II Trial").
Endpoint: Create an endpoint for a specific disease that returns two lists: (A) The known clinical treatments from the ground truth data, and (B) Our model's Top 10 computed drug rankings.
Frontend Requirements (React):

Side-by-Side UI: Build a split-view or comparison table component.
Left side: "Currently used clinically" (showing the ground truth drugs and their evidence badges).
Right side: "Computed ranking" (showing our model's top 10 predictions and scores).
Overlap Highlighting: Implement logic to detect if a drug appears in BOTH the Left and Right lists. Visually highlight these overlapping rows in green.
Auto-Summary: Below the table, dynamically generate and render a summary sentence. (e.g., "3 of 5 clinically established drugs for Hypertension appear in our top 10 computed ranking — validating the approach.") If zero overlap exists, honestly report: "No overlap detected — model coverage for this disease may be limited."
Execution Plan: Before writing any code, please review these four features, explore the current project structure, and provide a brief step-by-step plan on which files you will create or modify to implement this. Await my approval before coding.**Feature 3: On-the-Fly Drug Inference Tool**
We need a feature that allows a user to type in a drug name and have the model compute its relevance score live, even if the drug isn't in our pre-computed database.
1. **Dynamic Lookup:** If the inputted drug name is not in our local dataset, implement a mechanism to look up its required input features (e.g., target genes, SMILES string, or chemical properties) via a local lookup table or a standard external API (like DrugBank, ChEMBL, or PubChem).
2. **Live Execution:** Pass these dynamically fetched features into the exact same computational pipeline used for the rest of the application. Run the prediction/scoring logic live.
3. **UI/UX:** Add a search interface in the frontend. When a search is triggered, display a clear loading state (e.g., "Computing relevance for [drug]... this may take a moment").
4. **Display Results:** Once the backend finishes, display the drug's computed relevance/similarity score to the currently active disease.
5. **No Permanent State:** Keep this result strictly in-memory. Do NOT automatically append it to our pre-computed databases or permanent storage unless I explicitly confirm later.
6. **Error Handling:** If the required biological/chemical data for the typed drug cannot be found, gracefully abort and display: "Insufficient data available for [drug name] — computational relevance cannot be evaluated."

**Feature 4: Clinical Verification / Comparative Analysis Panel**
We must prove our computational model makes biological sense by comparing its predictions against real-world clinical treatments. 
1. **Ground Truth Data Setup:** If it doesn't already exist, create a file named `known_indications.csv` (or equivalent database table) containing columns for `disease_name`, `drug_name`, and `evidence_level` (e.g., "Approved", "Phase II", "Off-label"). Populate this with a handful of well-documented, real-world treatments for the diseases currently supported by our app. *Crucial rule:* Ensure the drug names exactly match the naming conventions used in our computational drug pool.
2. **Comparison UI:** Build a new section/tab in the frontend showing a side-by-side comparison table (or split view) for the currently selected disease.
   - **LEFT Column:** "Currently Used Clinically" — List the real-world drugs from our ground-truth data, along with their evidence level.
   - **RIGHT Column:** "Model Computed Ranking" — List our model's top 10 predicted candidate drugs with their scores.
3. **Visual Verification:** Implement logic to detect overlapping drugs (drugs that appear in both the clinical list and our model's top 10). Visually highlight these overlapping rows in green. This acts as visual proof that the model independently rediscovers real treatments.
4. **Auto-Summary Metric:** Below the table, dynamically generate a summary sentence. Example: "X out of Y clinically established drugs for [Disease] appear in our top 10 computed ranking — validating the model's approach."
5. **Honest Reporting:** If zero known drugs overlap with our top 10 for a given disease, do not hide it. Display the message: "No overlap detected between known clinical treatments and our top 10 computed predictions for this disease. Model coverage or predictive accuracy here may be limited."

**Phase 3: Review and Commit**
Before saving any changes permanently:
1. Show me a summary of the files changed and the overall approach taken.
2. Ask me for confirmation to proceed.
3. Once I confirm, commit the changes with a clear message like: "Add live drug inference and clinical verification panel".