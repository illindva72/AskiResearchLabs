"""
evaluate.py — Claude AI evaluation across 8 dimensions (Python/Streamlit port)

Calls the Anthropic API with a dual-persona prompt (MLOps expert + LJMU professor)
and returns structured JSON with 7 dimension keys + a references section.
"""

import os
import json
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "You are a dual expert: (1) Elite MLOps Architect for Investment Banks. "
    "(2) Strict AI/ML Professor at LJMU reviewing Master's thesis proposals with "
    "zero sugar-coating. Be direct, specific, brutally honest. "
    "Respond ONLY with valid JSON — no markdown fences, no extra text before or after."
)

def _build_prompt(area: str, domain: str, topic_name: str, topic_details: str,
                  papers: list[dict], previous_feedback: str = None, previous_eval: dict = None) -> str:
    paper_list = "\n".join(
        f"{i+1}. [{p.get('source','?')}] \"{p.get('title','')}\" "
        f"({p.get('year') or 'n/a'}, {p.get('citations') or 0} cites)"
        for i, p in enumerate(papers[:12])
    )

    base_prompt = f"""Evaluate this LJMU Master's thesis proposal:

AREA: {area or 'Not specified'}
DOMAIN: {domain or 'Not specified'}
TOPIC: {topic_name}
DETAILS: {topic_details or 'Not provided'}

COMPETITIVE PAPERS ({len(papers)} found):
{paper_list}

Return ONLY a JSON object with exactly these 7 keys. Each value has:
riskLevel ("Low","Medium","High"), verdict (1 bold sentence),
points (array of 4-6 specific strings), summary (2-3 sentence paragraph).

{{
  "feasible": {{
    "riskLevel": "Low|Medium|High",
    "verdict": "...",
    "points": [
      "Is a suitable dataset publicly available or synthetically generatable?",
      "Can the project be completed within a 5-month Master's timeline?",
      "Does it require GPU? If yes, is it accessible via free-tier cloud (Google Colab Pro, Kaggle, AWS Free Tier)?",
      "Are there ethical/legal barriers to data access?"
    ],
    "summary": "..."
  }},
  "novel": {{
    "riskLevel": "Low|Medium|High",
    "verdict": "...",
    "points": [
      "Has a very similar problem been solved in published academic literature?",
      "What is the unique angle, method, or domain application that differentiates this from prior work?",
      "Mention 1-2 research gaps this topic addresses."
    ],
    "summary": "..."
  }},
  "relevant": {{
    "riskLevel": "Low|Medium|High",
    "verdict": "...",
    "points": [
      "What is the real-world industry pain point this solves?",
      "How does solving this problem benefit an Investment Bank's back office operations?",
      "How does this topic strengthen an MLOps Engineer's portfolio?"
    ],
    "summary": "..."
  }},
  "ethical": {{
    "riskLevel": "Low|Medium|High",
    "verdict": "...",
    "points": [
      "Does this research avoid use of proprietary, confidential, or personally identifiable financial data?",
      "Are there any IP, copyright, or data privacy concerns (GDPR, FCA regulations)?",
      "Confirm this topic does not reproduce or closely paraphrase any known published thesis."
    ],
    "summary": "..."
  }},
  "scope": {{
    "riskLevel": "Low|Medium|High",
    "verdict": "...",
    "points": [
      "Is the problem statement specific enough for a Master's dissertation (not too broad)?",
      "Is it narrow enough to complete with limited resources but broad enough to generate meaningful academic contribution?",
      "Suggest how scope can be adjusted (widened or narrowed) if needed."
    ],
    "summary": "..."
  }},
  "professorView": {{
    "riskLevel": "Low|Medium|High",
    "verdict": "APPROVE or REJECT — one sentence with reason",
    "points": [
      "Is this topic really banking domain related or common IT industry problems? If they are common IT problems, is it safe to submit these topics to LJMU under banking domain?",
      "Universities like LJMU, do they usually approve these topics? What is the approval rate of these topics, amongst all named universities like LJMU in Europe?",
      "What is the Risk involved in working on these research topics, in terms of 1. time frame that I have to finish within 4-5 months and 2. Dataset quality by generating synthetic data?",
      "Do you accept using only the Public Data? or Should I use public Data and GAN data combinations?"
    ],
    "summary": "..."
  }},
  "careerAlignment": {{
    "riskLevel": "Low|Medium|High",
    "verdict": "...",
    "points": [
      "How is aligned with future roles or career path like MLOps Engineer/Gen AI Engineer/etc?"
    ],
    "summary": "..."
  }}
}}"""

    if previous_feedback and previous_eval:
        base_prompt += f"""\n\nPREVIOUS EVALUATION RESULTS:
{json.dumps(previous_eval, indent=2)}

USER FEEDBACK:
"{previous_feedback}"

Please RE-EVALUATE the topic, modifying your responses to address the user's specific feedback above. Adjust your verdicts, risk levels, and points to reflect these concerns.
"""

    return base_prompt

def evaluate_research(area: str, domain: str, topic_name: str,
                       topic_details: str, papers: list[dict], previous_feedback: str = None, previous_eval: dict = None) -> dict:
    """
    Call Claude and return a dict with keys:
      feasible, novel, relevant, ethical, scope, professorView, careerAlignment

    Raises RuntimeError on API or parse failure.
    """
    api_key  = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")

    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file to use AI evaluation."
        )

    client_kwargs: dict = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = anthropic.Anthropic(**client_kwargs)

    prompt = _build_prompt(area, domain, topic_name, topic_details, papers, previous_feedback, previous_eval)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = (message.content[0].text or "").strip()  # type: ignore
    if not raw:
        raise RuntimeError("Empty response from AI model. Please try again.")

    # Strip accidental markdown fences
    cleaned = re.sub(r"^```json\s*", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*",     "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$",     "", cleaned).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"AI response could not be parsed as JSON: {e}. "
            f"First 300 chars: {raw[:300]}"
        )

    return result

def generate_prerequisites(area: str, domain: str, topic_name: str, topic_details: str, papers: list[dict] = None) -> dict:
    """
    Call Claude and return a dict with keys:
      flowchart, dataset, input_vars, output_vars, matching_papers
    """
    api_key  = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")

    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file to use AI evaluation."
        )

    client_kwargs: dict = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = anthropic.Anthropic(**client_kwargs)

    papers_context = ""
    if papers:
        papers_context = "\n".join(
            f"{i+1}. [Source: {p.get('source', '?')}] Title: \"{p.get('title', '')}\"\n   Abstract: {p.get('abstract', '')[:300]}..."
            for i, p in enumerate(papers[:15])
        )

    prompt = f"""Generate Pre-requisites and Model Execution Factors for this Master's thesis proposal:

AREA: {area or 'Not specified'}
DOMAIN: {domain or 'Not specified'}
TOPIC: {topic_name}
DETAILS: {topic_details or 'Not provided'}

SEARCH RESULTS CONTEXT (Matching Papers):
{papers_context if papers_context else "None provided."}

Return your response ONLY using the following XML tags. Do not include any other text outside these tags. Use HTML tags for formatting inside the tags instead of markdown (e.g., <ul>, <li>, <strong>, <p>). Do not use markdown syntax like **, *, or #.

<flowchart>
Provide an HTML unordered list (<ul>) showing the 4-5 high-level steps involved in generating the final model. 
CRITICAL: Do NOT use ASCII art, boxes, or drawing characters. Just use a simple, extremely brief HTML list (max 100 words total).
</flowchart>

<dataset>
Provide the most specific and best possible public sources to refer for the dataset to work with. Ideally the dataset should be a minimum of 50-75K records and look realistic for a real-time scenario. 
Important: The data sources should ONLY be from public sources where there is no issue with consent for using it, and they MUST NOT require any premium/paid subscriptions. You MUST provide direct URLs/links to these public datasets. Do NOT provide any code to generate synthetic data. Format your response beautifully using HTML (e.g. <p>, <strong>, <ul>) and ensure the links are clickable <a> tags.
</dataset>

<input_vars>
Provide the exact Input Variables from the provided Sample Dataset and explain in detail how they are considered as Input variables. Format your response beautifully using HTML.
</input_vars>

<output_vars>
Provide the Output variable(s) to evaluate the model and explain how/why they can be considered for model evaluation. Format your response beautifully using HTML.
</output_vars>

<matching_papers>
From the search results provided above, identify EXACTLY 5 research papers that match this problem to attach to the topic submission and to compare model accuracy. 
Return ONLY a valid JSON array of strings containing the titles of the 5 chosen papers. Example: ["Paper 1", "Paper 2", ...]
</matching_papers>
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
        system="You are an MLOps Architect. You MUST return ALL FIVE requested XML tags. Your response MUST be under 500 words total. Be extremely concise. Avoid all ASCII art and verbose explanations.",
        messages=[{"role": "user", "content": prompt}],
    )

    raw = (message.content[0].text or "").strip() # type: ignore
    
    def extract_tag(tag: str, text: str) -> str:
        pattern = f"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    flowchart = extract_tag("flowchart", raw)
    dataset = extract_tag("dataset", raw)
    input_vars = extract_tag("input_vars", raw)
    output_vars = extract_tag("output_vars", raw)
    matching_papers_str = extract_tag("matching_papers", raw)
    
    matching_papers = []
    if matching_papers_str:
        cleaned = re.sub(r"^```json\s*", "", matching_papers_str, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        try:
            matching_papers = json.loads(cleaned)
        except json.JSONDecodeError:
            matching_papers = [matching_papers_str]
    
    if not flowchart or not dataset or not input_vars or not output_vars:
         raise RuntimeError(f"AI response was missing required sections (likely stopped due to token limit). Raw output starts with:\n\n{raw[:500]}")

    return {
        "flowchart": flowchart,
        "dataset": dataset,
        "input_vars": input_vars,
        "output_vars": output_vars,
        "matching_papers": matching_papers
    }

def evaluate_opportunity(area: str, domain: str, topic_name: str, topic_details: str, profile_name: str = "Default", existing_dimensions: dict = None) -> dict:
    if existing_dimensions:
        dimensions = existing_dimensions
    else:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")

        client_kwargs: dict = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = anthropic.Anthropic(**client_kwargs)

        prompt = f"""Evaluate the Model Opportunity Score for this AI/ML topic:

AREA: {area or 'Not specified'}
DOMAIN: {domain or 'Not specified'}
TOPIC: {topic_name}
DETAILS: {topic_details or 'Not provided'}

You must evaluate this topic across 10 dimensions on a scale of 1 to 10 (10 is best, 1 is worst).
The 10 dimensions are:
1. Problem Value: Does it solve a meaningful problem? Frequent? Expensive?
2. Data Availability: Is training data accessible, sufficient, legal?
3. Signal Strength: Is there a learnable pattern, or inherently noisy?
4. Technical Feasibility: Can current ML solve it? Reasonable infra?
5. Competition Gap: (10=Underserved, 1=Saturated)
6. Scalability: Can inference scale economically?
7. Deployment Ease: Is deployment straightforward? Hardware needed?
8. Explainability Fit: Does the model fit explainability requirements?
9. Regulatory Risk: (10=Minimal risk, 1=Significant burden)
10. ROI Potential: Expected value vs build cost.

Return ONLY a valid JSON object with EXACTLY these 10 keys (e.g. "Problem Value", "Data Availability", etc.).
Each key MUST contain a JSON object with two fields: "score" (integer 1-10) and "reason" (a short 1-sentence justification).
Do NOT include markdown fences, just pure JSON.
"""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
            system="You are an elite AI researcher evaluating model opportunities. Output ONLY pure JSON.",
            messages=[{"role": "user", "content": prompt}],
        )

        raw = (message.content[0].text or "").strip()
        cleaned = re.sub(r"^```json\s*", "", raw, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()

        try:
            dimensions = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI response was not valid JSON: {raw[:500]}") from e

    # Calculate Weights
    weights = {
        "Problem Value": 0.20,
        "Data Availability": 0.15,
        "Signal Strength": 0.15,
        "Technical Feasibility": 0.10,
        "Competition Gap": 0.10,
        "Scalability": 0.10,
        "Deployment Ease": 0.05,
        "Explainability Fit": 0.05,
        "Regulatory Risk": 0.05,
        "ROI Potential": 0.05
    }

    if profile_name == "Startup":
        weights.update({"Problem Value": 0.30, "Competition Gap": 0.20, "ROI Potential": 0.10})
        # Normalize weights to 1.0
    elif profile_name == "Research":
        weights.update({"Data Availability": 0.25, "Signal Strength": 0.25, "Technical Feasibility": 0.20})
    elif profile_name == "Enterprise":
        weights.update({"Regulatory Risk": 0.15, "Explainability Fit": 0.15, "Deployment Ease": 0.15})

    total_weight = sum(weights.values())
    for k in weights:
        weights[k] = weights[k] / total_weight

    total_score = 0.0
    for dim_name in weights.keys():
        if dim_name not in dimensions:
            dimensions[dim_name] = {"score": 5, "reason": "Missing dimension."}
        
        # Calculate weighted score (out of 10)
        dim_weighted = dimensions[dim_name]["score"] * weights[dim_name]
        dimensions[dim_name]["weighted_score"] = round(dim_weighted * 10, 1) # out of 10 max relative
        dimensions[dim_name]["weight_percent"] = round(weights[dim_name] * 100, 1)
        total_score += dim_weighted

    # Final score out of 100
    final_score_100 = round(total_score * 10, 1)

    if final_score_100 >= 90:
        rating = "Exceptional Opportunity"
    elif final_score_100 >= 80:
        rating = "Strong Opportunity"
    elif final_score_100 >= 70:
        rating = "Promising Opportunity"
    elif final_score_100 >= 60:
        rating = "Needs Further Validation"
    elif final_score_100 >= 50:
        rating = "High Risk"
    else:
        rating = "Not Recommended"

    return {
        "dimensions": dimensions,
        "total_score": final_score_100,
        "rating": rating,
        "profile": profile_name
    }
